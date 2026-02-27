from dataclasses import dataclass
from .base import BaseRepository


@dataclass
class OpinionData:
    """Represents a HAS_OPINION relation between an entity and a claim."""
    entity_id: str      # NPC id or GROUP name
    entity_type: str    # "NPC" or "GROUP"
    claim_id: str
    claim_content: str
    belief_in: float
    openness: float


class OpinionRepo(BaseRepository):
    """CRUD operations for HAS_OPINION relations."""

    def create(self, entity_id: str, entity_type: str, claim_id: str,
               belief_in: float, openness: float) -> bool:
        """Create a HAS_OPINION relation from NPC/GROUP to CLAIM.

        entity_type: 'NPC' or 'GROUP'
        For NPC: entity_id matches npc.id
        For GROUP: entity_id matches group.name
        """
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})
            MATCH (c:CLAIM {claim_id: $claim_id})
            CREATE (npc)-[o:HAS_OPINION {belief_in: $belief_in, openness: $openness}]->(c)
            RETURN o
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})
            MATCH (c:CLAIM {claim_id: $claim_id})
            CREATE (g)-[o:HAS_OPINION {belief_in: $belief_in, openness: $openness}]->(c)
            RETURN o
            """
        record = self._run_single(
            query, entity_id=entity_id, claim_id=claim_id,
            belief_in=belief_in, openness=openness,
        )
        return record is not None

    def list_for_entity(self, entity_id: str, entity_type: str) -> list[OpinionData]:
        """List all opinions for a given NPC or GROUP."""
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})-[o:HAS_OPINION]->(c:CLAIM)
            RETURN npc.id AS eid, c.claim_id AS claim_id, c.content AS content,
                   o.belief_in AS belief_in, o.openness AS openness
            ORDER BY c.claim_id
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})-[o:HAS_OPINION]->(c:CLAIM)
            RETURN g.name AS eid, c.claim_id AS claim_id, c.content AS content,
                   o.belief_in AS belief_in, o.openness AS openness
            ORDER BY c.claim_id
            """
        records = self._run(query, entity_id=entity_id)
        return [
            OpinionData(
                entity_id=r["eid"],
                entity_type=entity_type,
                claim_id=r["claim_id"],
                claim_content=r["content"],
                belief_in=r["belief_in"],
                openness=r["openness"],
            )
            for r in records
        ]

    def delete(self, entity_id: str, entity_type: str, claim_id: str) -> bool:
        """Delete the HAS_OPINION relation between an entity and a claim."""
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            DELETE o
            RETURN count(o) AS deleted
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            DELETE o
            RETURN count(o) AS deleted
            """
        record = self._run_single(query, entity_id=entity_id, claim_id=claim_id)
        return record is not None and record["deleted"] > 0

    def update(self, entity_id: str, entity_type: str, claim_id: str,
               belief_in: float, openness: float) -> bool:
        """Update belief_in and openness for an existing HAS_OPINION relation."""
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            SET o.belief_in = $belief_in, o.openness = $openness
            RETURN o
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            SET o.belief_in = $belief_in, o.openness = $openness
            RETURN o
            """

        record = self._run_single(
            query,
            entity_id=entity_id,
            claim_id=claim_id,
            belief_in=belief_in,
            openness=openness,
        )
        return record is not None
