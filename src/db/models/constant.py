from dataclasses import dataclass


@dataclass
class Object:
    object_id: str
    name: str

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

    def display_str(self) -> str:
        lock_state = "låst" if self.is_locked else "olåst"
        return f"[DOOR] {self.object_id} | {self.name} | {lock_state}"

    def short_str(self) -> str:
        return f"{self.object_id} | {self.name}"


@dataclass
class Place:
    name: str

    def display_str(self) -> str:
        return f"[PLACE] {self.name}"

    def short_str(self) -> str:
        return self.name
