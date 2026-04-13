from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import AsyncSessionLocal
from app.services.user_service import UserService

from app.agent.runner import AgentRunner
from app.api.chat_router import chat_router
from app.api.conversation_router import conversation_router
from app.api.user_router import user_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.dependencies import set_agent
from app.providers.openai_responses import OpenAIResponsesClient
from app.tools.core.loader import build_registry

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    

    registry = build_registry()

    llm = OpenAIResponsesClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        max_output_tokens=settings.max_output_tokens,
        request_timeout_seconds=settings.request_timeout_seconds,
    )

    agent = AgentRunner(
        llm=llm,
        registry=registry,
        max_tool_iterations=settings.max_tool_iterations,
    )

    set_agent(agent)

    # create local user for test localy
    if not settings.auth_enabled:
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            await user_service.ensure_dev_user()

    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(conversation_router, prefix="/api")
app.include_router(user_router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}