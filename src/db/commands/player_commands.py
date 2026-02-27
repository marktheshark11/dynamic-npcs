from .base import Command
from ..repositories import PlayerRepo
from ..models import Player
from ..ui import InputHelpers


class CreatePlayerCommand(Command):
    def __init__(self, repo: PlayerRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny player"

    def execute(self) -> None:
        name_val = self._ui.prompt("namn")
        appearance_val = self._ui.prompt("utseende")

        player = self._repo.create(name_val, appearance_val)
        self._ui.display.success(f"Player '{player.name}' skapad med ID '{player.player_id}'")


class EditPlayerCommand(Command):
    def __init__(self, repo: PlayerRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera en player"

    def execute(self) -> None:
        players = self._repo.list_all()
        selected = self._ui.select_from_list(players, Player.display_str, "Alla players")
        if not selected:
            return

        name_val = self._ui.prompt_optional("namn")
        appearance_val = self._ui.prompt_optional("utseende")

        if self._repo.update(selected.player_id, name_val, appearance_val):
            self._ui.display.success(f"Player '{selected.player_id}' uppdaterad")
        else:
            self._ui.display.error("Inga andringar gjorda")
