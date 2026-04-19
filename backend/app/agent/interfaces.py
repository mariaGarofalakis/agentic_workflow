from collections.abc import AsyncIterator
from typing import Any, Protocol


class ChatAgentRunner(Protocol):
    async def run_stream(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ...