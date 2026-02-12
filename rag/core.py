from rag.rendering import Rendering


class RAGCore:
    def __init__(self, driver, embed_model):
        self.driver = driver
        self.embed_model = embed_model

    def create_query_embedding(self, text):
        return self.embed_model.embed_query(f"Represent this sentence for searching relevant passages: {text}")

    def get_accessible_claim_ids(self, npc_name):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n:NPC {name: $npc_name})
                OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM)
                OPTIONAL MATCH (n)-[:MEMBER_OF]->(g:GROUP)-[:HAS_OPINION]->(c2:CLAIM)
                WITH collect(DISTINCT c1) + collect(DISTINCT c2) AS claims
                UNWIND claims AS c
                WITH c WHERE c IS NOT NULL AND c.embedding IS NOT NULL
                RETURN DISTINCT elementId(c) AS id
            """, npc_name=npc_name)
            return [r["id"] for r in result]

    def find_top_claims(self, npc_name, query, top_k=5):
        accessible_ids = self.get_accessible_claim_ids(npc_name)
        if not accessible_ids:
            return []
        query_embedding = self.create_query_embedding(query)
        with self.driver.session() as session:
            result = session.run("""
                CALL db.index.vector.queryNodes('claim_index', $top_k * 3, $query_vector)
                YIELD node, score
                WHERE elementId(node) IN $accessible_ids
                RETURN elementId(node) AS id, 
                       node.content AS content, 
                       node.type AS type,
                       score
                LIMIT $top_k
            """, query_vector=query_embedding, accessible_ids=accessible_ids, top_k=top_k)
            return [{
                "id": r["id"],
                "content": r["content"],
                "type": r["type"],
                "score": r["score"]
            } for r in result]

    def get_constants_from_claims(self, claim_ids):
        if not claim_ids:
            return []
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:CLAIM) WHERE elementId(c) IN $claim_ids
                MATCH (c)-[:REFERENCE]->(target)
                WHERE target:NPC OR target:PLACE OR target:OBJECT
                RETURN DISTINCT labels(target)[0] AS type, target.name AS name, elementId(target) AS id
            """, claim_ids=claim_ids)
            return [{"type": r["type"], "name": r["name"], "id": r["id"]} for r in result]

    def find_relation_claims(self, npc_name, constant_ids, min_refs=2):
        if not constant_ids or len(constant_ids) < min_refs:
            return []
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n:NPC {name: $npc_name})
                OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM {type: "relation"})
                OPTIONAL MATCH (n)-[:MEMBER_OF]->(g:GROUP)-[:HAS_OPINION]->(c2:CLAIM {type: "relation"})
                WITH collect(DISTINCT c1) + collect(DISTINCT c2) AS claims
                UNWIND claims AS c
                WITH c WHERE c IS NOT NULL
                MATCH (c)-[:REFERENCE]->(target)
                WHERE elementId(target) IN $constant_ids
                WITH c, count(DISTINCT target) AS ref_count
                WHERE ref_count >= $min_refs
                RETURN elementId(c) AS id, 
                       c.content AS content, 
                       c.type AS type,
                       ref_count
            """, npc_name=npc_name, constant_ids=constant_ids, min_refs=min_refs)
            return [{
                "id": r["id"],
                "content": r["content"],
                "type": r["type"],
                "score": 0.0
            } for r in result]

    def get_reference_chain(self, claim_id, npc_name):
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth DESC
                OPTIONAL MATCH (n:NPC {name: $npc_name})-[o:HAS_OPINION]->(ref)
                OPTIONAL MATCH (n:NPC {name: $npc_name})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
                WITH ref, depth,
                     COALESCE(o.belief_in, go.belief_in) AS belief_in,
                     COALESCE(o.openness, go.openness) AS openness
                RETURN DISTINCT elementId(ref) AS id, 
                       ref.content AS content, 
                       ref.type AS type, 
                       depth,
                       belief_in,
                       openness
            """, claim_id=claim_id, npc_name=npc_name)
            return [{
                "id": r["id"],
                "content": r["content"],
                "type": r["type"],
                "depth": r["depth"],
                "belief_in": r["belief_in"],
                "openness": r["openness"]
            } for r in result]

    def build_claim_chains(self, claims, npc_name):
        if not claims:
            return []
        claim_ids = {c["id"] for c in claims}
        claims_in_others_chain = set()
        for claim in claims:
            chain = self.get_reference_chain(claim["id"], npc_name)
            for c in chain:
                if c["id"] != claim["id"] and c["id"] in claim_ids:
                    claims_in_others_chain.add(c["id"])
        processed = set()
        chain_metadata = []
        for claim in claims:
            if claim["id"] in claims_in_others_chain or claim["id"] in processed:
                continue
            chain = self.get_reference_chain(claim["id"], npc_name)
            chain = [c for c in chain if c["id"] not in processed]
            if not chain:
                continue
            for c in chain:
                processed.add(c["id"])
            rendered_parts = []
            for c in chain:
                rendered = Rendering.render_claim_static(
                    c["content"],
                    c["belief_in"],
                    c["openness"]
                )
                rendered_parts.append(rendered)
            combined = " ".join(rendered_parts)
            has_relation = any(c["type"] == "relation" for c in chain)
            chain_metadata.append({
                "content": combined,
                "is_relation": has_relation,
                "chain_length": len(chain)
            })
        return chain_metadata
