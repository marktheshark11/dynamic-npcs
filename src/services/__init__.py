__all__ = ["ChatService", "DoorService", "HintService", "ScriptedNpcService"]


def __getattr__(name):
    if name == "ChatService":
        from .chat_service import ChatService

        return ChatService
    if name == "HintService":
        from .hint_service import HintService

        return HintService
    if name == "DoorService":
        from .door_service import DoorService

        return DoorService
    if name == "ScriptedNpcService":
        from .scripted_npc_service import ScriptedNpcService

        return ScriptedNpcService
    raise AttributeError(f"module 'services' has no attribute '{name}'")
