from .base import Command
from ..repositories import ConstantRepo
from ..models import Item, Object, Place
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
        self._ui.display.success(f"OBJECT '{obj.name}' skapad med ID '{obj.object_id}'")


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


class CreateItemCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa ett nytt ITEM"

    def execute(self) -> None:
        name = self._ui.prompt("itemnamn")
        inspect_text = self._ui.prompt("inspect_text")
        pickupable = self._ui.confirm("Ska itemet kunna plockas upp?")
        item = self._repo.create_item(name, inspect_text, pickupable)
        pickup_text = "pickupbart" if item.pickupable else "inspect-only"
        self._ui.display.success(
            f"ITEM '{item.name}' skapad med ID '{item.object_id}' ({pickup_text})"
        )


class DeleteObjectCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort ett OBJECT"

    def execute(self) -> None:
        objects = self._repo.list_objects()
        selected = self._ui.select_from_list(objects, Object.display_str, "Alla objekt")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort OBJECT '{selected.object_id}' ({selected.name})?"):
            if self._repo.delete_object(selected.object_id):
                self._ui.display.success(f"OBJECT '{selected.object_id}' borttaget")
            else:
                self._ui.display.error("Kunde inte ta bort objektet")


class DeletePlaceCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort ett PLACE"

    def execute(self) -> None:
        places = self._repo.list_places()
        selected = self._ui.select_from_list(places, Place.display_str, "Alla platser")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort PLACE '{selected.name}'?"):
            if self._repo.delete_place(selected.name):
                self._ui.display.success(f"PLACE '{selected.name}' borttaget")
            else:
                self._ui.display.error("Kunde inte ta bort platsen")


class DeleteItemCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort ett ITEM"

    def execute(self) -> None:
        items = self._repo.list_items()
        selected = self._ui.select_from_list(items, Item.display_str, "Alla items")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort ITEM '{selected.object_id}' ({selected.name})?"):
            if self._repo.delete_item(selected.object_id):
                self._ui.display.success(f"ITEM '{selected.object_id}' borttaget")
            else:
                self._ui.display.error("Kunde inte ta bort itemet")


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


class ListItemsCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla items"

    def execute(self) -> None:
        items = self._repo.list_items()
        if not items:
            self._ui.display.error("Inga items hittades")
            return

        self._ui.display.header("Alla items")
        for idx, item in enumerate(items, 1):
            pickup_text = "pickupbart" if item.pickupable else "inspect-only"
            print(
                f"  {idx}. {item.display_str()} | inspect: {item.inspect_text} | {pickup_text}"
            )
