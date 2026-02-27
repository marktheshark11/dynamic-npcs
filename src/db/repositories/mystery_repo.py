from .base import BaseRepository
from ..models import Mystery, Claim


class MysteryRepo(BaseRepository):
    """CRUD for MYSTERY nodes and PART_OF relations (CLAIM -> MYSTERY)."""

    def create(self, name: str) -> Mystery:
        formatted = name.capitalize()
        self._run("MERGE (m:MYSTERY {name: $name})", name=formatted)
        return Mystery(name=formatted)

    def list_all(self) -> list[Mystery]:
        records = self._run(
            "MATCH (m:MYSTERY) RETURN m.name AS name ORDER BY m.name"
        )
        return [Mystery(name=r["name"]) for r in records]

    def delete(self, name: str) -> bool:
        record = self._run_single(
            "MATCH (m:MYSTERY {name: $name}) RETURN m", name=name,
        )
        if not record:
            return False
        self._run("MATCH (m:MYSTERY {name: $name}) DETACH DELETE m", name=name)
        return True

    # --- PART_OF ---

    def link_claim(self, claim_id: str, mystery_name: str) -> bool:
        """Create PART_OF relation from CLAIM to MYSTERY."""
        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id}), (m:MYSTERY {name: $name}) "
            "MERGE (c)-[:PART_OF]->(m) RETURN c",
            claim_id=claim_id, name=mystery_name,
        )
        return record is not None

    def unlink_claim(self, claim_id: str, mystery_name: str) -> bool:
        """Remove PART_OF relation from CLAIM to MYSTERY."""
        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id})-[r:PART_OF]->(m:MYSTERY {name: $name}) "
            "DELETE r RETURN count(r) AS cnt",
            claim_id=claim_id, name=mystery_name,
        )
        return record is not None and record["cnt"] > 0

    def list_claims(self, mystery_name: str) -> list[Claim]:
        """List all CLAIMs that are PART_OF a given MYSTERY."""
        records = self._run(
            "MATCH (c:CLAIM)-[:PART_OF]->(m:MYSTERY {name: $name}) "
            "RETURN c.claim_id AS claim_id, c.content AS content, c.type AS type "
            "ORDER BY c.claim_id",
            name=mystery_name,
        )
        return [
            Claim(claim_id=r["claim_id"], content=r["content"], type=r["type"])
            for r in records
        ]
