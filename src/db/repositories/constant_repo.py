from .base import BaseRepository
from ..models import Door, Item, Object, Place


class ConstantRepo(BaseRepository):
    """CRUD operations for OBJECT and PLACE nodes."""

    DOOR_LOCK_TYPES = {"none", "item", "code"}

    @classmethod
    def _normalize_door_lock_config(
        cls,
        is_locked: bool,
        lock_type: str | None = None,
        unlock_code: str | None = None,
        required_item_id: str | None = None,
    ) -> tuple[bool, str, str | None, str | None]:
        normalized_lock_type = (lock_type or "none").strip().lower()
        normalized_code = (unlock_code or "").strip() or None
        normalized_item_id = (required_item_id or "").strip() or None

        if normalized_lock_type not in cls.DOOR_LOCK_TYPES:
            raise ValueError("Ogiltig låstyp för dörr")

        if not is_locked:
            return False, "none", None, None

        if normalized_lock_type == "none":
            raise ValueError("Låsta dörrar måste ha låstyp 'item' eller 'code'")

        if normalized_lock_type == "item":
            if not normalized_item_id:
                raise ValueError("Låstyp 'item' kräver ett item_id")
            return True, normalized_lock_type, None, normalized_item_id

        if not normalized_code:
            raise ValueError("Låstyp 'code' kräver en unlock_code")
        return True, normalized_lock_type, normalized_code, None

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

    def create_object(self, name: str, object_id: str | None = None, name_en: str | None = None) -> Object:
        self._ensure_object_ids()
        formatted = name.capitalize()
        normalized_id = (object_id or "").strip() or None
        existing = self._run_single(
            "MATCH (o:OBJECT {name: $name}) RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en LIMIT 1",
            name=formatted,
        )
        if existing:
            if normalized_id and existing["object_id"] != normalized_id:
                raise ValueError("Det finns redan ett objekt med samma namn men annat ID")
            return Object(object_id=existing["object_id"], name=existing["name"], name_en=existing.get("name_en"))

        final_object_id = normalized_id or self._next_object_id("object")
        conflicting = self._run_single(
            "MATCH (o:OBJECT {object_id: $object_id}) RETURN o.name AS name LIMIT 1",
            object_id=final_object_id,
        )
        if conflicting:
            raise ValueError("Det finns redan ett objekt med samma ID")

        self._run(
            "CREATE (o:OBJECT {object_id: $object_id, name: $name, name_en: $name_en})",
            object_id=final_object_id,
            name=formatted,
            name_en=name_en,
        )
        return Object(object_id=final_object_id, name=formatted, name_en=name_en)

    def list_objects(self) -> list[Object]:
        self._ensure_object_ids()
        records = self._run(
            "MATCH (o:OBJECT) RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en ORDER BY o.object_id"
        )
        return [Object(object_id=r["object_id"], name=r["name"], name_en=r.get("name_en")) for r in records]

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
        name_en: str | None,
        inspect_text: str,
        inspect_text_en: str | None,
        is_locked: bool,
        lock_type: str = "none",
        unlock_code: str | None = None,
        required_item_id: str | None = None,
        object_id: str | None = None,
    ) -> Door:
        self._ensure_object_ids()
        normalized_is_locked, normalized_lock_type, normalized_code, normalized_item_id = self._normalize_door_lock_config(
            is_locked=is_locked,
            lock_type=lock_type,
            unlock_code=unlock_code,
            required_item_id=required_item_id,
        )
        if normalized_item_id:
            required_item = self.get_item(normalized_item_id)
            if not required_item:
                raise ValueError("Kunde inte hitta itemet som krävs för dörren")
        formatted = name.capitalize()
        normalized_id = (object_id or "").strip() or None
        existing = self._run_single(
            "MATCH (o:OBJECT {name: $name}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.is_locked AS is_locked, "
            "       o.lock_type AS lock_type, o.unlock_code AS unlock_code "
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
            "SET o:DOOR, o.name_en = $name_en, o.inspect_text = $inspect_text, o.inspect_text_en = $inspect_text_en, o.is_locked = $is_locked, "
            "    o.lock_type = $lock_type, o.unlock_code = $unlock_code",
            object_id=final_object_id,
            name=formatted,
            name_en=name_en,
            inspect_text=inspect_text,
            inspect_text_en=inspect_text_en,
            is_locked=normalized_is_locked,
            lock_type=normalized_lock_type,
            unlock_code=normalized_code,
        )
        self._run(
            "MATCH (d:OBJECT:DOOR {object_id: $object_id})-[r:REQUIRES_ITEM]->(:OBJECT:ITEM) DELETE r",
            object_id=final_object_id,
        )
        if normalized_item_id:
            self._run(
                "MATCH (d:OBJECT:DOOR {object_id: $door_id}) "
                "MATCH (i:OBJECT:ITEM {object_id: $item_id}) "
                "MERGE (d)-[:REQUIRES_ITEM]->(i)",
                door_id=final_object_id,
                item_id=normalized_item_id,
            )
        return Door(
            object_id=final_object_id,
            name=formatted,
            name_en=name_en,
            inspect_text=inspect_text,
            inspect_text_en=inspect_text_en,
            is_locked=normalized_is_locked,
            lock_type=normalized_lock_type,
            unlock_code=normalized_code,
            required_item_id=normalized_item_id,
        )

    def create_item(
        self,
        name: str,
        name_en: str | None,
        inspect_text: str,
        inspect_text_en: str | None,
        pickupable: bool,
        object_id: str | None = None,
    ) -> Item:
        self._ensure_object_ids()
        formatted = name.capitalize()
        normalized_id = (object_id or "").strip() or None
        existing = self._run_single(
            "MATCH (o:OBJECT {name: $name}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.pickupable AS pickupable "
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
            "SET o:ITEM, o.name_en = $name_en, o.inspect_text = $inspect_text, o.inspect_text_en = $inspect_text_en, o.pickupable = $pickupable",
            object_id=final_object_id,
            name=formatted,
            name_en=name_en,
            inspect_text=inspect_text,
            inspect_text_en=inspect_text_en,
            pickupable=pickupable,
        )
        return Item(
            object_id=final_object_id,
            name=formatted,
            name_en=name_en,
            inspect_text=inspect_text,
            inspect_text_en=inspect_text_en,
            pickupable=pickupable,
        )

    def list_items(self) -> list[Item]:
        self._ensure_object_ids()
        records = self._run(
            "MATCH (o:OBJECT:ITEM) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.pickupable AS pickupable "
            "ORDER BY o.object_id"
        )
        return [
            Item(
                object_id=r["object_id"],
                name=r["name"],
                name_en=r.get("name_en"),
                inspect_text=r.get("inspect_text") or "",
                inspect_text_en=r.get("inspect_text_en"),
                pickupable=bool(r.get("pickupable")),
            )
            for r in records
        ]

    def list_doors(self) -> list[Door]:
        self._ensure_object_ids()
        records = self._run(
            "MATCH (o:OBJECT:DOOR) "
            "OPTIONAL MATCH (o)-[:REQUIRES_ITEM]->(required:OBJECT:ITEM) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.is_locked AS is_locked, "
            "       o.lock_type AS lock_type, o.unlock_code AS unlock_code, required.object_id AS required_item_id "
            "ORDER BY o.object_id"
        )
        return [
            Door(
                object_id=r["object_id"],
                name=r["name"],
                name_en=r.get("name_en"),
                inspect_text=r.get("inspect_text") or "",
                inspect_text_en=r.get("inspect_text_en"),
                is_locked=bool(r.get("is_locked")),
                lock_type=(r.get("lock_type") or "none"),
                unlock_code=r.get("unlock_code"),
                required_item_id=r.get("required_item_id"),
            )
            for r in records
        ]

    def get_item(self, object_id: str) -> Item | None:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (o:OBJECT:ITEM {object_id: $object_id}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.pickupable AS pickupable "
            "LIMIT 1",
            object_id=object_id,
        )
        if not record:
            return None
        return Item(
            object_id=record["object_id"],
            name=record["name"],
            name_en=record.get("name_en"),
            inspect_text=record.get("inspect_text") or "",
            inspect_text_en=record.get("inspect_text_en"),
            pickupable=bool(record.get("pickupable")),
        )

    def get_door(self, object_id: str) -> Door | None:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (o:OBJECT:DOOR {object_id: $object_id}) "
            "OPTIONAL MATCH (o)-[:REQUIRES_ITEM]->(required:OBJECT:ITEM) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.is_locked AS is_locked, "
            "       o.lock_type AS lock_type, o.unlock_code AS unlock_code, required.object_id AS required_item_id "
            "LIMIT 1",
            object_id=object_id,
        )
        if not record:
            return None
        return Door(
            object_id=record["object_id"],
            name=record["name"],
            name_en=record.get("name_en"),
            inspect_text=record.get("inspect_text") or "",
            inspect_text_en=record.get("inspect_text_en"),
            is_locked=bool(record.get("is_locked")),
            lock_type=(record.get("lock_type") or "none"),
            unlock_code=record.get("unlock_code"),
            required_item_id=record.get("required_item_id"),
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
        name_en: str | None = None,
        inspect_text: str | None = None,
        inspect_text_en: str | None = None,
        pickupable: bool | None = None,
    ) -> bool:
        self._ensure_object_ids()
        existing = self._run_single(
            "MATCH (o:OBJECT:ITEM {object_id: $current_object_id}) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.pickupable AS pickupable "
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
        if name_en is not None:
            set_clauses.append("o.name_en = $name_en")
            params["name_en"] = name_en
        if inspect_text_en is not None:
            set_clauses.append("o.inspect_text_en = $inspect_text_en")
            params["inspect_text_en"] = inspect_text_en

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
        name_en: str | None = None,
        inspect_text: str | None = None,
        inspect_text_en: str | None = None,
        is_locked: bool | None = None,
        lock_type: str | None = None,
        unlock_code: str | None = None,
        required_item_id: str | None = None,
    ) -> bool:
        self._ensure_object_ids()
        existing = self._run_single(
            "MATCH (o:OBJECT:DOOR {object_id: $current_object_id}) "
            "OPTIONAL MATCH (o)-[:REQUIRES_ITEM]->(required:OBJECT:ITEM) "
            "RETURN o.object_id AS object_id, o.name AS name, o.name_en AS name_en, o.inspect_text AS inspect_text, o.inspect_text_en AS inspect_text_en, o.is_locked AS is_locked, "
            "       o.lock_type AS lock_type, o.unlock_code AS unlock_code, required.object_id AS required_item_id "
            "LIMIT 1",
            current_object_id=current_object_id,
        )
        if not existing:
            return False

        next_object_id = (object_id or "").strip() or existing["object_id"]
        next_name = name.capitalize() if name else existing["name"]
        next_is_locked = bool(existing.get("is_locked")) if is_locked is None else is_locked
        next_lock_type = lock_type if lock_type is not None else (existing.get("lock_type") or "none")
        next_unlock_code = unlock_code if unlock_code is not None else existing.get("unlock_code")
        next_required_item_id = required_item_id if required_item_id is not None else existing.get("required_item_id")
        normalized_is_locked, normalized_lock_type, normalized_code, normalized_item_id = self._normalize_door_lock_config(
            is_locked=next_is_locked,
            lock_type=next_lock_type,
            unlock_code=next_unlock_code,
            required_item_id=next_required_item_id,
        )
        if normalized_item_id:
            required_item = self.get_item(normalized_item_id)
            if not required_item:
                raise ValueError("Kunde inte hitta itemet som krävs för dörren")

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
            "o.is_locked = $is_locked",
            "o.lock_type = $lock_type",
            "o.unlock_code = $unlock_code",
        ]
        params: dict[str, str | bool | None] = {
            "current_object_id": current_object_id,
            "object_id": next_object_id,
            "name": next_name,
            "is_locked": normalized_is_locked,
            "lock_type": normalized_lock_type,
            "unlock_code": normalized_code,
        }

        if inspect_text is not None:
            set_clauses.append("o.inspect_text = $inspect_text")
            params["inspect_text"] = inspect_text
        if name_en is not None:
            set_clauses.append("o.name_en = $name_en")
            params["name_en"] = name_en
        if inspect_text_en is not None:
            set_clauses.append("o.inspect_text_en = $inspect_text_en")
            params["inspect_text_en"] = inspect_text_en

        record = self._run_single(
            f"MATCH (o:OBJECT:DOOR {{object_id: $current_object_id}}) SET {', '.join(set_clauses)} RETURN o",
            **params,
        )
        if not record:
            return False
        self._run(
            "MATCH (d:OBJECT:DOOR {object_id: $object_id})-[r:REQUIRES_ITEM]->(:OBJECT:ITEM) DELETE r",
            object_id=next_object_id,
        )
        if normalized_item_id:
            self._run(
                "MATCH (d:OBJECT:DOOR {object_id: $door_id}) "
                "MATCH (i:OBJECT:ITEM {object_id: $item_id}) "
                "MERGE (d)-[:REQUIRES_ITEM]->(i)",
                door_id=next_object_id,
                item_id=normalized_item_id,
            )
        return True

    def get_required_item_for_door(self, object_id: str) -> Item | None:
        self._ensure_object_ids()
        record = self._run_single(
            "MATCH (:OBJECT:DOOR {object_id: $object_id})-[:REQUIRES_ITEM]->(i:OBJECT:ITEM) "
            "RETURN i.object_id AS object_id, i.name AS name, i.name_en AS name_en, i.inspect_text AS inspect_text, i.inspect_text_en AS inspect_text_en, i.pickupable AS pickupable "
            "LIMIT 1",
            object_id=object_id,
        )
        if not record:
            return None
        return Item(
            object_id=record["object_id"],
            name=record["name"],
            name_en=record.get("name_en"),
            inspect_text=record.get("inspect_text") or "",
            inspect_text_en=record.get("inspect_text_en"),
            pickupable=bool(record.get("pickupable")),
        )

    # --- PLACE ---

    def create_place(self, name: str, name_en: str | None = None) -> Place:
        formatted = name.capitalize()
        self._run("MERGE (p:PLACE {name: $name}) SET p.name_en = $name_en", name=formatted, name_en=name_en)
        return Place(name=formatted, name_en=name_en)

    def list_places(self) -> list[Place]:
        records = self._run(
            "MATCH (p:PLACE) RETURN p.name AS name, p.name_en AS name_en ORDER BY p.name"
        )
        return [Place(name=r["name"], name_en=r.get("name_en")) for r in records]

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
            "c.object_id AS object_id, c.name AS name, c.name_en AS name_en, c.inspect_text AS inspect_text, c.inspect_text_en AS inspect_text_en, "
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
                        name_en=r.get("name_en"),
                        inspect_text=r.get("inspect_text") or "",
                        inspect_text_en=r.get("inspect_text_en"),
                        pickupable=bool(r.get("pickupable")),
                    )
                )
            elif r["is_door"]:
                items.append(
                    Door(
                        object_id=r.get("object_id") or "",
                        name=r["name"],
                        name_en=r.get("name_en"),
                        inspect_text=r.get("inspect_text") or "",
                        inspect_text_en=r.get("inspect_text_en"),
                        is_locked=bool(r.get("is_locked")),
                    )
                )
            elif r["is_object"]:
                items.append(Object(object_id=r.get("object_id") or "", name=r["name"], name_en=r.get("name_en")))
            else:
                items.append(Place(name=r["name"], name_en=r.get("name_en")))
        return items
