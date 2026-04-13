import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        openai_response_id: str | None = None,
    ) -> Message:
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            openai_response_id=openai_response_id,
        )
        self.session.add(message)
        return message