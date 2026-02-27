from dataclasses import dataclass


@dataclass
class NPC:
    id: str
    name: str
    age: int
    personality: str
    status: str
    story_background: str | None = None

    def display_str(self) -> str:
        return f"ID: {self.id}, Namn: {self.name}, Ålder: {self.age}, Personlighet: {self.personality}, Status: {self.status}"

    def short_str(self) -> str:
        return f"ID: {self.id}, Namn: {self.name}"


@dataclass
class Group:
    name: str

    def display_str(self) -> str:
        return f"Namn: {self.name}"

    def short_str(self) -> str:
        return self.name
