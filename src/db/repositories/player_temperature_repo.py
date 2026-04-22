import random

from .base import BaseRepository


class PlayerTemperatureRepo(BaseRepository):
    CONFIG_ID = "default"

    @staticmethod
    def _normalize_values(values: list[float] | tuple[float, ...]) -> list[float]:
        normalized_values = [float(value) for value in values]
        if not normalized_values:
            raise ValueError("Temperature-värden får inte vara tomma")
        for value in normalized_values:
            if not 0.0 <= value <= 2.0:
                raise ValueError("Temperature-värden måste vara mellan 0.0 och 2.0")
        return normalized_values

    def get_config(self) -> dict | None:
        record = self._run_single(
            "MATCH (c:PLAYER_TEMPERATURE_CONFIG {config_id: $config_id}) "
            "RETURN c.values AS values, c.remaining_values AS remaining_values "
            "LIMIT 1",
            config_id=self.CONFIG_ID,
        )
        if not record:
            return None
        return {
            "values": [float(value) for value in (record.get("values") or [])],
            "remaining_values": [float(value) for value in (record.get("remaining_values") or [])],
        }

    def upsert_values(self, values: list[float] | tuple[float, ...]) -> dict:
        normalized_values = self._normalize_values(values)
        self._run(
            "MERGE (c:PLAYER_TEMPERATURE_CONFIG {config_id: $config_id}) "
            "SET c.values = $values, c.remaining_values = []",
            config_id=self.CONFIG_ID,
            values=normalized_values,
        )
        return {
            "values": normalized_values,
            "remaining_values": [],
        }

    def clear_remaining_values(self) -> bool:
        record = self._run_single(
            "MATCH (c:PLAYER_TEMPERATURE_CONFIG {config_id: $config_id}) "
            "SET c.remaining_values = [] "
            "RETURN c.config_id AS config_id",
            config_id=self.CONFIG_ID,
        )
        return record is not None

    def draw_next_temperature(self) -> float:
        with self._driver.session() as session:
            return session.execute_write(self._draw_next_temperature_tx)

    @classmethod
    def _draw_next_temperature_tx(cls, tx) -> float:
        record = tx.run(
            "MATCH (c:PLAYER_TEMPERATURE_CONFIG {config_id: $config_id}) "
            "RETURN c.values AS values, c.remaining_values AS remaining_values "
            "LIMIT 1",
            config_id=cls.CONFIG_ID,
        ).single()
        if not record:
            raise RuntimeError("Player temperature-config saknas")

        values = cls._normalize_values(record.get("values") or [])
        remaining_values = [float(value) for value in (record.get("remaining_values") or [])]

        if not remaining_values:
            remaining_values = values.copy()
            random.shuffle(remaining_values)

        next_temperature = float(remaining_values.pop(0))
        tx.run(
            "MATCH (c:PLAYER_TEMPERATURE_CONFIG {config_id: $config_id}) "
            "SET c.remaining_values = $remaining_values",
            config_id=cls.CONFIG_ID,
            remaining_values=remaining_values,
        )
        return next_temperature
