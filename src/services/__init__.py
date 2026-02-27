__all__ = ["ChatService"]


def __getattr__(name):
    if name == "ChatService":
        from .chat_service import ChatService

        return ChatService
    raise AttributeError(f"module 'services' has no attribute '{name}'")
