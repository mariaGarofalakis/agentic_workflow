from collections.abc import AsyncIterator
from typing import Any, Protocol
from app.agent.core.events import AgentEvent


class ChatAgentRunner(Protocol):
    async def run_stream(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        ...

    async def run(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> dict[str, Any]:
        ...