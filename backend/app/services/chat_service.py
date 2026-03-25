from collections.abc import AsyncIterator

from app.agent.runner import AgentRunner


class ChatService:
    def __init__(self, agent: AgentRunner) -> None:
        self.agent = agent

    async def reply_stream(self, message: str) -> AsyncIterator[str]:
        async for chunk in self.agent.run_stream(message):
            yield chunk