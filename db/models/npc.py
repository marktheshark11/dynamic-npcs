from dataclasses import dataclass


@dataclass
class NPC:
    id: str
    name: str
    age: int
    personality: str
    backstory: str

    def display_str(self) -> str:
        return f"ID: {self.id}, Namn: {self.name}, Alder: {self.age}, Personlighet: {self.personality}, Backstory: {self.backstory}"

    def short_str(self) -> str:
        return f"ID: {self.id}, Namn: {self.name}"


@dataclass
class Group:
    name: str

    def display_str(self) -> str:
        return f"Namn: {self.name}"

    def short_str(self) -> str:
        return self.name
