from .base import Command
from ..repositories import ConstantRepo
from ..models import Object, Place
from ..ui import InputHelpers


class CreateObjectCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa ett nytt OBJECT"

    def execute(self) -> None:
        name = self._ui.prompt("objektnamn")
        obj = self._repo.create_object(name)
        self._ui.display.success(f"OBJECT '{obj.name}' skapad")


class CreatePlaceCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny PLACE"

    def execute(self) -> None:
        name = self._ui.prompt("platsnamn")
        place = self._repo.create_place(name)
        self._ui.display.success(f"PLACE '{place.name}' skapad")


class ListConstantsCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla objekt och platser"

    def execute(self) -> None:
        items = self._repo.list_all()
        if not items:
            self._ui.display.error("Inga objekt eller platser hittades")
            return

        self._ui.display.header("Alla konstanter")
        for idx, item in enumerate(items, 1):
            print(f"  {idx}. {item.display_str()}")
