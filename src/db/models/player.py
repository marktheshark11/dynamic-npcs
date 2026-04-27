from dataclasses import dataclass


@dataclass
class Player:
    player_id: str
    name: str
    appearance: str | None = None
    temperature: float | None = None
    main_player: bool = False

    def display_str(self) -> str:
        return (
            f"ID: {self.player_id}, Namn: {self.name}, Utseende: {self.appearance}, "
            f"Temperature: {self.temperature}, Main player: {self.main_player}"
        )

    def short_str(self) -> str:
        return f"ID: {self.player_id}, Namn: {self.name}"
