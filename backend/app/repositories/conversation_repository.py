from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.models import Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: str,
        title: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            last_response_id=None,
            is_processing=False,
        )
        self.session.add(conversation)
        return conversation


    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, conversation_id: str) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def claim_for_processing(self, conversation_id: str) -> Conversation:
        conversation = await self.get_by_id_for_update(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        if conversation.is_processing:
            raise RuntimeError("Conversation is already processing another message")

        conversation.is_processing = True
        conversation.updated_at = datetime.now(UTC)
        self.session.add(conversation)
        return conversation

    async def release_processing(
        self,
        conversation_id: str,
        *,
        new_last_response_id: str | None = None,
    ) -> Conversation:
        conversation = await self.get_by_id_for_update(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        if new_last_response_id is not None:
            conversation.last_response_id = new_last_response_id

        conversation.is_processing = False
        conversation.updated_at = datetime.now(UTC)
        self.session.add(conversation)
        return conversation