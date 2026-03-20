__all__ = ["ChatService", "ScriptedNpcService"]


def __getattr__(name):
    if name == "ChatService":
        from .chat_service import ChatService

        return ChatService
    if name == "ScriptedNpcService":
        from .scripted_npc_service import ScriptedNpcService

        return ScriptedNpcService
    raise AttributeError(f"module 'services' has no attribute '{name}'")
