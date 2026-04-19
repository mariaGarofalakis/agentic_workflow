from typing import TypeVar

from pydantic import BaseModel

from app.agent.core.base import BaseAgent

T = TypeVar("T", bound=BaseModel)


class WorkerAgent(BaseAgent):
    system_prompt: str = "You are a helpful specialist agent."

    async def run_text(self, user_input: str) -> str:
        messages = self.build_message(self.system_prompt, user_input)
        return await self._get_text_response(messages)

    async def run_structured(self, user_input: str, schema: type[T]) -> T:
        messages = self.build_message(self.system_prompt, user_input)
        return await self._get_structured_response(messages, schema)

    async def stream_text(self, user_input: str):
        messages = self.build_message(self.system_prompt, user_input)
        async for chunk in self._stream_text(messages):
            yield chunk