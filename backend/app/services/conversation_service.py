from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.user_repository import UserRepository


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.user_repository = UserRepository(session)

    async def create_conversation(
        self,
        *,
        title: str | None = None,
        user_id: str | None = None,
    ) -> str:
        async with self.session.begin():
            resolved_user_id = user_id

            if not settings.auth_enabled:
                resolved_user_id = settings.dev_user_id

            if resolved_user_id is None:
                raise ValueError("user_id is required when auth is enabled")

            user = await self.user_repository.get_by_id(resolved_user_id)
            if user is None:
                raise ValueError(f"User {resolved_user_id} not found")

            conversation = await self.conversation_repository.create(
                user_id=resolved_user_id,
                title=title,
            )

        return conversation.id