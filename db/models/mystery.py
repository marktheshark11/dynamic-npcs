from dataclasses import dataclass


@dataclass
class Mystery:
    name: str

    def display_str(self) -> str:
        return f"Mysterium: {self.name}"

    def short_str(self) -> str:
        return self.name
