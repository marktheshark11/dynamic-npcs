from .base import BaseRepository
from ..models import Item, Object, Place


class ConstantRepo(BaseRepository):
    """CRUD operations for OBJECT and PLACE nodes."""

    def _next_object_id(self, prefix: str) -> str:
        record = self._run_single(
            "MATCH (o:OBJECT) "
            "WITH CASE "
            "WHEN o.object_id STARTS WITH $prefix THEN toInteger(split(o.object_id, '_')[1]) "
            "ELSE NULL "
            "END AS numeric_id "
            "RETURN coalesce(max(numeric_id), 0) + 1 AS next_id",
            prefix=f"{prefix}_",
        )
        next_id = 1 if not record else record["next_id"]
        return f"{prefix}_{next_id}"

    def _backfill_missing_object_ids(self, prefix: str, match_clause: str) -> None:
        records = self._run(
            f"MATCH (o:OBJECT{match_clause}) "
            "WHERE o.object_id IS NULL "
            "RETURN elementId(o) AS element_id"
        )
        for record in records:
            object_id = self._next_object_id(prefix)
            self._run(
                "MATCH (o) WHERE elementId(o) = $element_id SET o.object_id = $object_id",
                element_id=record["element_id"],
                object_id=object_id,
            )

    def _ensure_object_ids(self) -> None:
        self._backfill_missing_object_ids("item", ":ITEM")
        self._backfill_missing_object_ids("object", "")

    # --- OBJECT ---

    def create_object(self, name: str, object_id: str | None = None) -> Object:
        self._ensure_object_ids()
        formatted = name.capitalize()
        normalized_id = (object_id or "").strip() or None
        existing = self._run_single(
            "MATCH (o:OBJECT {name: $name}) RETURN o.object_id AS object_id, o.name AS name LIMIT 1",
            name=formatted,
        )
        if existing:
            if normalized_id and existing["object_id"] != normalized_id:
                raise ValueError("Det finns redan ett objekt med samma namn men annat ID")
            return Object(object_id=existing["object_id"], name=existing["name"])

        final_object_id = normalized_id or self._next_object_id("object")
        conflicting = self._run_single(
            "MATCH (o:OBJECT {object_id: $object_id}) RETURN o.name AS name LIMIT 1",
            object_id=final_object_id,
        )
        if conflicting:
            raise ValueError("Det finns redan ett objekt med samma ID")

        self._run(
            "CREATE (o:OBJECT {object_id: $object_id, name: $name})",
            object_id=final_object_id,
            name=formatted,
        )
        return Object(object_id=final_object_id, name=formatted)

    def list_objects(self) -> list[Object]:
        self._ensure_object_ids()
        records = self._run(
            "MATCH (o:OBJECT) RETURN o.object_id AS object_id, o.name AS name ORDER BY o.object_id"
        )
        return [Object(object_id=r["object_id"], name=r["name"]) for r in records]

    def delete_object(self, object_id: str) -> bool:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (o:OBJECT {object_id: $object_id}) RETURN o", object_id=object_id,
        )
        if not record:
            return False
        self._run("MATCH (o:OBJECT {object_id: $object_id}) DETACH DELETE o", object_id=object_id)
        return True

    def create_item(
        self,
        name: str,
        inspect_text: str,
        pickupable: bool,
        object_id: str | None = None,
    ) -> Item:
        self._ensure_object_ids()
        formatted = name.capitalize()
        normalized_id = (object_id or "").strip() or None
        existing = self._run_single(
            "MATCH (o:OBJECT {name: $name}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.pickupable AS pickupable "
            "LIMIT 1",
            name=formatted,
        )
        if existing and normalized_id and existing["object_id"] != normalized_id:
            raise ValueError("Det finns redan ett objekt med samma namn men annat ID")

        final_object_id = normalized_id or (existing["object_id"] if existing else self._next_object_id("item"))
        conflicting = self._run_single(
            "MATCH (o:OBJECT {object_id: $object_id}) RETURN o.name AS name LIMIT 1",
            object_id=final_object_id,
        )
        if conflicting and (not existing or conflicting["name"] != formatted):
            raise ValueError("Det finns redan ett objekt med samma ID")

        self._run(
            "MERGE (o:OBJECT {name: $name}) "
            "ON CREATE SET o.object_id = $object_id "
            "SET o:ITEM, o.inspect_text = $inspect_text, o.pickupable = $pickupable",
            object_id=final_object_id,
            name=formatted,
            inspect_text=inspect_text,
            pickupable=pickupable,
        )
        return Item(
            object_id=final_object_id,
            name=formatted,
            inspect_text=inspect_text,
            pickupable=pickupable,
        )

    def list_items(self) -> list[Item]:
        self._ensure_object_ids()
        records = self._run(
            "MATCH (o:OBJECT:ITEM) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.pickupable AS pickupable "
            "ORDER BY o.object_id"
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

    def get_item(self, object_id: str) -> Item | None:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (o:OBJECT:ITEM {object_id: $object_id}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.pickupable AS pickupable "
            "LIMIT 1",
            object_id=object_id,
        )
        if not record:
            return None
        return Item(
            object_id=record["object_id"],
            name=record["name"],
            inspect_text=record.get("inspect_text") or "",
            pickupable=bool(record.get("pickupable")),
        )

    def delete_item(self, object_id: str) -> bool:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (o:OBJECT:ITEM {object_id: $object_id}) RETURN o", object_id=object_id,
        )
        if not record:
            return False
        self._run("MATCH (o:OBJECT:ITEM {object_id: $object_id}) DETACH DELETE o", object_id=object_id)
        return True

    def update_item(
        self,
        current_object_id: str,
        object_id: str | None = None,
        name: str | None = None,
        inspect_text: str | None = None,
        pickupable: bool | None = None,
    ) -> bool:
        self._ensure_object_ids()
        existing = self._run_single(
            "MATCH (o:OBJECT:ITEM {object_id: $current_object_id}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.pickupable AS pickupable "
            "LIMIT 1",
            current_object_id=current_object_id,
        )
        if not existing:
            return False

        next_object_id = (object_id or "").strip() or existing["object_id"]
        next_name = name.capitalize() if name else existing["name"]

        if next_object_id != existing["object_id"]:
            conflicting_id = self._run_single(
                "MATCH (o:OBJECT {object_id: $object_id}) RETURN o.name AS name LIMIT 1",
                object_id=next_object_id,
            )
            if conflicting_id:
                raise ValueError("Det finns redan ett objekt med samma ID")

        if next_name != existing["name"]:
            conflicting_name = self._run_single(
                "MATCH (o:OBJECT {name: $name}) RETURN o.object_id AS object_id LIMIT 1",
                name=next_name,
            )
            if conflicting_name and conflicting_name["object_id"] != existing["object_id"]:
                raise ValueError("Det finns redan ett objekt med samma namn")

        set_clauses = [
            "o.object_id = $object_id",
            "o.name = $name",
        ]
        params: dict[str, str | bool] = {
            "current_object_id": current_object_id,
            "object_id": next_object_id,
            "name": next_name,
        }

        if inspect_text is not None:
            set_clauses.append("o.inspect_text = $inspect_text")
            params["inspect_text"] = inspect_text

        if pickupable is not None:
            set_clauses.append("o.pickupable = $pickupable")
            params["pickupable"] = pickupable

        record = self._run_single(
            f"MATCH (o:OBJECT:ITEM {{object_id: $current_object_id}}) SET {', '.join(set_clauses)} RETURN o",
            **params,
        )
        return record is not None

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
        self._ensure_object_ids()
        records = self._run(
            "MATCH (c) WHERE c:OBJECT OR c:PLACE "
            "RETURN labels(c)[0] AS label, c.object_id AS object_id, c.name AS name "
            "ORDER BY labels(c)[0], c.object_id, c.name"
        )
        items: list[Object | Place] = []
        for r in records:
            if r["label"] == "OBJECT":
                items.append(Object(object_id=r.get("object_id") or "", name=r["name"]))
            else:
                items.append(Place(name=r["name"]))
        return items
