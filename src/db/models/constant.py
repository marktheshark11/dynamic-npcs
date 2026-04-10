from dataclasses import dataclass


@dataclass
class Object:
    object_id: str
    name: str
    name_en: str | None = None

    def display_str(self) -> str:
        return f"[OBJECT] {self.object_id} | {self.name}"

    def short_str(self) -> str:
        return f"{self.object_id} | {self.name}"


@dataclass
class Item:
    object_id: str
    name: str
    inspect_text: str
    pickupable: bool
    name_en: str | None = None
    inspect_text_en: str | None = None

    def display_str(self) -> str:
        pickup_state = "pickupbar" if self.pickupable else "inspect-only"
        return f"[ITEM] {self.object_id} | {self.name} | {pickup_state}"

    def short_str(self) -> str:
        return f"{self.object_id} | {self.name}"


@dataclass
class Door:
    object_id: str
    name: str
    inspect_text: str
    is_locked: bool
    lock_type: str = "none"
    unlock_code: str | None = None
    required_item_id: str | None = None
    name_en: str | None = None
    inspect_text_en: str | None = None

    def display_str(self) -> str:
        lock_state = "låst" if self.is_locked else "olåst"
        return f"[DOOR] {self.object_id} | {self.name} | {lock_state} | {self.lock_type}"

    def short_str(self) -> str:
        return f"{self.object_id} | {self.name}"


@dataclass
class Place:
    name: str
    name_en: str | None = None

    def display_str(self) -> str:
        return f"[PLACE] {self.name}"

    def short_str(self) -> str:
        return self.name
