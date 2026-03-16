from .base import BaseRepository
from ..models import Door, Item, Object, Place


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

    def _backfill_missing_object_ids(
        self,
        prefix: str,
        match_clause: str,
        extra_where_clause: str = "",
    ) -> None:
        records = self._run(
            f"MATCH (o:OBJECT{match_clause}) "
            f"WHERE o.object_id IS NULL{extra_where_clause} "
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
        self._backfill_missing_object_ids("door", ":DOOR")
        self._backfill_missing_object_ids("object", "", " AND NOT o:ITEM AND NOT o:DOOR")

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

    def create_door(
        self,
        name: str,
        inspect_text: str,
        is_locked: bool,
        object_id: str | None = None,
    ) -> Door:
        self._ensure_object_ids()
        formatted = name.capitalize()
        normalized_id = (object_id or "").strip() or None
        existing = self._run_single(
            "MATCH (o:OBJECT {name: $name}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.is_locked AS is_locked "
            "LIMIT 1",
            name=formatted,
        )
        if existing and normalized_id and existing["object_id"] != normalized_id:
            raise ValueError("Det finns redan ett objekt med samma namn men annat ID")

        final_object_id = normalized_id or (existing["object_id"] if existing else self._next_object_id("door"))
        conflicting = self._run_single(
            "MATCH (o:OBJECT {object_id: $object_id}) RETURN o.name AS name LIMIT 1",
            object_id=final_object_id,
        )
        if conflicting and (not existing or conflicting["name"] != formatted):
            raise ValueError("Det finns redan ett objekt med samma ID")

        self._run(
            "MERGE (o:OBJECT {name: $name}) "
            "ON CREATE SET o.object_id = $object_id "
            "SET o:DOOR, o.inspect_text = $inspect_text, o.is_locked = $is_locked",
            object_id=final_object_id,
            name=formatted,
            inspect_text=inspect_text,
            is_locked=is_locked,
        )
        return Door(
            object_id=final_object_id,
            name=formatted,
            inspect_text=inspect_text,
            is_locked=is_locked,
        )

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

    def list_doors(self) -> list[Door]:
        self._ensure_object_ids()
        records = self._run(
            "MATCH (o:OBJECT:DOOR) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.is_locked AS is_locked "
            "ORDER BY o.object_id"
        )
        return [
            Door(
                object_id=r["object_id"],
                name=r["name"],
                inspect_text=r.get("inspect_text") or "",
                is_locked=bool(r.get("is_locked")),
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

    def get_door(self, object_id: str) -> Door | None:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (o:OBJECT:DOOR {object_id: $object_id}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.is_locked AS is_locked "
            "LIMIT 1",
            object_id=object_id,
        )
        if not record:
            return None
        return Door(
            object_id=record["object_id"],
            name=record["name"],
            inspect_text=record.get("inspect_text") or "",
            is_locked=bool(record.get("is_locked")),
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

    def delete_door(self, object_id: str) -> bool:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (o:OBJECT:DOOR {object_id: $object_id}) RETURN o", object_id=object_id,
        )
        if not record:
            return False
        self._run("MATCH (o:OBJECT:DOOR {object_id: $object_id}) DETACH DELETE o", object_id=object_id)
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

    def update_door(
        self,
        current_object_id: str,
        object_id: str | None = None,
        name: str | None = None,
        inspect_text: str | None = None,
        is_locked: bool | None = None,
    ) -> bool:
        self._ensure_object_ids()
        existing = self._run_single(
            "MATCH (o:OBJECT:DOOR {object_id: $current_object_id}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.is_locked AS is_locked "
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

        if is_locked is not None:
            set_clauses.append("o.is_locked = $is_locked")
            params["is_locked"] = is_locked

        record = self._run_single(
            f"MATCH (o:OBJECT:DOOR {{object_id: $current_object_id}}) SET {', '.join(set_clauses)} RETURN o",
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

    def list_all(self) -> list[Object | Door | Item | Place]:
        """List all OBJECTs and PLACEs together."""
        self._ensure_object_ids()
        records = self._run(
            "MATCH (c) WHERE c:OBJECT OR c:PLACE "
            "RETURN c:OBJECT AS is_object, c:ITEM AS is_item, c:DOOR AS is_door, "
            "c.object_id AS object_id, c.name AS name, c.inspect_text AS inspect_text, "
            "c.pickupable AS pickupable, c.is_locked AS is_locked "
            "ORDER BY labels(c)[0], c.object_id, c.name"
        )
        items: list[Object | Door | Item | Place] = []
        for r in records:
            if r["is_item"]:
                items.append(
                    Item(
                        object_id=r.get("object_id") or "",
                        name=r["name"],
                        inspect_text=r.get("inspect_text") or "",
                        pickupable=bool(r.get("pickupable")),
                    )
                )
            elif r["is_door"]:
                items.append(
                    Door(
                        object_id=r.get("object_id") or "",
                        name=r["name"],
                        inspect_text=r.get("inspect_text") or "",
                        is_locked=bool(r.get("is_locked")),
                    )
                )
            elif r["is_object"]:
                items.append(Object(object_id=r.get("object_id") or "", name=r["name"]))
            else:
                items.append(Place(name=r["name"]))
        return items
