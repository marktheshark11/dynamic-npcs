from .base import BaseRepository
from ..models import Item, Player


class PlayerRepo(BaseRepository):
    """CRUD operations for PLAYER nodes."""

    def _next_player_id(self) -> str:
        record = self._run_single(
            "MATCH (p:PLAYER) "
            "WITH CASE "
            "WHEN p.player_id STARTS WITH 'player_' THEN toInteger(split(p.player_id, '_')[1]) "
            "WHEN p.player_id STARTS WITH 'p_' THEN toInteger(split(p.player_id, '_')[1]) "
            "ELSE NULL "
            "END AS numeric_id "
            "RETURN coalesce(max(numeric_id), 0) + 1 AS next_id"
        )
        next_id = 1 if not record else record["next_id"]
        return f"player_{next_id}"

    def create(self, name: str, appearance: str) -> Player:
        player_id = self._next_player_id()
        self._run(
            "CREATE (p:PLAYER {player_id: $player_id, name: $name, appearance: $appearance})",
            player_id=player_id,
            name=name,
            appearance=appearance,
        )
        return Player(player_id=player_id, name=name, appearance=appearance)

    def get_profile_by_id(self, player_id: str) -> dict | None:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "RETURN p.name AS name, p.appearance AS appearance "
            "LIMIT 1",
            player_id=player_id,
        )
        if not record:
            return None
        return {
            "name": record["name"],
            "appearance": record.get("appearance"),
        }

    def list_all(self) -> list[Player]:
        records = self._run(
            "MATCH (p:PLAYER) "
            "RETURN p.player_id AS player_id, p.name AS name, p.appearance AS appearance "
            "ORDER BY p.player_id"
        )
        return [
            Player(
                player_id=r["player_id"],
                name=r["name"],
                appearance=r["appearance"],
            )
            for r in records
        ]

    def update(self, player_id: str, name: str | None = None, appearance: str | None = None) -> bool:
        set_clauses = []
        params: dict[str, str] = {"player_id": player_id}

        if name is not None:
            set_clauses.append("p.name = $name")
            params["name"] = name

        if appearance is not None:
            set_clauses.append("p.appearance = $appearance")
            params["appearance"] = appearance

        if not set_clauses:
            return False

        query = f"MATCH (p:PLAYER {{player_id: $player_id}}) SET {', '.join(set_clauses)} RETURN p"
        record = self._run_single(query, **params)
        return record is not None

    def mark_aware_of(self, player_id: str, claim_ids: list[str], npc_id: str | None = None) -> int:
        """
        Drag AWARE_OF-pilar från spelaren till varje claim i listan.
        Skapar bara pilen om den inte redan finns (MERGE).
        Spårar vilka NPCs som nämnt claimet via npc_ids-listan på kanten.
        Returnerar antalet pilar som faktiskt skapades.
        """
        if not claim_ids:
            return 0
        record = self._run_single(
            """
            MATCH (p:PLAYER {player_id: $player_id})
            UNWIND $claim_ids AS cid
            MATCH (c:CLAIM {claim_id: cid})
            MERGE (p)-[r:AWARE_OF]->(c)
            ON CREATE SET
              r.created_at = datetime(),
              r.npc_ids = CASE WHEN $npc_id IS NOT NULL THEN [$npc_id] ELSE [] END
            ON MATCH SET
              r.npc_ids = CASE
                WHEN $npc_id IS NULL THEN coalesce(r.npc_ids, [])
                WHEN $npc_id IN coalesce(r.npc_ids, []) THEN r.npc_ids
                ELSE coalesce(r.npc_ids, []) + $npc_id
              END
            RETURN count(r) AS total
            """,
            player_id=player_id,
            claim_ids=claim_ids,
            npc_id=npc_id,
        )
        return record["total"] if record else 0

    def clear_aware_of(self, player_id: str) -> int:
        """Tar bort alla AWARE_OF-pilar för en specifik spelare. Returnerar antal borttagna."""
        record = self._run_single(
            """
            MATCH (p:PLAYER {player_id: $player_id})-[r:AWARE_OF]->()
            WITH count(r) AS total
            MATCH (p2:PLAYER {player_id: $player_id})-[r2:AWARE_OF]->()
            DELETE r2
            RETURN total
            """,
            player_id=player_id,
        )
        return record["total"] if record else 0

    def clear_aware_of_all(self) -> int:
        """Tar bort alla AWARE_OF-pilar i hela grafen. Returnerar antal borttagna."""
        record = self._run_single(
            """
            MATCH ()-[r:AWARE_OF]->()
            WITH count(r) AS total
            MATCH ()-[r2:AWARE_OF]->()
            DELETE r2
            RETURN total
            """,
        )
        return record["total"] if record else 0

    def get_aware_claim_ids_from_npc(self, player_id: str, npc_id: str) -> set[str]:
        """Returnerar claim_ids som spelaren redan fått av en specifik NPC."""
        records = self._run(
            """
            MATCH (p:PLAYER {player_id: $player_id})-[r:AWARE_OF]->(c:CLAIM)
            WHERE $npc_id IN coalesce(r.npc_ids, [])
            RETURN c.claim_id AS claim_id
            """,
            player_id=player_id,
            npc_id=npc_id,
        )
        return {r["claim_id"] for r in records if r.get("claim_id")}

    def mark_seen_object(self, player_id: str, object_id: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "MATCH (o:OBJECT:ITEM {object_id: $object_id}) "
            "MERGE (p)-[:SEEN_OBJECT]->(o) "
            "RETURN o.object_id AS object_id",
            player_id=player_id,
            object_id=object_id,
        )
        return record is not None

    def pickup_item(self, player_id: str, object_id: str) -> tuple[bool, str]:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "MATCH (o:OBJECT:ITEM {object_id: $object_id}) "
            "WITH p, o, coalesce(o.pickupable, false) AS pickupable "
            "FOREACH (_ IN CASE WHEN pickupable THEN [1] ELSE [] END | "
            "    MERGE (p)-[:HAS_ITEM]->(o) "
            "    MERGE (p)-[:SEEN_OBJECT]->(o)"
            ") "
            "RETURN pickupable AS pickupable",
            player_id=player_id,
            object_id=object_id,
        )
        if not record:
            return False, "Item eller player hittades inte"
        if not record["pickupable"]:
            return False, "Det itemet kan inte plockas upp"
        return True, "Item upplockat"

    def list_inventory(self, player_id: str) -> list[Item]:
        records = self._run(
            "MATCH (:PLAYER {player_id: $player_id})-[:HAS_ITEM]->(o:OBJECT:ITEM) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.pickupable AS pickupable "
            "ORDER BY o.object_id",
            player_id=player_id,
        )
        return [
            Item(
                object_id=r["object_id"],
                name=r["name"],
                inspect_text=r.get("inspect_text") or "",
                pickupable=bool(r.get("pickupable")),
            )
            for r in records
        ]

    def delete(self, player_id: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "RETURN p.player_id AS player_id",
            player_id=player_id,
        )
        if not record:
            return False

        self._run(
            "MATCH (p:PLAYER {player_id: $player_id})-[:HAS_CONVERSATION]->(c:CONVERSATION) "
            "SET c.player_id = NULL",
            player_id=player_id,
        )
        self._run(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "DETACH DELETE p",
            player_id=player_id,
        )
        return True
