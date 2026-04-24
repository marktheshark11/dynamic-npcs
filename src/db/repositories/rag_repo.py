from .base import BaseRepository


class RAGRepo(BaseRepository):
    """Read queries used by the RAG retrieval pipeline."""

    @staticmethod
    def _claim_content_expr(locale: str, alias: str = "c") -> str:
        return f"{alias}.content_en" if locale == "en" else f"{alias}.content"

    @staticmethod
    def _name_expr(locale: str, alias: str = "target") -> str:
        return f"{alias}.name_en" if locale == "en" else f"{alias}.name"

    @staticmethod
    def _prefix_expr(locale: str, alias: str) -> str:
        return f"{alias}.prefix_en" if locale == "en" else f"{alias}.prefix"

    @staticmethod
    def _suffix_expr(locale: str, alias: str) -> str:
        return f"{alias}.suffix_en" if locale == "en" else f"{alias}.suffix"

    @staticmethod
    def _overwrite_suffix_expr(locale: str, alias: str) -> str:
        return f"{alias}.overwrite_suffix_en" if locale == "en" else f"{alias}.overwrite_suffix"

    @staticmethod
    def _condition_expr(primary_alias: str, fallback_alias: str | None, field: str) -> str:
        if fallback_alias is None:
            return f"coalesce({primary_alias}.{field}, []) AS {field}"
        return (
            f"CASE WHEN {primary_alias} IS NOT NULL "
            f"THEN coalesce({primary_alias}.{field}, []) "
            f"ELSE coalesce({fallback_alias}.{field}, []) END AS {field}"
        )

    @classmethod
    def _condition_return_exprs(cls, primary_alias: str, fallback_alias: str | None = None) -> str:
        fields = [
            "required_claim_ids",
            "excluded_claim_ids",
            "required_seen_object_ids",
            "excluded_seen_object_ids",
            "required_item_ids",
            "excluded_item_ids",
            "required_seen_door_ids",
            "excluded_seen_door_ids",
            "required_opened_door_ids",
            "excluded_opened_door_ids",
        ]
        return ",\n                     ".join(
            cls._condition_expr(primary_alias, fallback_alias, field)
            for field in fields
        )

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
            OPTIONAL MATCH (n)-[o1:HAS_OPINION]->(c1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[o2:HAS_OPINION]->(c2:CLAIM)

            WITH collect(c1) + collect(c2) AS all_c
            UNWIND all_c AS c
            WITH DISTINCT c WHERE c IS NOT NULL AND {embedding_expr} IS NOT NULL

            WITH c, vector.similarity.cosine({embedding_expr}, $query_vector) AS score
            RETURN elementId(c) AS id,
                   c.claim_id AS claim_id,
                   {content_expr} AS content,
                   c.type AS type,
                   coalesce(c.important, false) AS important,
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
            OPTIONAL MATCH (n)-[o1:HAS_OPINION]->(c1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[o2:HAS_OPINION]->(c2:CLAIM)

            WITH collect(c1) + collect(c2) AS all_c
            UNWIND all_c AS c
            WITH DISTINCT c WHERE c IS NOT NULL AND c.claim_id IN $claim_ids

            RETURN elementId(c) AS id,
                   c.claim_id AS claim_id,
                   {content_expr} AS content,
                   c.type AS type,
                   coalesce(c.important, false) AS important
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
                collect(DISTINCT {{id: elementId(c), claim_id: c.claim_id, type: c.type, content: {content_expr}, important: coalesce(c.important, false)}}) AS claims,
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

            WHERE size(overlaps) >= 1

            RETURN DISTINCT elementId(rc) AS id,
                            rc.claim_id AS claim_id,
                            {content_expr} AS content,
                            rc.type AS type,
                            coalesce(rc.important, false) AS important
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
                            rc.type AS type,
                            coalesce(rc.important, false) AS important
            """,
            mystery_ids=mystery_ids,
            npc_id=npc_id,
        )
        return [dict(r) for r in records]

    def find_unlocked_opinion_claims(
        self,
        npc_id: str,
        aware_claim_ids: list[str],
        seen_object_ids: list[str],
        inventory_item_ids: list[str],
        seen_door_ids: list[str],
        opened_door_ids: list[str],
        locale: str = "sv",
    ) -> list[dict]:
        if not any([aware_claim_ids, seen_object_ids, inventory_item_ids, seen_door_ids, opened_door_ids]):
            return []

        content_expr = self._claim_content_expr(locale, "c")
        records = self._run(
            f"""
            MATCH (n:NPC {{id: $npc_id}})
            OPTIONAL MATCH (n)-[o1:HAS_OPINION]->(c1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(:GROUP)-[o2:HAS_OPINION]->(c2:CLAIM)

            WITH collect({{claim: c1, opinion: o1}}) + collect({{claim: c2, opinion: o2}}) AS opinions
            UNWIND opinions AS item
            WITH item.claim AS c, item.opinion AS o
            WHERE c IS NOT NULL
              AND (
                size(coalesce(o.required_claim_ids, [])) > 0 OR
                size(coalesce(o.excluded_claim_ids, [])) > 0 OR
                size(coalesce(o.required_seen_object_ids, [])) > 0 OR
                size(coalesce(o.excluded_seen_object_ids, [])) > 0 OR
                size(coalesce(o.required_item_ids, [])) > 0 OR
                size(coalesce(o.excluded_item_ids, [])) > 0 OR
                size(coalesce(o.required_seen_door_ids, [])) > 0 OR
                size(coalesce(o.excluded_seen_door_ids, [])) > 0 OR
                size(coalesce(o.required_opened_door_ids, [])) > 0 OR
                size(coalesce(o.excluded_opened_door_ids, [])) > 0
              )
              AND all(required_id IN coalesce(o.required_claim_ids, []) WHERE required_id IN $aware_claim_ids)
              AND none(excluded_id IN coalesce(o.excluded_claim_ids, []) WHERE excluded_id IN $aware_claim_ids)
              AND all(required_id IN coalesce(o.required_seen_object_ids, []) WHERE required_id IN $seen_object_ids)
              AND none(excluded_id IN coalesce(o.excluded_seen_object_ids, []) WHERE excluded_id IN $seen_object_ids)
              AND all(required_id IN coalesce(o.required_item_ids, []) WHERE required_id IN $inventory_item_ids)
              AND none(excluded_id IN coalesce(o.excluded_item_ids, []) WHERE excluded_id IN $inventory_item_ids)
              AND all(required_id IN coalesce(o.required_seen_door_ids, []) WHERE required_id IN $seen_door_ids)
              AND none(excluded_id IN coalesce(o.excluded_seen_door_ids, []) WHERE excluded_id IN $seen_door_ids)
              AND all(required_id IN coalesce(o.required_opened_door_ids, []) WHERE required_id IN $opened_door_ids)
              AND none(excluded_id IN coalesce(o.excluded_opened_door_ids, []) WHERE excluded_id IN $opened_door_ids)

            RETURN DISTINCT elementId(c) AS id,
                            c.claim_id AS claim_id,
                            {content_expr} AS content,
                            c.type AS type,
                            coalesce(c.important, false) AS important
            """,
            npc_id=npc_id,
            aware_claim_ids=aware_claim_ids,
            seen_object_ids=seen_object_ids,
            inventory_item_ids=inventory_item_ids,
            seen_door_ids=seen_door_ids,
            opened_door_ids=opened_door_ids,
        )
        return [dict(r) for r in records]

    def get_reference_chain(self, claim_id: str, npc_id: str, include_group: bool, locale: str = "sv") -> list[dict]:
        content_expr = self._claim_content_expr(locale, "ref")
        opinion_prefix_expr = self._prefix_expr(locale, "o")
        group_prefix_expr = self._prefix_expr(locale, "go")
        opinion_suffix_expr = self._suffix_expr(locale, "o")
        group_suffix_expr = self._suffix_expr(locale, "go")
        opinion_overwrite_suffix_expr = self._overwrite_suffix_expr(locale, "o")
        group_overwrite_suffix_expr = self._overwrite_suffix_expr(locale, "go")
        group_conditions_expr = self._condition_return_exprs("o", "go")
        npc_conditions_expr = self._condition_return_exprs("o")
        if include_group:
            query = f"""
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
                WITH ref, depth,
                     COALESCE({opinion_prefix_expr}, {group_prefix_expr}) AS prefix,
                     COALESCE({opinion_suffix_expr}, {group_suffix_expr}) AS suffix,
                     COALESCE({opinion_overwrite_suffix_expr}, {group_overwrite_suffix_expr}) AS overwrite_suffix,
                     {group_conditions_expr}
                RETURN DISTINCT elementId(ref) AS id,
                       {content_expr} AS content,
                       ref.claim_id AS claim_id,
                       ref.type AS type,
                       coalesce(ref.important, false) AS important,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix,
                       required_claim_ids,
                       excluded_claim_ids,
                       required_seen_object_ids,
                       excluded_seen_object_ids,
                       required_item_ids,
                       excluded_item_ids,
                       required_seen_door_ids,
                       excluded_seen_door_ids,
                       required_opened_door_ids,
                       excluded_opened_door_ids
            """
        else:
            query = f"""
                MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                WITH ref, depth,
                     {opinion_prefix_expr} AS prefix,
                     {opinion_suffix_expr} AS suffix,
                     {opinion_overwrite_suffix_expr} AS overwrite_suffix,
                     {npc_conditions_expr}
                RETURN DISTINCT elementId(ref) AS id,
                       ref.claim_id AS claim_id,
                       {content_expr} AS content,
                       ref.type AS type,
                       coalesce(ref.important, false) AS important,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix,
                       required_claim_ids,
                       excluded_claim_ids,
                       required_seen_object_ids,
                       excluded_seen_object_ids,
                       required_item_ids,
                       excluded_item_ids,
                       required_seen_door_ids,
                       excluded_seen_door_ids,
                       required_opened_door_ids,
                       excluded_opened_door_ids
            """

        records = self._run(query, claim_id=claim_id, npc_id=npc_id)
        return [dict(r) for r in records]

    def get_upstream_claims(self, claim_id: str, npc_id: str, up_steps: int, include_group: bool, locale: str = "sv") -> list[dict]:
        content_expr = self._claim_content_expr(locale, "ref")
        opinion_prefix_expr = self._prefix_expr(locale, "o")
        group_prefix_expr = self._prefix_expr(locale, "go")
        opinion_suffix_expr = self._suffix_expr(locale, "o")
        group_suffix_expr = self._suffix_expr(locale, "go")
        opinion_overwrite_suffix_expr = self._overwrite_suffix_expr(locale, "o")
        group_overwrite_suffix_expr = self._overwrite_suffix_expr(locale, "go")
        group_conditions_expr = self._condition_return_exprs("o", "go")
        npc_conditions_expr = self._condition_return_exprs("o")
        if include_group:
            query = f"""
                MATCH path = (ref:CLAIM)-[:REFERENCE*1..{up_steps}]->(start:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, -length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
                WITH ref, depth,
                     COALESCE({opinion_prefix_expr}, {group_prefix_expr}) AS prefix,
                     COALESCE({opinion_suffix_expr}, {group_suffix_expr}) AS suffix,
                     COALESCE({opinion_overwrite_suffix_expr}, {group_overwrite_suffix_expr}) AS overwrite_suffix,
                     {group_conditions_expr}
                RETURN DISTINCT elementId(ref) AS id,
                       {content_expr} AS content,
                       ref.claim_id AS claim_id,
                       ref.type AS type,
                       coalesce(ref.important, false) AS important,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix,
                       required_claim_ids,
                       excluded_claim_ids,
                       required_seen_object_ids,
                       excluded_seen_object_ids,
                       required_item_ids,
                       excluded_item_ids,
                       required_seen_door_ids,
                       excluded_seen_door_ids,
                       required_opened_door_ids,
                       excluded_opened_door_ids
            """
        else:
            query = f"""
                MATCH path = (ref:CLAIM)-[:REFERENCE*1..{up_steps}]->(start:CLAIM)
                WHERE elementId(start) = $claim_id
                WITH ref, -length(path) AS depth
                ORDER BY depth ASC
                OPTIONAL MATCH (n:NPC {{id: $npc_id}})-[o:HAS_OPINION]->(ref)
                WITH ref, depth,
                     {opinion_prefix_expr} AS prefix,
                     {opinion_suffix_expr} AS suffix,
                     {opinion_overwrite_suffix_expr} AS overwrite_suffix,
                     {npc_conditions_expr}
                RETURN DISTINCT elementId(ref) AS id,
                       ref.claim_id AS claim_id,
                       {content_expr} AS content,
                       ref.type AS type,
                       coalesce(ref.important, false) AS important,
                       depth,
                       prefix,
                       suffix,
                       overwrite_suffix,
                       required_claim_ids,
                       excluded_claim_ids,
                       required_seen_object_ids,
                       excluded_seen_object_ids,
                       required_item_ids,
                       excluded_item_ids,
                       required_seen_door_ids,
                       excluded_seen_door_ids,
                       required_opened_door_ids,
                       excluded_opened_door_ids
            """

        records = self._run(query, claim_id=claim_id, npc_id=npc_id)
        return [dict(r) for r in records]
