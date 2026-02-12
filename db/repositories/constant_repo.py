from .base import BaseRepository
from ..models import Object, Place


class ConstantRepo(BaseRepository):
    """CRUD operations for OBJECT and PLACE nodes."""

    # --- OBJECT ---

    def create_object(self, name: str) -> Object:
        formatted = name.capitalize()
        self._run("MERGE (o:OBJECT {name: $name})", name=formatted)
        return Object(name=formatted)

    def list_objects(self) -> list[Object]:
        records = self._run(
            "MATCH (o:OBJECT) RETURN o.name AS name ORDER BY o.name"
        )
        return [Object(name=r["name"]) for r in records]

    def delete_object(self, name: str) -> bool:
        record = self._run_single(
            "MATCH (o:OBJECT {name: $name}) RETURN o", name=name,
        )
        if not record:
            return False
        self._run("MATCH (o:OBJECT {name: $name}) DETACH DELETE o", name=name)
        return True

    # --- PLACE ---

    def create_place(self, name: str) -> Place:
        formatted = name.capitalize()
        self._run("MERGE (p:PLACE {name: $name})", name=formatted)
        return Place(name=formatted)

    def list_places(self) -> list[Place]:
        records = self._run(
            "MATCH (p:PLACE) RETURN p.name AS name ORDER BY p.name"
        )
        return [Place(name=r["name"]) for r in records]

    def delete_place(self, name: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLACE {name: $name}) RETURN p", name=name,
        )
        if not record:
            return False
        self._run("MATCH (p:PLACE {name: $name}) DETACH DELETE p", name=name)
        return True

    # --- Combined ---

    def list_all(self) -> list[Object | Place]:
        """List all OBJECTs and PLACEs together."""
        records = self._run(
            "MATCH (c) WHERE c:OBJECT OR c:PLACE "
            "RETURN labels(c)[0] AS label, c.name AS name "
            "ORDER BY labels(c)[0], c.name"
        )
        items: list[Object | Place] = []
        for r in records:
            if r["label"] == "OBJECT":
                items.append(Object(name=r["name"]))
            else:
                items.append(Place(name=r["name"]))
        return items
