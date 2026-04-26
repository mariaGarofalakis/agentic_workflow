import logging
from abc import ABC
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from pydantic import BaseModel

from app.agent.core.messages import MessageBuilder
from app.agent.core.response_text import ResponseTextExtractor
from app.agent.core.structured_output import StructuredOutputRunner
from app.providers.openai_responses import OpenAIResponsesClient
from app.tools.core.registry import ToolRegistry, ToolSet


T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """
    Small base class for concrete agents.

    It owns shared dependencies and exposes focused helper components.

    It intentionally does NOT implement run() or run_stream().
    """

    def __init__(self, llm: OpenAIResponsesClient) -> None:
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__qualname__)

        self.messages = MessageBuilder()
        self.text = ResponseTextExtractor()
        self.structured = StructuredOutputRunner(
            llm=self.llm,
            logger=self.logger,
        )

    # ---------------------------------------------------------------------
    # Convenience wrappers
    # ---------------------------------------------------------------------

    @staticmethod
    def current_date_utc() -> str:
        return MessageBuilder.current_date_utc()

    @staticmethod
    def schema_to_prompt(schema: type[BaseModel]) -> str:
        return MessageBuilder.schema_to_prompt(schema)

    @staticmethod
    def build_messages(
        system_prompt: str,
        user_content: str,
    ) -> list[dict[str, Any]]:
        return MessageBuilder.build_messages(
            system_prompt=system_prompt,
            user_content=user_content,
        )

    @staticmethod
    def extract_text(response: Any) -> str:
        return ResponseTextExtractor.extract_text(response)

    async def get_text_response(
        self,
        messages: list[dict[str, Any]],
        previous_response_id: str | None = None,
    ) -> str:
        response = await self.llm.get_final_response(
            input_data=messages,
            tools=[],
            previous_response_id=previous_response_id,
        )

        return self.text.extract_text(response)

    async def stream_text(
        self,
        messages: list[dict[str, Any]],
        previous_response_id: str | None = None,
    ) -> AsyncIterator[str]:
        async for chunk, _ in self.llm.stream_response(
            input_data=messages,
            tools=[],
            previous_response_id=previous_response_id,
        ):
            if chunk:
                yield chunk

    async def get_structured_response(
        self,
        messages: list[dict[str, Any]],
        schema: type[T],
        previous_response_id: str | None = None,
        max_retries: int = 3,
    ) -> tuple[T, str | None]:
        return await self.structured.get(
            messages=messages,
            schema=schema,
            previous_response_id=previous_response_id,
            max_retries=max_retries,
        )

    async def get_structured_response_with_tools(
        self,
        messages: list[dict[str, Any]],
        schema: type[T],
        tools: ToolRegistry | ToolSet,
        previous_response_id: str | None = None,
        max_tool_iterations: int = 4,
        max_retries: int = 2,
    ) -> tuple[T, str | None]:
        return await self.structured.get_with_tools(
            messages=messages,
            schema=schema,
            tools=tools,
            previous_response_id=previous_response_id,
            max_tool_iterations=max_tool_iterations,
            max_retries=max_retries,
        )