from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.runner import AgentRunner
from app.api.chat_router import chat_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.dependencies import set_chat_service
from app.providers.openai_responses import OpenAIResponsesClient
from app.services.chat_service import ChatService
from app.tools.core.loader import build_registry

# Initialize logging
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build tool registry
    registry = build_registry()

    # Initialize LLM client
    llm = OpenAIResponsesClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        max_output_tokens=settings.max_output_tokens,
        request_timeout_seconds=settings.request_timeout_seconds,
    )

    # Initialize agent
    agent = AgentRunner(
        llm=llm,
        registry=registry,
        max_tool_iterations=settings.max_tool_iterations,
    )

    # Initialize service layer
    chat_service = ChatService(agent)
    set_chat_service(chat_service)

    yield  # App runs here


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(chat_router, prefix="/api")


# Health check
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
