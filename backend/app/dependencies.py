from app.services.chat_service import ChatService

_chat_service: ChatService | None = None


def set_chat_service(service: ChatService) -> None:
    global _chat_service
    _chat_service = service


def get_chat_service() -> ChatService:
    if _chat_service is None:
        raise RuntimeError("Chat service not initialized")
    return _chat_service
