from typing import TypeVar, Callable, Optional

from .display import Display

T = TypeVar("T")


class InputHelpers:
    """Reusable validated-input helpers for the terminal UI."""

    def __init__(self) -> None:
        self.display = Display()

    # --- Basic prompts ---

    def prompt(self, label: str) -> str:
        """Prompt for a non-empty string."""
        while True:
            value = input(f"{label}: ").strip()
            if not value:
                value = ''
            return value
            # self.display.error("Vardet far inte vara tomt")

    def prompt_optional(self, label: str) -> Optional[str]:
        """Prompt for an optional string (empty = None)."""
        value = input(f"{label} (lamna tom for ingen andring): ").strip()
        return value if value else None

    def prompt_int(self, label: str) -> int:
        """Prompt for an integer."""
        while True:
            raw = input(f"{label}: ").strip()
            try:
                return int(raw)
            except ValueError:
                self.display.error("Ange ett heltal")

    def prompt_optional_int(self, label: str) -> Optional[int]:
        """Prompt for an optional integer (empty = None)."""
        raw = input(f"{label} (lamna tom for ingen andring): ").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            self.display.error("Ogiltigt tal, ingen andring gjord")
            return None

    def prompt_float(self, label: str, min_val: float = -1.0,
                     max_val: float = 1.0) -> float:
        """Prompt for a float within a range."""
        while True:
            raw = input(f"{label} ({min_val} till {max_val}): ").strip()
            try:
                value = float(raw)
                if min_val <= value <= max_val:
                    return value
                self.display.error(f"Vardet maste vara mellan {min_val} och {max_val}")
            except ValueError:
                self.display.error("Ange ett tal")

    def confirm(self, message: str) -> bool:
        """Ask for yes/no confirmation."""
        response = input(f"\n{message} (j/n): ").strip().lower()
        return response == "j"

    # --- List selection ---

    def select_from_list(self, items: list[T], display_fn: Callable[[T], str],
                         title: str = "Valj") -> Optional[T]:
        """Display a numbered list and let the user pick one item.

        Returns the selected item, or None if the list is empty.
        """
        if not items:
            self.display.error("Inga objekt hittades")
            return None

        self.display.header(title)
        self.display.list_items(items, display_fn)

        choice = input(f"\nValj nummer (1-{len(items)}): ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(items):
                return items[idx - 1]
        except ValueError:
            pass

        self.display.error("Ogiltigt val")
        return None

    def select_option(self, options: list[str], title: str = "Valj") -> Optional[str]:
        """Display a list of string options and return the selected one."""
        return self.select_from_list(options, lambda x: x, title)
