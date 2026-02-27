from dataclasses import dataclass


@dataclass
class Object:
    name: str

    def display_str(self) -> str:
        return f"[OBJECT] {self.name}"

    def short_str(self) -> str:
        return self.name


@dataclass
class Place:
    name: str

    def display_str(self) -> str:
        return f"[PLACE] {self.name}"

    def short_str(self) -> str:
        return self.name
