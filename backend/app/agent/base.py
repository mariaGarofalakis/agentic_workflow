import logging
from abc import ABC
from collections.abc import AsyncIterator
from typing import Any, TypeVar
from pydantic import BaseModel, Field, ValidationError

from app.providers.openai_responses import OpenAIResponsesClient


class ToolParameter(BaseModel):
    type: str
    description: str = ""


class ToolParameters(BaseModel):
    type: str = "object"
    properties: dict[str, ToolParameter] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    additional_properties: bool = False


class ToolSchema(BaseModel):
    type: str = "function"
    name: str
    description: str = ""
    parameters: ToolParameters = Field(default_factory=ToolParameters)


T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    pass


class BaseAgent(ABC):
    def __init__(self, llm: OpenAIResponsesClient) -> None:
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__qualname__)

    @staticmethod
    def build_message(
        system_prompt: str,
        user_content: str,
    ) -> list[dict[str, Any]]:
        return [
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    @staticmethod
    def _extract_text(response: Any) -> str:
        parts: list[str] = []
        for item in getattr(response, "output", []):
            if getattr(item, "type", None) != "message":
                continue
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    parts.append(getattr(content, "text", ""))
        return "".join(parts)

    async def _get_text_response(
        self,
        messages: list[dict[str, Any]],
    ) -> str:
        response = await self.llm.get_final_response(
            input_data=messages,
            tools=[],
        )
        return self._extract_text(response)

    async def _stream_text(
        self,
        messages: list[dict[str, Any]],
    ) -> AsyncIterator[str]:
        async for chunk, _ in self.llm.stream_response(
            input_data=messages,
            tools=[],
        ):
            if chunk:
                yield chunk

    async def _get_structured_response(
        self,
        messages: list[dict[str, Any]],
        schema: type[T],
        max_retries: int = 3,
    ) -> T:
        """
        Request a schema-constrained response and retry explicitly if parsing/validation fails.

        Total attempts = 1 + max_retries.
        """
        text_format = {
            "type": "json_schema",
            "name": schema.__name__,
            "schema": schema.model_json_schema(),
            "strict": True,
        }

        working_messages = list(messages)

        for attempt in range(max_retries + 1):
            response = await self.llm.get_final_response(
                input_data=working_messages,
                tools=[],
                text_format=text_format,
            )

            raw_text = self._extract_text(response).strip()

            try:
                return schema.model_validate_json(raw_text)

            except ValidationError as exc:
                self.logger.warning(
                    "Structured output validation failed on attempt %s/%s: %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )

                if attempt == max_retries:
                    raise StructuredOutputError(
                        f"Failed to obtain valid structured output after "
                        f"{max_retries + 1} attempts.\n\n"
                        f"Last raw output:\n{raw_text}\n\n"
                        f"Validation error:\n{exc}"
                    ) from exc

                # Feed the model its invalid output plus the validation error.
                working_messages = [
                    *working_messages,
                    {
                        "role": "assistant",
                        "content": raw_text,
                    },
                    {
                        "role": "developer",
                        "content": (
                            "Your previous response did not match the required JSON schema.\n"
                            "Return ONLY valid JSON that matches the schema exactly.\n"
                            "Do not include markdown fences, prose, or extra keys.\n"
                            f"Validation error:\n{exc}"
                        ),
                    },
                ]