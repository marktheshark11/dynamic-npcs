from rag.rendering import Rendering


class RAGCore:
    def __init__(self, driver, embed_model):
        self.driver = driver
        self.embed_model = embed_model
        self._group_support: bool | None = None

    def _supports_group_membership(self):
        if self._group_support is not None:
            return self._group_support

        try:
            with self.driver.session() as session:
                labels_result = session.run("CALL db.labels() YIELD label RETURN collect(label) AS labels").single()
                rels_result = session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS rels"
                ).single()

            labels = set(labels_result["labels"] if labels_result else [])
            rels = set(rels_result["rels"] if rels_result else [])
            self._group_support = "GROUP" in labels and "MEMBER_OF" in rels
        except Exception:
            # Safe fallback: avoid GROUP/MEMBER_OF paths if schema checks are unavailable.
            self._group_support = False

        return self._group_support

    def create_query_embedding(self, text):
        return self.embed_model.embed_query(f"Represent this sentence for searching relevant passages: {text}")

    def get_npc_profile(self, npc_id):
        with self.driver.session() as session:
            record = session.run(
                "MATCH (n:NPC {id: $npc_id}) "
                "RETURN n.name AS name, n.personality AS personality, n.backstory AS backstory "
                "LIMIT 1",
                npc_id=npc_id,
            ).single()
            if not record:
                return None
            return {
                "name": record["name"],
                "personality": record.get("personality"),
                "backstory": record.get("backstory"),
            }

    def get_accessible_claim_ids(self, npc_id):
        include_group = self._supports_group_membership()

        if include_group:
            query = """
                MATCH (n:NPC {id: $npc_id})
                OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM)
                OPTIONAL MATCH (n)-[:MEMBER_OF]->(g:GROUP)-[:HAS_OPINION]->(c2:CLAIM)
                WITH collect(DISTINCT c1) + collect(DISTINCT c2) AS claims
                UNWIND claims AS c
                WITH c WHERE c IS NOT NULL AND c.embedding IS NOT NULL
                RETURN DISTINCT elementId(c) AS id
            """
        else:
            query = """
                MATCH (n:NPC {id: $npc_id})
                OPTIONAL MATCH (n)-[:HAS_OPINION]->(c:CLAIM)
                WITH c WHERE c IS NOT NULL AND c.embedding IS NOT NULL
                RETURN DISTINCT elementId(c) AS id
            """

        with self.driver.session() as session:
            result = session.run(query, npc_id=npc_id)
            return [r["id"] for r in result]

    def find_top_claims(self, npc_id, query, top_k=5):
        accessible_ids = self.get_accessible_claim_ids(npc_id)
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

    def find_relation_claims(self, npc_id, constant_ids, min_refs=2):
        if not constant_ids or len(constant_ids) < min_refs:
            return []

        include_group = self._supports_group_membership()

        if include_group:
            query = """
                MATCH (n:NPC {id: $npc_id})
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
            """
        else:
            query = """
                MATCH (n:NPC {id: $npc_id})
                OPTIONAL MATCH (n)-[:HAS_OPINION]->(c:CLAIM {type: "relation"})
                WITH c WHERE c IS NOT NULL
                MATCH (c)-[:REFERENCE]->(target)
                WHERE elementId(target) IN $constant_ids
                WITH c, count(DISTINCT target) AS ref_count
                WHERE ref_count >= $min_refs
                RETURN elementId(c) AS id,
                       c.content AS content,
                       c.type AS type,
                       ref_count
            """

        with self.driver.session() as session:
            result = session.run(query, npc_id=npc_id, constant_ids=constant_ids, min_refs=min_refs)
            return [{
                "id": r["id"],
                "content": r["content"],
                "type": r["type"],
                "score": 0.0
            } for r in result]

    def get_reference_chain(self, claim_id, npc_id):
        include_group = self._supports_group_membership()

        if include_group:
            query = """
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth DESC
                OPTIONAL MATCH (n:NPC {id: $npc_id})-[o:HAS_OPINION]->(ref)
                OPTIONAL MATCH (n:NPC {id: $npc_id})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
                WITH ref, depth,
                     COALESCE(o.belief_in, go.belief_in) AS belief_in,
                     COALESCE(o.openness, go.openness) AS openness
                RETURN DISTINCT elementId(ref) AS id,
                       ref.content AS content,
                       ref.type AS type,
                       depth,
                       belief_in,
                       openness
            """
        else:
            query = """
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth DESC
                OPTIONAL MATCH (n:NPC {id: $npc_id})-[o:HAS_OPINION]->(ref)
                WITH ref, depth,
                     o.belief_in AS belief_in,
                     o.openness AS openness
                RETURN DISTINCT elementId(ref) AS id,
                       ref.content AS content,
                       ref.type AS type,
                       depth,
                       belief_in,
                       openness
            """

        with self.driver.session() as session:
            result = session.run(query, claim_id=claim_id, npc_id=npc_id)
            return [{
                "id": r["id"],
                "content": r["content"],
                "type": r["type"],
                "depth": r["depth"],
                "belief_in": r["belief_in"],
                "openness": r["openness"]
            } for r in result]

    def build_claim_chains(self, claims, npc_id):
        if not claims:
            return []
        claim_ids = {c["id"] for c in claims}
        claims_in_others_chain = set()
        for claim in claims:
            chain = self.get_reference_chain(claim["id"], npc_id)
            for c in chain:
                if c["id"] != claim["id"] and c["id"] in claim_ids:
                    claims_in_others_chain.add(c["id"])
        processed = set()
        chain_metadata = []
        for claim in claims:
            if claim["id"] in claims_in_others_chain or claim["id"] in processed:
                continue
            chain = self.get_reference_chain(claim["id"], npc_id)
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
