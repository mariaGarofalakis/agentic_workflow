import logging
from collections.abc import AsyncIterator
from typing import Any

from app.providers.openai_responses import OpenAIResponsesClient
from app.tools.core.executor import ToolExecutor
from app.tools.core.registry import ToolRegistry
from app.planning.state import TripPlanState
from app.agent.orchestrator import OrchestratorAgent, OrchestratorAction
from app.agent.destination_agent import DestinationAgent, DestinationResult

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
    ):
        # initialize agents
        orchestrator = OrchestratorAgent(self.llm)
        destination_agent = DestinationAgent(self.llm)

        state = TripPlanState()
        state.messages.append(user_input)

        final_text = ""

        for _ in range(5):
            action: OrchestratorAction = await orchestrator.decide(
                state.model_dump_json()
            )

            if action.action == "extract_request":
                state.request.destination = user_input

            elif action.action == "research_destinations":
                result = await destination_agent.run_structured(
                    user_input,
                    schema=DestinationResult,
                )
                state.destinations = result.options

            elif action.action == "finalize":
                final_text = self._build_final_response(state)
                break

        # stream result
        for char in final_text:
            yield {"type": "chunk", "content": char}

        yield {
            "type": "completed",
            "final_response_id": "multiagent-static-id",
        }



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
    
    def _build_final_response(self, state: TripPlanState) -> str:
        if not state.destinations:
            return "I could not find suitable destinations."

        text = "Here are some travel ideas:\\n\\n"
        for d in state.destinations:
            text += f"- {d.name} ({d.country}): {d.reason}\\n"

        return text