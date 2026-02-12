from typing import Any

from neo4j import Driver, Record


class BaseRepository:
    """Base class for all repositories. Provides driver access and query helpers."""

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def _run(self, query: str, **params: Any) -> list[Record]:
        """Execute a query and return all records."""
        with self._driver.session() as session:
            result = session.run(query, parameters=params)  # pyright: ignore[reportArgumentType]
            return list(result)

    def _run_single(self, query: str, **params: Any) -> Record | None:
        """Execute a query and return the first record, or None."""
        with self._driver.session() as session:
            result = session.run(query, parameters=params)  # pyright: ignore[reportArgumentType]
            return result.single()
