from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import AgentRunner
from app.db.session import get_db_session
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService



def get_agent(request: Request) -> AgentRunner:
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise RuntimeError("Agent has not been initialised")
    return agent

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
    agent: AgentRunner = Depends(get_agent),
) -> ChatService:
    return ChatService(agent=agent, session=session)