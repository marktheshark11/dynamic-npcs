from abc import ABC, abstractmethod


class Command(ABC):
    """Abstract base for all menu commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name shown in the menu."""
        ...

    @abstractmethod
    def execute(self) -> None:
        """Run the command (interactive, may prompt for input)."""
        ...
