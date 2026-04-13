from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import AgentRunner
from app.db.session import get_db_session
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService

_agent: AgentRunner | None = None


def set_agent(agent: AgentRunner) -> None:
    global _agent
    _agent = agent


def get_agent() -> AgentRunner:
    if _agent is None:
        raise RuntimeError("Agent has not been initialized")
    return _agent

async def get_conversation_service(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationService:
    return ConversationService(session=session)

async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UserService:
    return UserService(session=session)


async def get_chat_service(
    session: AsyncSession = Depends(get_db_session),
) -> ChatService:
    agent = get_agent()
    return ChatService(agent=agent, session=session)