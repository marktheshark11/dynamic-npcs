from .base import BaseRepository


class RAGRepo(BaseRepository):
    """Read queries used by the RAG retrieval pipeline."""

    @staticmethod
    def _claim_content_expr(locale: str, alias: str = "c") -> str:
        return f"{alias}.content_en" if locale == "en" else f"{alias}.content"

    @staticmethod
    def _name_expr(locale: str, alias: str = "target") -> str:
        return f"{alias}.name_en" if locale == "en" else f"{alias}.name"

    def supports_group_membership(self) -> bool:
        try:
            labels_result = self._run_single(
                "CALL db.labels() YIELD label RETURN collect(label) AS labels"
            )
            rels_result = self._run_single(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS rels"
            )
        except Exception:
            return False

        labels = set(labels_result["labels"] if labels_result else [])
        rels = set(rels_result["rels"] if rels_result else [])
        return "GROUP" in labels and "MEMBER_OF" in rels

    def find_top_claims(self, npc_id: str, query_vector: list[float], top_k: int, locale: str = "sv") -> list[dict]:
        content_expr = self._claim_content_expr(locale)
        embedding_expr = "c.embedding_en" if locale == "en" else "c.embedding"
        records = self._run(
            f"""
            MATCH (n:NPC {{id: $npc_id}})
            OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[:HAS_OPINION]->(c2:CLAIM)

            WITH collect(c1) + collect(c2) AS all_c
            UNWIND all_c AS c
            WITH DISTINCT c WHERE c IS NOT NULL AND {embedding_expr} IS NOT NULL

            WITH c, vector.similarity.cosine({embedding_expr}, $query_vector) AS score
            RETURN elementId(c) AS id,
                   c.claim_id AS claim_id,
                   {content_expr} AS content,
                   c.type AS type,
                   score
            ORDER BY score DESC
            LIMIT $top_k
            """,
            query_vector=query_vector,
            npc_id=npc_id,
            top_k=top_k,
        )
        return [dict(r) for r in records]

    def find_claims_by_claim_ids(self, npc_id: str, claim_ids: list[str], locale: str = "sv") -> list[dict]:
        if not claim_ids:
            return []

        content_expr = self._claim_content_expr(locale)

        records = self._run(
            f"""
            MATCH (n:NPC {{id: $npc_id}})
            OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[:HAS_OPINION]->(c2:CLAIM)

            WITH collect(c1) + collect(c2) AS all_c
            UNWIND all_c AS c
            WITH DISTINCT c WHERE c IS NOT NULL AND c.claim_id IN $claim_ids

            RETURN elementId(c) AS id,
                   c.claim_id AS claim_id,
                   {content_expr} AS content,
                   c.type AS type
            """,
            npc_id=npc_id,
            claim_ids=claim_ids,
        )
        return [dict(r) for r in records]

    def expand_from_claims(self, claim_ids: list[str], locale: str = "sv") -> tuple[list[dict], list[dict]]:
        content_expr = self._claim_content_expr(locale)
        name_expr = self._name_expr(locale)
        record = self._run_single(
            f"""
            MATCH (start:CLAIM) WHERE elementId(start) IN $claim_ids
            OPTIONAL MATCH (start)-[:REFERENCE*0..]->(sub:CLAIM)
            WITH collect(DISTINCT sub) AS all_claims
            UNWIND all_claims AS c
            OPTIONAL MATCH (c)-[:REFERENCE]->(target)
            WHERE target:NPC OR target:PLACE OR target:OBJECT OR target:MYSTERY
            RETURN
                collect(DISTINCT {{id: elementId(c), claim_id: c.claim_id, type: c.type, content: {content_expr}}}) AS claims,
                collect(DISTINCT {{id: elementId(target), name: {name_expr}, type: labels(target)[0]}}) AS constants
            """,
            claim_ids=claim_ids,
        )
        if not record:
            return [], []

        claims = [c for c in record["claims"] if c.get("id")]
        constants = [c for c in record["constants"] if c.get("id")]
        return claims, constants

    def find_relational_candidates(self, npc_id: str, constant_ids: list[str], locale: str = "sv") -> list[dict]:
        content_expr = self._claim_content_expr(locale, "rc")
        records = self._run(
            f"""
            MATCH (n:NPC {{id: $npc_id}})
            OPTIONAL MATCH (n)-[:HAS_OPINION]->(rc1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[:HAS_OPINION]->(rc2:CLAIM)

            WITH n, collect(rc1) + collect(rc2) AS all_rc
            UNWIND all_rc AS rc
            WITH DISTINCT rc, n WHERE rc IS NOT NULL

            OPTIONAL MATCH (rc)-[:REFERENCE]->(target)
            WITH rc, n, collect(target) AS targets, collect(elementId(target)) AS targetIds

            WITH rc, n, targetIds,
                 [id IN targetIds WHERE id IN $constant_ids] AS overlaps

            WHERE size(overlaps) >= 2

            RETURN DISTINCT elementId(rc) AS id,
                            {content_expr} AS content,
                            rc.type AS type
            """,
            npc_id=npc_id,
            constant_ids=constant_ids,
        )
        return [dict(r) for r in records]

    def find_mystery_claims(self, mystery_ids: list[str], npc_id: str, locale: str = "sv") -> list[dict]:
        """Find NPC claims that reference any of the given MYSTERY nodes (threshold=1)."""
        content_expr = self._claim_content_expr(locale, "rc")
        records = self._run(
            f"""
            MATCH (n:NPC {{id: $npc_id}})
            OPTIONAL MATCH (n)-[:HAS_OPINION]->(rc1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[:HAS_OPINION]->(rc2:CLAIM)
            WITH collect(rc1) + collect(rc2) AS all_rc
            UNWIND all_rc AS rc
            WITH DISTINCT rc WHERE rc IS NOT NULL
            MATCH (rc)-[:REFERENCE]->(m:MYSTERY)
            WHERE elementId(m) IN $mystery_ids
            RETURN DISTINCT elementId(rc) AS id,
                            rc.claim_id AS claim_id,
                            {content_expr} AS content,
                            rc.type AS type
            """,
            mystery_ids=mystery_ids,
            npc_id=npc_id,
        )
        return [dict(r) for r in records]

    def get_reference_chain(self, claim_id: str, npc_id: str, include_group: bool, locale: str = "sv") -> list[dict]:
        content_expr = self._claim_content_expr(locale, "ref")
        if include_group:
            query = f"""
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
                WITH ref, depth,
                     COALESCE(o.prefix, go.prefix) AS prefix,
                     COALESCE(o.suffix, go.suffix) AS suffix,
                     COALESCE(o.overwrite_suffix, go.overwrite_suffix) AS overwrite_suffix
                RETURN DISTINCT elementId(ref) AS id,
                       {content_expr} AS content,
                       ref.claim_id AS claim_id,
                       ref.type AS type,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix
            """
        else:
            query = f"""
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                WITH ref, depth,
                     o.prefix AS prefix,
                     o.suffix AS suffix,
                     o.overwrite_suffix AS overwrite_suffix
                RETURN DISTINCT elementId(ref) AS id,
                       ref.claim_id AS claim_id,
                       {content_expr} AS content,
                       ref.type AS type,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix
            """

        records = self._run(query, claim_id=claim_id, npc_id=npc_id)
        return [dict(r) for r in records]

    def get_upstream_claims(self, claim_id: str, npc_id: str, up_steps: int, include_group: bool, locale: str = "sv") -> list[dict]:
        content_expr = self._claim_content_expr(locale, "ref")
        if include_group:
            query = f"""
                MATCH path = (ref:CLAIM)-[:REFERENCE*1..{up_steps}]->(start:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, -length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
                WITH ref, depth,
                     COALESCE(o.prefix, go.prefix) AS prefix,
                     COALESCE(o.suffix, go.suffix) AS suffix,
                     COALESCE(o.overwrite_suffix, go.overwrite_suffix) AS overwrite_suffix
                RETURN DISTINCT elementId(ref) AS id,
                       {content_expr} AS content,
                       ref.claim_id AS claim_id,
                       ref.type AS type,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix
            """
        else:
            query = f"""
                MATCH path = (ref:CLAIM)-[:REFERENCE*1..{up_steps}]->(start:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, -length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                WITH ref, depth,
                     o.prefix AS prefix,
                     o.suffix AS suffix,
                     o.overwrite_suffix AS overwrite_suffix
                RETURN DISTINCT elementId(ref) AS id,
                       ref.claim_id AS claim_id,
                       {content_expr} AS content,
                       ref.type AS type,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix
            """

        records = self._run(query, claim_id=claim_id, npc_id=npc_id)
        return [dict(r) for r in records]
