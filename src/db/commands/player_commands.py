from .base import Command
from ..repositories import ConstantRepo, PlayerRepo
from ..models import Item, Player
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


class DeletePlayerCommand(Command):
    def __init__(self, repo: PlayerRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en player"

    def execute(self) -> None:
        players = self._repo.list_all()
        selected = self._ui.select_from_list(players, Player.display_str, "Alla players")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort player '{selected.player_id}'?"):
            if self._repo.delete(selected.player_id):
                self._ui.display.success(f"Player '{selected.player_id}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort player")


class InspectItemCommand(Command):
    def __init__(self, player_repo: PlayerRepo, constant_repo: ConstantRepo, ui: InputHelpers) -> None:
        self._player_repo = player_repo
        self._constant_repo = constant_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Inspecta ett item som player"

    def execute(self) -> None:
        players = self._player_repo.list_all()
        selected_player = self._ui.select_from_list(players, Player.display_str, "Alla players")
        if not selected_player:
            return

        items = self._constant_repo.list_items()
        selected_item = self._ui.select_from_list(items, Item.display_str, "Alla items")
        if not selected_item:
            return

        self._player_repo.mark_seen_object(selected_player.player_id, selected_item.object_id)
        self._ui.display.header(f"Inspect: {selected_item.name}")
        print(selected_item.inspect_text)
        self._ui.display.success(
            f"Player '{selected_player.player_id}' har nu sett item '{selected_item.object_id}'"
        )


class PickupItemCommand(Command):
    def __init__(self, player_repo: PlayerRepo, constant_repo: ConstantRepo, ui: InputHelpers) -> None:
        self._player_repo = player_repo
        self._constant_repo = constant_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Plocka upp ett item som player"

    def execute(self) -> None:
        players = self._player_repo.list_all()
        selected_player = self._ui.select_from_list(players, Player.display_str, "Alla players")
        if not selected_player:
            return

        items = self._constant_repo.list_items()
        selected_item = self._ui.select_from_list(items, Item.display_str, "Alla items")
        if not selected_item:
            return

        ok, message = self._player_repo.pickup_item(selected_player.player_id, selected_item.object_id)
        if ok:
            self._ui.display.success(
                f"Player '{selected_player.player_id}' plockade upp '{selected_item.object_id}'"
            )
        else:
            self._ui.display.error(message)


class ListPlayerInventoryCommand(Command):
    def __init__(self, player_repo: PlayerRepo, ui: InputHelpers) -> None:
        self._player_repo = player_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa inventory for en player"

    def execute(self) -> None:
        players = self._player_repo.list_all()
        selected_player = self._ui.select_from_list(players, Player.display_str, "Alla players")
        if not selected_player:
            return

        items = self._player_repo.list_inventory(selected_player.player_id)
        if not items:
            self._ui.display.error("Playern har inga items i inventory")
            return

        self._ui.display.header(f"Inventory for {selected_player.player_id}")
        self._ui.display.list_items(items, Item.display_str)
