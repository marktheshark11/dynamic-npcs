from .base import Command
from ..repositories import GroupRepo
from ..models import Group
from ..ui import InputHelpers


class CreateGroupCommand(Command):
    def __init__(self, repo: GroupRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny grupp"

    def execute(self) -> None:
        name_val = self._ui.prompt("gruppnamn")
        group = self._repo.create(name_val)
        self._ui.display.success(f"GROUP '{group.name}' skapad")


class DeleteGroupCommand(Command):
    def __init__(self, repo: GroupRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en grupp"

    def execute(self) -> None:
        groups = self._repo.list_all()
        selected = self._ui.select_from_list(groups, Group.display_str, "Alla grupper")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort GROUP '{selected.name}'?"):
            if self._repo.delete(selected.name):
                self._ui.display.success(f"GROUP '{selected.name}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort gruppen")


class ListGroupsCommand(Command):
    def __init__(self, repo: GroupRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla grupper"

    def execute(self) -> None:
        groups = self._repo.list_all()
        if not groups:
            self._ui.display.error("Inga grupper hittades")
            return
        self._ui.display.header("Alla grupper")
        self._ui.display.list_items(groups, Group.display_str)
