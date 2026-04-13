from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)

    async def create_user(self, *, email: str | None = None) -> str:
        async with self.session.begin():
            if email:
                existing = await self.user_repository.get_by_email(email)
                if existing is not None:
                    raise ValueError(f"User with email {email} already exists")

            user = await self.user_repository.create(email=email)

        return user.id

    async def ensure_dev_user(self) -> str:
        async with self.session.begin():
            existing = await self.user_repository.get_by_id(settings.dev_user_id)
            if existing is not None:
                return existing.id

            if settings.dev_user_email:
                existing_email = await self.user_repository.get_by_email(settings.dev_user_email)
                if existing_email is not None:
                    return existing_email.id

            user = await self.user_repository.create(
                user_id=settings.dev_user_id,
                email=settings.dev_user_email,
            )

        return user.id