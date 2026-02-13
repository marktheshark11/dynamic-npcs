__all__ = ["ChatService", "NPCService"]


def __getattr__(name):
    if name == "NPCService":
        from .npc_service import NPCService

        return NPCService
    if name == "ChatService":
        from .chat_service import ChatService

        return ChatService
    raise AttributeError(f"module 'services' has no attribute '{name}'")
