import logging
from collections.abc import AsyncIterator
from typing import Any

from app.providers.openai_responses import OpenAIResponsesClient
from app.tools.core.executor import ToolExecutor
from app.tools.core.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MultiAgentWorkflowRunner:
    """
    Phase 1 skeleton.


    In later phases this runner will:
    - create an orchestrator
    - dispatch to worker agents
    - use agent-specific ToolSets
    - maintain structured planning state
    """

    def __init__(
        self,
        llm: OpenAIResponsesClient,
        registry: ToolRegistry,
        max_tool_iterations: int = 4,
        stream_text: bool = False,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.max_tool_iterations = max_tool_iterations
        self.stream_text = stream_text
        self.executor = ToolExecutor(registry)

    async def run_stream(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Phase 1 compatibility behavior:
        - preserve current streaming contract
        - preserve previous_response_id continuity
        - preserve tool execution loop

        In Phase 2+, this method will orchestrate a multi-agent workflow.
        """
        response = None

        async for event in self._stream_turn_and_get_response(
            input_data=self._build_orchestrator_input(user_input),
            previous_response_id=previous_response_id,
        ):
            if event["type"] == "chunk":
                yield event
            elif event["type"] == "final_response":
                response = event["response"]

        if response is None:
            raise RuntimeError("No response returned from initial workflow turn")

        for _ in range(self.max_tool_iterations):
            tool_outputs = await self._collect_tool_outputs(response)
            if not tool_outputs:
                yield {
                    "type": "completed",
                    "final_response_id": response.id,
                }
                return

            current_response_id = response.id
            response = None

            async for event in self._stream_turn_and_get_response(
                input_data=tool_outputs,
                previous_response_id=current_response_id,
            ):
                if event["type"] == "chunk":
                    yield event
                elif event["type"] == "final_response":
                    response = event["response"]

            if response is None:
                raise RuntimeError("No response returned from workflow tool turn")

        yield {
            "type": "completed",
            "final_response_id": response.id if response is not None else None,
        }

    def _build_orchestrator_input(self, user_input: str) -> str:
        """
        Phase 1:
        Keep prompt shaping minimal.

        Later this will package:
        - user request
        - planning state
        - agent decisions
        - worker outputs
        """
        return user_input

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

            parsed_args = self.executor.parse_arguments(raw_args)
            executed = await self.executor.execute(tool_name, parsed_args)

            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": self.executor.serialize_result(executed.result),
                }
            )

        return outputs