from .base import Command
from ..repositories import ConstantRepo
from ..models import Door, Item, Object, Place
from ..ui import InputHelpers


class CreateObjectCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa ett nytt OBJECT"

    def execute(self) -> None:
        object_id = self._ui.prompt("object_id")
        name = self._ui.prompt("objektnamn")
        try:
            obj = self._repo.create_object(name, object_id=object_id)
        except ValueError as exc:
            self._ui.display.error(str(exc))
            return
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
        object_id = self._ui.prompt("item_id")
        name = self._ui.prompt("itemnamn")
        inspect_text = self._ui.prompt("inspect_text")
        pickupable = self._ui.confirm("Ska itemet kunna plockas upp?")
        try:
            item = self._repo.create_item(name, inspect_text, pickupable, object_id=object_id)
        except ValueError as exc:
            self._ui.display.error(str(exc))
            return
        pickup_text = "pickupbart" if item.pickupable else "inspect-only"
        self._ui.display.success(
            f"ITEM '{item.name}' skapad med ID '{item.object_id}' ({pickup_text})"
        )


class CreateDoorCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny DOOR"

    def execute(self) -> None:
        object_id = self._ui.prompt("door_id")
        name = self._ui.prompt("dörrnamn")
        inspect_text = self._ui.prompt("inspect_text")
        is_locked = self._ui.confirm("Ska dörren vara låst?")
        try:
            door = self._repo.create_door(name, inspect_text, is_locked, object_id=object_id)
        except ValueError as exc:
            self._ui.display.error(str(exc))
            return
        lock_text = "låst" if door.is_locked else "olåst"
        self._ui.display.success(
            f"DOOR '{door.name}' skapad med ID '{door.object_id}' ({lock_text})"
        )


class EditItemCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera ett ITEM"

    def execute(self) -> None:
        items = self._repo.list_items()
        selected = self._ui.select_from_list(items, Item.display_str, "Alla items")
        if not selected:
            return

        object_id = self._ui.prompt_optional("object_id")
        name = self._ui.prompt_optional("itemnamn")
        inspect_text = self._ui.prompt_optional("inspect_text")
        pickup_option = self._ui.select_option(
            ["ingen andring", "pickupbar", "inspect-only"],
            "Pickup-status",
        )
        if pickup_option is None:
            return

        pickupable: bool | None = None
        if pickup_option == "pickupbar":
            pickupable = True
        elif pickup_option == "inspect-only":
            pickupable = False

        try:
            updated = self._repo.update_item(
                current_object_id=selected.object_id,
                object_id=object_id,
                name=name,
                inspect_text=inspect_text,
                pickupable=pickupable,
            )
        except ValueError as exc:
            self._ui.display.error(str(exc))
            return

        if updated:
            self._ui.display.success(f"ITEM '{selected.object_id}' uppdaterat")
        else:
            self._ui.display.error("Kunde inte uppdatera itemet")


class EditDoorCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera en DOOR"

    def execute(self) -> None:
        doors = self._repo.list_doors()
        selected = self._ui.select_from_list(doors, Door.display_str, "Alla dörrar")
        if not selected:
            return

        object_id = self._ui.prompt_optional("object_id")
        name = self._ui.prompt_optional("dörrnamn")
        inspect_text = self._ui.prompt_optional("inspect_text")
        lock_option = self._ui.select_option(
            ["ingen ändring", "låst", "olåst"],
            "Låsstatus",
        )
        if lock_option is None:
            return

        is_locked: bool | None = None
        if lock_option == "låst":
            is_locked = True
        elif lock_option == "olåst":
            is_locked = False

        try:
            updated = self._repo.update_door(
                current_object_id=selected.object_id,
                object_id=object_id,
                name=name,
                inspect_text=inspect_text,
                is_locked=is_locked,
            )
        except ValueError as exc:
            self._ui.display.error(str(exc))
            return

        if updated:
            self._ui.display.success(f"DOOR '{selected.object_id}' uppdaterad")
        else:
            self._ui.display.error("Kunde inte uppdatera dörren")


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


class DeleteDoorCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en DOOR"

    def execute(self) -> None:
        doors = self._repo.list_doors()
        selected = self._ui.select_from_list(doors, Door.display_str, "Alla dörrar")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort DOOR '{selected.object_id}' ({selected.name})?"):
            if self._repo.delete_door(selected.object_id):
                self._ui.display.success(f"DOOR '{selected.object_id}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort dörren")


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


class ListDoorsCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla dörrar"

    def execute(self) -> None:
        doors = self._repo.list_doors()
        if not doors:
            self._ui.display.error("Inga dörrar hittades")
            return

        self._ui.display.header("Alla dörrar")
        for idx, door in enumerate(doors, 1):
            lock_text = "låst" if door.is_locked else "olåst"
            print(
                f"  {idx}. {door.display_str()} | inspect: {door.inspect_text} | {lock_text}"
            )
