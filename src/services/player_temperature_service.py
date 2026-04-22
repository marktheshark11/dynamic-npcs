import re

from db.repositories import PlayerTemperatureRepo
from llms.config import DEFAULT_CHAT_TEMPERATURE, PLAYER_TEMPERATURE_RANDOMIZATION_ENABLED


def infer_temperature_override_from_player_name(name: str) -> float | None:
    match = re.fullmatch(r"temp(?P<temperature>\d+(?:\.\d+)?)", name.strip().lower())
    if not match:
        return None

    inferred_temperature = float(match.group("temperature"))
    if 0.0 <= inferred_temperature <= 2.0:
        return inferred_temperature
    return None


class PlayerTemperatureService:
    def __init__(self, repo: PlayerTemperatureRepo) -> None:
        self._repo = repo

    def resolve_for_new_player(self, name: str) -> float:
        override_temperature = infer_temperature_override_from_player_name(name)
        if override_temperature is not None:
            return override_temperature
        if not PLAYER_TEMPERATURE_RANDOMIZATION_ENABLED:
            return DEFAULT_CHAT_TEMPERATURE
        return self._repo.draw_next_temperature()
