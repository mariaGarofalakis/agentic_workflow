from collections.abc import AsyncIterator

from app.agent.runner import AgentRunner


class ChatService:
    def __init__(self, agent: AgentRunner) -> None:
        self.agent = agent
        self.final_response_id: str | None = None

    async def reply_stream(self, message: str) -> AsyncIterator[str]:
        async for chunk in self.agent.run_stream(
            message,
            previous_response_id=self.final_response_id,
        ):
            yield chunk

        self.final_response_id = self.agent.final_response_id
