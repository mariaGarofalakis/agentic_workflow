import json
from datetime import datetime, date
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI


class OpenAIResponsesClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_output_tokens: int = 1024,
        request_timeout_seconds: float = 60.0,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=request_timeout_seconds,
        )

    async def stream_response(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_response_id: str | None = None,
    ) -> AsyncIterator[tuple[str, Any | None]]:
        async with self._client.responses.stream(
            model=self.model,
            input=input_data,
            tools=tools,
            tool_choice="auto",
            previous_response_id=previous_response_id,
            max_output_tokens=self.max_output_tokens,
        ) as stream:
            async for event in stream:
                delta = getattr(event, "delta", None)
                if isinstance(delta, str) and delta:
                    yield delta, None

            final_response = await stream.get_final_response()
            yield "", final_response

    async def get_final_response(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_response_id: str | None = None,
    ) -> Any:
        async with self._client.responses.stream(
            model=self.model,
            input=input_data,
            tools=tools,
            tool_choice="auto",
            previous_response_id=previous_response_id,
            max_output_tokens=self.max_output_tokens,
        ) as stream:
            async for _ in stream:
                pass
            return await stream.get_final_response()


def safe_json_dumps(value: Any) -> str:
    def serializer(obj: Any) -> str:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return str(obj)

    return json.dumps(
        value,
        default=serializer,
        ensure_ascii=False,
    )
