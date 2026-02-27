from .base import BaseRepository
from ..models import Player


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
