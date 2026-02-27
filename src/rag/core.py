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

    def find_top_claims(self, npc_id, query, top_k=5):
        query_embedding = self.create_query_embedding(query)
        with self.driver.session() as session:
            # BUGGFIX 2: Hämtar nu både NPC:ns OCH dess gruppers åsikter
            result = session.run("""
                MATCH (n:NPC {id: $npc_id})
                OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM)
                OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[:HAS_OPINION]->(c2:CLAIM)
                
                WITH collect(c1) + collect(c2) AS all_c
                UNWIND all_c AS c
                WITH DISTINCT c WHERE c IS NOT NULL AND c.embedding IS NOT NULL
                
                WITH c, vector.similarity.cosine(c.embedding, $query_vector) AS score
                RETURN elementId(c) AS id,
                    c.claim_id AS claim_id, 
                    c.content AS content, 
                    c.type AS type,
                    score
                ORDER BY score DESC
                LIMIT $top_k
            """, query_vector=query_embedding, npc_id=npc_id, top_k=top_k)
            return [dict(r) for r in result]
        
    def expand_from_claims(self, claim_ids):
        if not claim_ids:
            return [], []
        with self.driver.session() as session:
            result = session.run("""
                MATCH (start:CLAIM) WHERE elementId(start) IN $claim_ids
                OPTIONAL MATCH (start)-[:REFERENCE*0..]->(sub:CLAIM)
                WITH collect(DISTINCT sub) AS all_claims
                UNWIND all_claims AS c
                OPTIONAL MATCH (c)-[:REFERENCE]->(target)
                WHERE target:NPC OR target:PLACE OR target:OBJECT OR target:MYSTERY
                RETURN 
                    collect(DISTINCT {id: elementId(c), claim_id: c.claim_id, type: c.type, content: c.content}) AS claims,
                    collect(DISTINCT {id: elementId(target), name: target.name, type: labels(target)[0]}) AS constants
            """, claim_ids=claim_ids).single()
            
            claims = [c for c in result["claims"] if c.get("id")]
            constants = [c for c in result["constants"] if c.get("id")]
            return claims, constants
        
    def find_relational_candidates(self, npc_id, constant_ids):
        with self.driver.session() as session:
            # BUGGFIX 2: Tillåter även relationskandidater från grupper
            # UPPDATERING: Tog bort strikt krav på 'relation'-typ och lade till krav på 2+ konstanter.
            res = session.run("""
                MATCH (n:NPC {id: $npc_id})
                OPTIONAL MATCH (n)-[:HAS_OPINION]->(rc1:CLAIM)
                OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[:HAS_OPINION]->(rc2:CLAIM)
                
                WITH n, collect(rc1) + collect(rc2) AS all_rc
                UNWIND all_rc AS rc
                WITH DISTINCT rc, n WHERE rc IS NOT NULL
                
                OPTIONAL MATCH (rc)-[:REFERENCE]->(target)
                WITH rc, n, collect(target) AS targets, collect(elementId(target)) AS targetIds
                
                // Filtrera konstanterna mot vår lista från Fas 2
                WITH rc, n, targetIds, 
                     [id IN targetIds WHERE id IN $constant_ids] AS overlaps
                
                WHERE 
                   // --- REGLER ---
                   
                   // 1. (AVSTÄNGD) Krav på att typen måste vara explicit 'relation'. 
                   // Ta bort kommentaren nedan för att aktivera igen:
                   // rc.type = 'relation' AND
                   
                   // 2. Krav: Claimet måste handla om MINST TVÅ av konstanterna från Fas 2.
                   // Detta hittar kopplingar mellan entiteter i kontexten.
                   size(overlaps) >= 2
                
                RETURN DISTINCT elementId(rc) AS id, 
                                rc.content AS content, 
                                rc.type AS type
            """, npc_id=npc_id, constant_ids=constant_ids)
            return [dict(r) for r in res]

    def get_reference_chain(self, claim_id, npc_id):
        # Denna låg redan helt rätt med group_support från din kod!
        include_group = self._supports_group_membership()

        if include_group:
            query = """
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {id: $npc_id})-[o:HAS_OPINION]->(ref)
                OPTIONAL MATCH (n:NPC {id: $npc_id})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
                WITH ref, depth,
                     COALESCE(o.belief_in, go.belief_in) AS belief_in,
                     COALESCE(o.openness, go.openness) AS openness
                RETURN DISTINCT elementId(ref) AS id,
                       ref.content AS content,
                       ref.claim_id AS claim_id,
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
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {id: $npc_id})-[o:HAS_OPINION]->(ref)
                WITH ref, depth,
                     o.belief_in AS belief_in,
                     o.openness AS openness
                RETURN DISTINCT elementId(ref) AS id,
                       ref.claim_id AS claim_id,
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
                "claim_id": r["claim_id"],
                "content": r["content"],
                "type": r["type"],
                "depth": r["depth"],
                "belief_in": r["belief_in"],
                "openness": r["openness"]
            } for r in result]

    def build_claim_chains(self, claims, npc_id):
        if not claims: return []
        
        # Build a graph where Referenced Claim is the Parent of the Referencing Claim.
        # Example: "I agree" (A) references "Sky is blue" (B).
        # Graph: B -> A.
        # Output: "Sky is blue. I agree."
        
        all_nodes = {}  # id -> claim data
        adj = {}        # parent_id -> list of child_ids
        potential_roots = set()
        
        # 1. Collect all nodes and build the hierarchy (Bottom-Up)
        for claim in claims:
            # Chain comes as [Referencer, Referenced, Referenced_Deep...]
            # e.g. [A, B, C] where A->B->C
            chain = self.get_reference_chain(claim["id"], npc_id)
            if not chain: continue
            
            # Add all nodes to our lookup
            for c in chain:
                all_nodes[c["id"]] = c
                if c["id"] not in adj:
                    adj[c["id"]] = []
                potential_roots.add(c["id"])

            # Link them: C is parent of B, B is parent of A
            # Iterate backwards through the chain
            for i in range(len(chain) - 1, 0, -1):
                parent = chain[i]   # e.g. C
                child = chain[i-1]  # e.g. B
                
                # Link parent -> child
                if child["id"] not in adj[parent["id"]]:
                    adj[parent["id"]].append(child["id"])
                
                # If a node is a child, it cannot be a root
                if child["id"] in potential_roots:
                    potential_roots.remove(child["id"])

        # 2. Depth-First Traversal to build coherent chains from Roots (Core Claims)
        final_chains = []
        visited = set()

        def dfs(node_id):
            if node_id in visited:
                return []
            visited.add(node_id)
            
            result = [all_nodes[node_id]]
            
            # Visit children (Referencers)
            for child_id in adj.get(node_id, []):
                result.extend(dfs(child_id))
            
            return result

        # Process from identified roots (The deepest referenced claims)
        for root_id in list(potential_roots):
            if root_id in visited: continue
            
            chain_nodes = dfs(root_id)
            if not chain_nodes: continue

            contents = [c["content"] for c in chain_nodes]
            ids = [c["id"] for c in chain_nodes]
            
            final_chains.append({
                "content": " ".join(contents),
                "ids": ids,
                "chain_length": len(chain_nodes),
                "has_relation_type": any(c.get("type") == "relation" for c in chain_nodes)
            })

        return final_chains