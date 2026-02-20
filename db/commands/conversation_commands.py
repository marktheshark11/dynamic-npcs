from .base import Command
from ..repositories import ConversationRepo
from ..ui import InputHelpers


def _conversation_display(item: dict) -> str:
    return (
        f"{item['conv_id']} | npc: {item['npc_id']} | "
        f"turns: {item.get('exchange_count', 0)} | "
        f"created: {item.get('created_at') or '-'}"
    )


class ListConversationsCommand(Command):
    def __init__(self, repo: ConversationRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla konversationer"

    def execute(self) -> None:
        conversations = self._repo.list_conversations()
        if not conversations:
            self._ui.display.error("Inga konversationer hittades")
            return

        self._ui.display.header("Alla konversationer")
        self._ui.display.list_items(conversations, _conversation_display)


class DeleteConversationCommand(Command):
    def __init__(self, repo: ConversationRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en konversation"

    def execute(self) -> None:
        conversations = self._repo.list_conversations()
        selected = self._ui.select_from_list(
            conversations,
            _conversation_display,
            "Valj konversation att ta bort",
        )
        if not selected:
            return

        conversation_id = selected["conv_id"]
        if self._ui.confirm(f"Ta bort konversation '{conversation_id}'?"):
            if self._repo.delete_conversation(conversation_id):
                self._ui.display.success(f"Konversation '{conversation_id}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort konversationen")


class DeleteAllConversationsCommand(Command):
    def __init__(self, repo: ConversationRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort alla konversationer"

    def execute(self) -> None:
        if not self._ui.confirm("Ta bort ALLA konversationer?"):
            return

        deleted_count = self._repo.delete_all_conversations()
        if deleted_count == 0:
            self._ui.display.error("Inga konversationer att ta bort")
            return

        self._ui.display.success(f"Tog bort {deleted_count} konversationer")
