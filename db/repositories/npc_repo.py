from .base import BaseRepository
from ..models import NPC, Group


class NPCRepo(BaseRepository):
    """CRUD operations for NPC nodes."""

    def create(self, npc: NPC) -> None:
        self._run(
            "MERGE (npc:NPC {id: $id}) "
            "SET npc.name = $name, npc.age = $age, npc.personality = $personality, npc.backstory = $backstory",
            id=npc.id, name=npc.name, age=npc.age, personality=npc.personality, backstory=npc.backstory,
        )

    def get_by_id(self, id: str) -> NPC | None:
        record = self._run_single(
            "MATCH (npc:NPC {id: $id}) "
            "RETURN npc.id AS id, npc.name AS name, npc.age AS age, npc.personality AS personality, npc.backstory AS backstory",
            id=id,
        )
        if not record:
            return None
        return NPC(
            id=record["id"],
            name=record["name"],
            age=record["age"],
            personality=record["personality"],
            backstory=record["backstory"]
        )

    def list_all(self) -> list[NPC]:
        records = self._run(
            "MATCH (npc:NPC) "
            "RETURN npc.id AS id, npc.name AS name, npc.age AS age, npc.personality AS personality, npc.backstory AS backstory "
            "ORDER BY npc.id"
        )
        return [
            NPC(id=r["id"], name=r["name"], age=r["age"], personality=r["personality"], backstory=r["backstory"])
            for r in records
        ]

    def update(self, id: str, name: str | None = None, age: int | None = None,
               personality: str | None = None, backstory: str | None = None) -> bool:
        set_clauses = []
        params: dict = {"id": id}

        if name is not None:
            set_clauses.append("npc.name = $name")
            params["name"] = name
        if age is not None:
            set_clauses.append("npc.age = $age")
            params["age"] = age
        if personality is not None:
            set_clauses.append("npc.personality = $personality")
            params["personality"] = personality
        if backstory is not None:
            set_clauses.append("npc.backstory = $backstory")
            params["backstory"] = backstory

        if not set_clauses:
            return False

        query = f"MATCH (npc:NPC {{id: $id}}) SET {', '.join(set_clauses)} RETURN npc"
        record = self._run_single(query, **params)
        return record is not None

    def delete(self, id: str) -> bool:
        """Delete an NPC and all its relations."""
        record = self._run_single(
            "MATCH (npc:NPC {id: $id}) RETURN npc", id=id,
        )
        if not record:
            return False
        self._run("MATCH (npc:NPC {id: $id}) DETACH DELETE npc", id=id)
        return True


class GroupRepo(BaseRepository):
    """CRUD operations for GROUP nodes."""

    def create(self, name: str) -> Group:
        formatted = name.capitalize()
        self._run("MERGE (g:GROUP {name: $name})", name=formatted)
        return Group(name=formatted)

    def list_all(self) -> list[Group]:
        records = self._run(
            "MATCH (g:GROUP) RETURN g.name AS name ORDER BY g.name"
        )
        return [Group(name=r["name"]) for r in records]

    def delete(self, name: str) -> bool:
        record = self._run_single(
            "MATCH (g:GROUP {name: $name}) RETURN g", name=name,
        )
        if not record:
            return False
        self._run("MATCH (g:GROUP {name: $name}) DETACH DELETE g", name=name)
        return True
