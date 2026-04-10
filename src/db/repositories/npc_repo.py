from .base import BaseRepository
from ..models import NPC, Group


class NPCRepo(BaseRepository):
    """CRUD operations for NPC nodes."""

    @staticmethod
    def _select_localized_name(record: dict, locale: str) -> str | None:
        if locale == "en":
            return record.get("name_en")
        return record.get("name")

    @staticmethod
    def _select_localized_text(record: dict, base_key: str, locale: str) -> str | None:
        if locale == "en":
            return record.get(f"{base_key}_en")
        return record.get(base_key)

    def create(self, npc: NPC) -> None:
        self._run(
            "MERGE (npc:NPC {id: $id}) "
            "SET npc.name = $name, npc.name_en = $name_en, npc.age = $age, npc.personality = $personality, "
            "npc.personality_en = $personality_en, npc.status = $status, "
            "npc.story_background = $story_background, npc.story_background_en = $story_background_en",
            id=npc.id,
            name=npc.name,
            name_en=npc.name_en,
            age=npc.age,
            personality=npc.personality,
            personality_en=npc.personality_en,
            status=npc.status,
            story_background=npc.story_background,
            story_background_en=npc.story_background_en,
        )

    def get_by_id(self, id: str, locale: str = "sv") -> NPC | None:
        record = self._run_single(
            "MATCH (npc:NPC {id: $id}) "
            "RETURN npc.id AS id, npc.name AS name, npc.name_en AS name_en, npc.age AS age, "
            "npc.personality AS personality, npc.status AS status, "
            "npc.personality_en AS personality_en, npc.story_background AS story_background, "
            "npc.story_background_en AS story_background_en",
            id=id,
        )
        if not record:
            return None
        return NPC(
            id=record["id"],
            name=self._select_localized_name(record, locale) or "",
            name_en=record.get("name_en"),
            age=record["age"],
            personality=record["personality"],
            personality_en=record.get("personality_en"),
            status=record["status"],
            story_background=record.get("story_background"),
            story_background_en=record.get("story_background_en"),
        )

    def list_all(self) -> list[NPC]:
        records = self._run(
            "MATCH (npc:NPC) "
            "RETURN npc.id AS id, npc.name AS name, npc.name_en AS name_en, npc.age AS age, "
            "npc.personality AS personality, npc.status AS status, "
            "npc.personality_en AS personality_en, npc.story_background AS story_background, "
            "npc.story_background_en AS story_background_en "
            "ORDER BY npc.id"
        )
        return [
            NPC(
                id=r["id"],
                name=r["name"],
                name_en=r.get("name_en"),
                age=r["age"],
                personality=r["personality"],
                personality_en=r.get("personality_en"),
                status=r["status"],
                story_background=r.get("story_background"),
                story_background_en=r.get("story_background_en"),
            )
            for r in records
        ]

    def list_for_selection(self) -> list[dict]:
        records = self._run(
            "MATCH (n:NPC) "
            "RETURN n.id AS id, n.name AS name, n.name_en AS name_en, n.age AS age "
            "ORDER BY n.name"
        )
        return [
            {"id": r["id"], "name": r["name"], "name_en": r.get("name_en"), "age": r.get("age")}
            for r in records
        ]

    def get_detail_by_id(self, npc_id: str, locale: str = "sv") -> dict | None:
        record = self._run_single(
            "MATCH (n:NPC {id: $npc_id}) "
            "RETURN n.id AS id, n.name AS name, n.name_en AS name_en, n.age AS age, "
            "n.personality AS personality, n.personality_en AS personality_en, "
            "n.backstory AS backstory, n.story_background AS story_background, n.story_background_en AS story_background_en "
            "LIMIT 1",
            npc_id=npc_id,
        )
        if not record:
            return None
        return {
            "id": record["id"],
            "name": self._select_localized_name(record, locale) or "",
            "name_en": record.get("name_en"),
            "age": record.get("age"),
            "personality": self._select_localized_text(record, "personality", locale),
            "personality_en": record.get("personality_en"),
            "backstory": record.get("backstory"),
            "story_background": self._select_localized_text(record, "story_background", locale),
            "story_background_en": record.get("story_background_en"),
        }

    def get_profile_by_id(self, npc_id: str, locale: str = "sv") -> dict | None:
        record = self._run_single(
            "MATCH (n:NPC {id: $npc_id}) "
            "RETURN n.name AS name, n.name_en AS name_en, n.personality AS personality, n.personality_en AS personality_en, "
            "n.backstory AS backstory, n.story_background AS story_background, n.story_background_en AS story_background_en "
            "LIMIT 1",
            npc_id=npc_id,
        )
        if not record:
            return None
        return {
            "name": self._select_localized_name(record, locale) or "",
            "name_en": record.get("name_en"),
            "personality": self._select_localized_text(record, "personality", locale),
            "personality_en": record.get("personality_en"),
            "backstory": record.get("backstory"),
            "story_background": self._select_localized_text(record, "story_background", locale),
            "story_background_en": record.get("story_background_en"),
        }

    def update(
        self,
        id: str,
        name: str | None = None,
        name_en: str | None = None,
        age: int | None = None,
        personality: str | None = None,
        personality_en: str | None = None,
        status: str | None = None,
        story_background: str | None = None,
        story_background_en: str | None = None,
    ) -> bool:
        set_clauses = []
        params: dict = {"id": id}

        if name is not None:
            set_clauses.append("npc.name = $name")
            params["name"] = name
        if name_en is not None:
            set_clauses.append("npc.name_en = $name_en")
            params["name_en"] = name_en
        if age is not None:
            set_clauses.append("npc.age = $age")
            params["age"] = age
        if personality is not None:
            set_clauses.append("npc.personality = $personality")
            params["personality"] = personality
        if personality_en is not None:
            set_clauses.append("npc.personality_en = $personality_en")
            params["personality_en"] = personality_en
        if status is not None:
            set_clauses.append("npc.status = $status")
            params["status"] = status
        if story_background is not None:
            set_clauses.append("npc.story_background = $story_background")
            params["story_background"] = story_background
        if story_background_en is not None:
            set_clauses.append("npc.story_background_en = $story_background_en")
            params["story_background_en"] = story_background_en

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
