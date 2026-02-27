from dataclasses import dataclass
from .base import BaseRepository


# Structural relation types with their inverse
STRUCTURAL_RELATIONS = {
    "SIBLING_WITH": "SIBLING_WITH",
    "FRIENDS_WITH": "FRIENDS_WITH",
    "DATING": "DATING",
    "MARRIED_TO": "MARRIED_TO",
    "DIVORCED_FROM": "DIVORCED_FROM",
    "PARENT_TO": "CHILD_TO",
    "CHILD_TO": "PARENT_TO",
}


@dataclass
class StructuralRelation:
    npc_a: str
    npc_b: str
    relation_type: str
    secrecy: float


class RelationRepo(BaseRepository):
    """CRUD for structural relations, REFERENCE, and MEMBER_OF."""

    # --- Structural ---

    def create_structural(self, name_a: str, name_b: str,
                          relation_type: str, secrecy: float = 0) -> bool:
        """Create a bidirectional structural relation between two NPCs."""
        if relation_type not in STRUCTURAL_RELATIONS:
            return False

        inverse = STRUCTURAL_RELATIONS[relation_type]

        # Forward relation
        self._run(
            f"MATCH (a:NPC {{name: $a}}), (b:NPC {{name: $b}}) "
            f"MERGE (a)-[r:{relation_type}]->(b) SET r.secrecy = $secrecy",
            a=name_a, b=name_b, secrecy=secrecy,
        )
        # Inverse relation
        self._run(
            f"MATCH (a:NPC {{name: $a}}), (b:NPC {{name: $b}}) "
            f"MERGE (b)-[r:{inverse}]->(a) SET r.secrecy = $secrecy",
            a=name_a, b=name_b, secrecy=secrecy,
        )
        return True

    def delete_all_between(self, name_a: str, name_b: str) -> int:
        """Remove all relations between two NPCs. Returns count of deleted."""
        record = self._run_single(
            "MATCH (a:NPC {name: $a})-[r]-(b:NPC {name: $b}) "
            "DELETE r RETURN count(r) AS cnt",
            a=name_a, b=name_b,
        )
        return record["cnt"] if record else 0

    # --- REFERENCE ---

    def create_reference(self, claim_id: str, target_name: str,
                         target_type: str) -> bool:
        """Create a REFERENCE from a CLAIM to another node.

        target_type: 'NPC', 'CLAIM', 'OBJECT', 'PLACE'
        For CLAIMs: target_name is the claim_id (e.g. 'C5')
        For others: target_name is the name property
        """
        if target_type == "CLAIM":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:CLAIM {claim_id: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        elif target_type == "NPC":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:NPC {name: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        elif target_type == "OBJECT":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:OBJECT {name: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        elif target_type == "PLACE":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:PLACE {name: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        else:
            return False

        record = self._run_single(query, claim_id=claim_id, target=target_name)
        return record is not None

    # --- MEMBER_OF ---

    def create_membership(self, npc_id: str, group_name: str) -> bool:
        """Create MEMBER_OF relation from NPC to GROUP."""
        record = self._run_single(
            "MATCH (npc:NPC {id: $npc_id}), (g:GROUP {name: $group_name}) "
            "MERGE (npc)-[:MEMBER_OF]->(g) RETURN npc",
            npc_id=npc_id, group_name=group_name,
        )
        return record is not None

    def delete_membership(self, npc_id: str, group_name: str) -> bool:
        """Remove MEMBER_OF relation."""
        record = self._run_single(
            "MATCH (npc:NPC {id: $npc_id})-[r:MEMBER_OF]->(g:GROUP {name: $group_name}) "
            "DELETE r RETURN count(r) AS cnt",
            npc_id=npc_id, group_name=group_name,
        )
        return record is not None and record["cnt"] > 0

    def list_members(self, group_name: str) -> list[str]:
        """List NPC ids that are members of a group."""
        records = self._run(
            "MATCH (npc:NPC)-[:MEMBER_OF]->(g:GROUP {name: $name}) "
            "RETURN npc.id AS id ORDER BY npc.id",
            name=group_name,
        )
        return [r["id"] for r in records]
