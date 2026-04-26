import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.agent.core.errors import build_structured_output_error
from app.agent.core.messages import MessageBuilder
from app.agent.core.response_text import ResponseTextExtractor
from app.agent.core.tool_loop import ToolLoopRunner
from app.providers.openai_responses import OpenAIResponsesClient
from app.tools.core.registry import ToolRegistry, ToolSet


T = TypeVar("T", bound=BaseModel)


class StructuredOutputRunner:
    def __init__(
        self,
        llm: OpenAIResponsesClient,
        logger: logging.Logger,
    ) -> None:
        self.llm = llm
        self.logger = logger
        self.messages = MessageBuilder()
        self.text = ResponseTextExtractor()

    def parse_structured_response(
        self,
        *,
        response: Any,
        schema: type[T],
    ) -> tuple[T, str | None]:
        raw_text = self.text.extract_text(response).strip()
        parsed = schema.model_validate_json(raw_text)
        return parsed, getattr(response, "id", None)

    async def get(
        self,
        messages: list[dict[str, Any]],
        schema: type[T],
        previous_response_id: str | None = None,
        max_retries: int = 3,
    ) -> tuple[T, str | None]:
        """
        Request a schema-constrained response and retry if parsing/validation fails.

        Use this for structured agents that do not need tools.
        """
        text_format = self.messages.build_text_format(schema)
        working_messages = list(messages)

        for attempt in range(max_retries + 1):
            response = await self.llm.get_final_response(
                input_data=working_messages,
                tools=[],
                previous_response_id=previous_response_id if attempt == 0 else None,
                text_format=text_format,
            )

            raw_text = self.text.extract_text(response).strip()

            try:
                return self.parse_structured_response(
                    response=response,
                    schema=schema,
                )

            except ValidationError as exc:
                self.logger.warning(
                    "Structured output validation failed on attempt %s/%s: %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )

                if attempt == max_retries:
                    raise build_structured_output_error(
                        max_attempts=max_retries + 1,
                        raw_text=raw_text,
                        exc=exc,
                    ) from exc

                working_messages = [
                    *working_messages,
                    {"role": "assistant", "content": raw_text},
                    self.messages.build_repair_message(exc),
                ]

        raise RuntimeError("Unreachable structured response failure")

    async def get_with_tools(
        self,
        messages: list[dict[str, Any]],
        schema: type[T],
        tools: ToolRegistry | ToolSet,
        previous_response_id: str | None = None,
        max_tool_iterations: int = 4,
        max_retries: int = 2,
    ) -> tuple[T, str | None]:
        """
        Allow the model to call tools, then require the final response to match
        the given Pydantic schema.

        Use this for structured agents that need deterministic helpers, e.g.
        an orchestrator calling normalize_travel_dates.

        This depends on your provider/local server supporting tools and
        structured output in the same call.
        """
        text_format = self.messages.build_text_format(schema)
        original_messages = list(messages)
        working_messages = list(messages)
        tool_loop = ToolLoopRunner(tools)

        for parse_attempt in range(max_retries + 1):
            current_previous_response_id = (
                previous_response_id if parse_attempt == 0 else None
            )

            response = await self.llm.get_final_response(
                input_data=working_messages,
                tools=tools.schemas,
                previous_response_id=current_previous_response_id,
                text_format=text_format,
            )

            for _ in range(max_tool_iterations):
                tool_outputs = await tool_loop.collect_tool_outputs(response)

                if not tool_outputs:
                    break

                response = await self.llm.get_final_response(
                    input_data=tool_outputs,
                    tools=tools.schemas,
                    previous_response_id=getattr(response, "id", None),
                    text_format=text_format,
                )

            raw_text = self.text.extract_text(response).strip()

            try:
                return self.parse_structured_response(
                    response=response,
                    schema=schema,
                )

            except ValidationError as exc:
                self.logger.warning(
                    "Structured output with tools validation failed on attempt %s/%s: %s",
                    parse_attempt + 1,
                    max_retries + 1,
                    exc,
                )

                if parse_attempt == max_retries:
                    raise build_structured_output_error(
                        max_attempts=max_retries + 1,
                        raw_text=raw_text,
                        exc=exc,
                    ) from exc

                working_messages = [
                    *original_messages,
                    {"role": "assistant", "content": raw_text},
                    self.messages.build_repair_message(exc),
                ]

        raise RuntimeError("Unreachable structured response with tools failure")