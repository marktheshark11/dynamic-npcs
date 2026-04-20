from dataclasses import dataclass


@dataclass
class Player:
    player_id: str
    name: str
    appearance: str | None = None
    temperature: float | None = None

    def display_str(self) -> str:
        return (
            f"ID: {self.player_id}, Namn: {self.name}, Utseende: {self.appearance}, "
            f"Temperature: {self.temperature}"
        )

    def short_str(self) -> str:
        return f"ID: {self.player_id}, Namn: {self.name}"
