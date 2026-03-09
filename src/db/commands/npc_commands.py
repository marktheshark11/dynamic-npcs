from .base import Command
from ..repositories import NPCRepo
from ..models import NPC
from ..ui import InputHelpers


class CreateNPCCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny NPC"

    def execute(self) -> None:
        id_val = self._ui.prompt("id")
        name_val = self._ui.prompt("namn")
        age_val = self._ui.prompt_int("ålder")
        personality_val = self._ui.prompt("personlighet")
        status_val = self._ui.prompt("status (levande, död, okänd)")
        story_background_val = self._ui.prompt("story_background (sammanfattning av vad som har hänt)")

        npc = NPC(
            id=id_val,
            name=name_val,
            age=age_val,
            personality=personality_val,
            status=status_val,
            story_background=story_background_val,
        )
        self._repo.create(npc)
        self._ui.display.success(f"NPC '{name_val}' skapad")


class EditNPCCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera en NPC"

    def execute(self) -> None:
        npcs = self._repo.list_all()
        selected = self._ui.select_from_list(npcs, NPC.display_str, "Alla NPCs")
        if not selected:
            return

        name_val = self._ui.prompt_optional("namn")
        age_val = self._ui.prompt_optional_int("ålder")
        personality_val = self._ui.prompt_optional("personlighet")
        status_val = self._ui.prompt_optional("status (levande, död, okänd)")
        story_background_val = self._ui.prompt_optional("story_background (sammanfattning av vad som har hänt)")

        if self._repo.update(
            selected.id,
            name_val,
            age_val,
            personality_val,
            status_val,
            story_background_val,
        ):
            self._ui.display.success(f"NPC '{selected.id}' uppdaterad")
        else:
            self._ui.display.error("Inga ändringar gjorda")


class DeleteNPCCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en NPC"

    def execute(self) -> None:
        npcs = self._repo.list_all()
        selected = self._ui.select_from_list(npcs, NPC.display_str, "Alla NPCs")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort NPC '{selected.name}'?"):
            if self._repo.delete(selected.id):
                self._ui.display.success(f"NPC '{selected.name}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort NPC")


class ListNPCsCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla NPCs"

    def execute(self) -> None:
        npcs = self._repo.list_all()
        if not npcs:
            self._ui.display.error("Inga NPCs hittades")
            return
        self._ui.display.header("Alla NPCs")
        self._ui.display.list_items(npcs, NPC.display_str)
