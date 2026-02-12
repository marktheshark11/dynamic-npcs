from __future__ import annotations
from typing import Protocol


class Executable(Protocol):
    """Any object with a name and execute method can be a menu item."""

    @property
    def name(self) -> str: ...

    def execute(self) -> None: ...


class Menu:
    """Interactive numbered menu that loops until the user exits."""

    def __init__(self, title: str, items: list[Executable]) -> None:
        self._title = title
        self._items = items

    def run(self) -> None:
        while True:
            print(f"\n=== {self._title} ===")
            for i, item in enumerate(self._items, 1):
                print(f"  {i}: {item.name}")
            print("  0: Tillbaka")

            choice = input("Valj: ").strip()
            if choice == "0":
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self._items):
                    self._items[idx].execute()
                else:
                    print("Ogiltigt val")
            except ValueError:
                print("Ogiltigt val")
            except KeyboardInterrupt:
                print("\nAvbruten")
                break


class SubMenu:
    """A menu item that opens a nested Menu when selected."""

    def __init__(self, title: str, items: list[Executable]) -> None:
        self._title = title
        self._menu = Menu(title, items)

    @property
    def name(self) -> str:
        return self._title

    def execute(self) -> None:
        self._menu.run()
