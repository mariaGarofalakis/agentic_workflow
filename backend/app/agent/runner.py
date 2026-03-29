import json
from collections.abc import AsyncIterator
from typing import Any

from app.providers.openai_responses import OpenAIResponsesClient, safe_json_dumps
from backend.app.tools.core.registry import ToolRegistry


class AgentRunner:
    def __init__(
        self,
        llm: OpenAIResponsesClient,
        registry: ToolRegistry,
        max_tool_iterations: int = 8,
        stream_text: bool = False,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.max_tool_iterations = max_tool_iterations
        self.stream_text = stream_text

    async def run(self, user_input: str) -> str:
        response = await self.llm.create_response(
            input_data=user_input,
            tools=self.registry.schemas,
        )

        for _ in range(self.max_tool_iterations):
            tool_outputs = await self._collect_tool_outputs(response)
            if not tool_outputs:
                return getattr(response, "output_text", "")

            response = await self.llm.create_response(
                input_data=tool_outputs,
                tools=self.registry.schemas,
                previous_response_id=response.id,
            )

        raise RuntimeError("Agent exceeded max tool iterations")

    async def run_stream(self, user_input: str) -> AsyncIterator[str]:
        response = None

        async for event in self._stream_turn_and_get_response(
            input_data=user_input,
            previous_response_id=None,
        ):
            if event["type"] == "chunk":
                yield event["content"]
            elif event["type"] == "final_response":
                response = event["response"]

        if response is None:
            raise RuntimeError("No response returned from initial streamed turn")

        for _ in range(self.max_tool_iterations):
            tool_outputs = await self._collect_tool_outputs(response)
            if not tool_outputs:
                return

            previous_response_id = response.id
            response = None

            async for event in self._stream_turn_and_get_response(
                input_data=tool_outputs,
                previous_response_id=previous_response_id,
            ):
                if event["type"] == "chunk":
                    yield event["content"]
                elif event["type"] == "final_response":
                    response = event["response"]

            if response is None:
                raise RuntimeError("No response returned from streamed tool turn")
            
    async def _stream_turn_and_get_response(
        self,
        input_data: str | list[dict[str, Any]],
        previous_response_id: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        final_response = None

        async for chunk, response in self.llm.stream_response(
            input_data=input_data,
            tools=self.registry.schemas,
            previous_response_id=previous_response_id,
        ):
            if chunk:
                yield {"type": "chunk", "content": chunk}
            if response is not None:
                final_response = response

        if final_response is None:
            raise RuntimeError("Stream completed without final response")

        yield {"type": "final_response", "response": final_response}

    async def _collect_tool_outputs(self, response: Any) -> list[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []

        for item in getattr(response, "output", []):
            item_type = getattr(item, "type", None)
            if item_type not in {"function_call", "tool_call"}:
                continue

            tool_name = getattr(item, "name", "")
            call_id = getattr(item, "call_id", None)
            raw_args = getattr(item, "arguments", {})
            args = self._parse_args(raw_args)

            try:
                result = await self.registry.run(tool_name, args)
            except Exception as exc:
                result = {
                    "ok": False,
                    "error": {
                        "type": "tool_execution_error",
                        "tool_name": tool_name,
                        "message": str(exc),
                    },
                }

            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": safe_json_dumps(result),
                }
            )

        return outputs

    @staticmethod
    def _parse_args(raw_args: Any) -> dict[str, Any]:
        if isinstance(raw_args, dict):
            return raw_args
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}