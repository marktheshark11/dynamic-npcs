from .base import BaseRepository
from ..models import Claim
from ..services import EmbeddingService


_NO_CHANGE = object()


class ClaimRepo(BaseRepository):
    """CRUD operations for CLAIM nodes. Auto-generates IDs and embeddings."""

    def __init__(self, driver, embedding_service: EmbeddingService) -> None:
        super().__init__(driver)
        self._embedding = embedding_service

    def _next_claim_id(self) -> str:
        """Get next available claim ID (C1, C2, C3, ...)."""
        records = self._run(
            "MATCH (c:CLAIM) "
            "WHERE c.claim_id IS NOT NULL AND c.claim_id STARTS WITH 'C' "
            "RETURN c.claim_id AS claim_id"
        )
        if not records:
            return "C1"

        numbers = []
        for r in records:
            try:
                numbers.append(int(r["claim_id"][1:]))
            except ValueError:
                continue

        return f"C{max(numbers) + 1}" if numbers else "C1"

    def create(self, content: str, claim_type: str | None = None) -> Claim:
        embedding = self._embedding.embed(content)
        claim_id = self._next_claim_id()

        params: dict = {
            "claim_id": claim_id,
            "content": content,
            "embedding": embedding,
        }

        set_parts = []
        if claim_type:
            set_parts.append("c.type = $type")
            params["type"] = claim_type

        set_clause = f" SET {', '.join(set_parts)}" if set_parts else ""
        query = (
            "CREATE (c:CLAIM {claim_id: $claim_id, content: $content, embedding: $embedding})"
            f"{set_clause} RETURN c.claim_id AS claim_id"
        )
        self._run(query, **params)
        return Claim(claim_id=claim_id, content=content, type=claim_type,
                     embedding=embedding)

    @staticmethod
    def _claim_sort_key(claim_id: str | None) -> tuple[int, int, str]:
        if claim_id and claim_id.startswith("C"):
            numeric_part = claim_id[1:]
            if numeric_part.isdigit():
                return (0, int(numeric_part), claim_id)
        return (1, 0, claim_id or "")

    def list_all(self) -> list[Claim]:
        records = self._run(
            "MATCH (c:CLAIM) "
            "RETURN c.claim_id AS claim_id, c.content AS content, "
            "c.type AS type"
        )
        claims = [
            Claim(
                claim_id=r["claim_id"],
                content=r["content"],
                type=r["type"],
            )
            for r in records
        ]
        claims.sort(key=lambda c: self._claim_sort_key(c.claim_id))
        return claims

    def reindex_claim_ids(self) -> list[tuple[str, str]]:
        """Renumber claim IDs to contiguous C1..Cn in current sort order.

        Returns a list of (old_id, new_id) for changed IDs.
        """
        records = self._run(
            "MATCH (c:CLAIM) "
            "RETURN elementId(c) AS eid, c.claim_id AS claim_id"
        )
        if not records:
            return []

        sorted_records = sorted(
            records,
            key=lambda r: self._claim_sort_key(r["claim_id"]),
        )

        updates: list[dict[str, str]] = []
        for idx, record in enumerate(sorted_records, 1):
            old_id = record["claim_id"] or ""
            new_id = f"C{idx}"
            if old_id != new_id:
                updates.append({
                    "eid": record["eid"],
                    "old_id": old_id,
                    "new_id": new_id,
                })

        if not updates:
            return []

        for idx, item in enumerate(updates, 1):
            tmp_id = f"__TMP_CLAIM_{idx}"
            self._run(
                "MATCH (c:CLAIM) WHERE elementId(c) = $eid "
                "SET c.claim_id = $tmp_id",
                eid=item["eid"],
                tmp_id=tmp_id,
            )

        for item in updates:
            self._run(
                "MATCH (c:CLAIM) WHERE elementId(c) = $eid "
                "SET c.claim_id = $new_id",
                eid=item["eid"],
                new_id=item["new_id"],
            )

        return [(item["old_id"], item["new_id"]) for item in updates]

    def get_by_id(self, claim_id: str) -> Claim | None:
        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id}) "
            "RETURN c.claim_id AS claim_id, c.content AS content, "
            "c.type AS type",
            claim_id=claim_id,
        )
        if not record:
            return None
        return Claim(
            claim_id=record["claim_id"],
            content=record["content"],
            type=record["type"],
        )

    def update(self, claim_id: str, content: str | None = None,
               claim_type: str | None | object = _NO_CHANGE) -> bool:
        """Update a claim. Use None for 'no change', empty string to remove a property.

        Note: claim_type uses sentinel default (...) to distinguish
        'not provided' from 'set to None'.
        """
        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id}) RETURN c",
            claim_id=claim_id,
        )
        if not record:
            return False

        updates = []
        params: dict = {"claim_id": claim_id}

        if content is not None:
            embedding = self._embedding.embed(content)
            updates.append("c.content = $content")
            updates.append("c.embedding = $embedding")
            params["content"] = content
            params["embedding"] = embedding

        if claim_type is not _NO_CHANGE:
            if claim_type is None or claim_type == "":
                updates.append("c.type = null")
            else:
                updates.append("c.type = $type")
                params["type"] = claim_type

        if not updates:
            return False

        query = f"MATCH (c:CLAIM {{claim_id: $claim_id}}) SET {', '.join(updates)} RETURN c"
        self._run(query, **params)
        return True

    def delete(self, claim_id: str) -> tuple[bool, dict[str, int]]:
        """Delete a claim and all connected relations.

        Reports HAS_OPINION, REFERENCE, and PART_OF relation counts,
        then detaches and deletes the claim node.

        Returns (success, counts_dict) where counts_dict has keys
        ``opinions``, ``references``, ``mysteries``, and ``other_relations``.
        """
        empty_counts: dict[str, int] = {
            "opinions": 0,
            "references": 0,
            "mysteries": 0,
            "other_relations": 0,
        }

        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id}) "
            "OPTIONAL MATCH ()-[o:HAS_OPINION]->(c) "
            "OPTIONAL MATCH (c)-[ref:REFERENCE]-() "
            "OPTIONAL MATCH (c)-[p:PART_OF]->() "
            "OPTIONAL MATCH (c)-[r]-() "
            "RETURN c.content AS content, "
            "       count(DISTINCT o) AS opinion_count, "
            "       count(DISTINCT ref) AS reference_count, "
            "       count(DISTINCT p) AS mystery_count, "
            "       count(DISTINCT r) AS total_relation_count",
            claim_id=claim_id,
        )
        if not record or not record["content"]:
            return False, empty_counts

        counts: dict[str, int] = {
            "opinions": record["opinion_count"],
            "references": record["reference_count"],
            "mysteries": record["mystery_count"],
            "other_relations": max(
                0,
                record["total_relation_count"]
                - record["opinion_count"]
                - record["reference_count"]
                - record["mystery_count"],
            ),
        }
        self._run(
            "MATCH (c:CLAIM {claim_id: $claim_id}) "
            "DETACH DELETE c",
            claim_id=claim_id,
        )
        return True, counts
