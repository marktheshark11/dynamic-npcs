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

    def mark_aware_of(self, player_id: str, claim_ids: list[str]) -> int:
        """
        Drag AWARE_OF-pilar från spelaren till varje claim i listan.
        Skapar bara pilen om den inte redan finns (MERGE).
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
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS total
            """,
            player_id=player_id,
            claim_ids=claim_ids,
        )
        return record["total"] if record else 0

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
