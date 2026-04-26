from app.core.logging import get_logger
from collections.abc import AsyncIterator
from typing import Any

from app.providers.openai_responses import OpenAIResponsesClient
from app.tools.core.executor import ToolExecutor
from app.tools.core.registry import ToolRegistry
from app.agent.orchestrator import OrchestratorAgent, OrchestratorDecision


logger = get_logger(__name__)


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
        self.orchestrator = OrchestratorAgent(llm, registry=registry)

    
    
    async def run_stream(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        result = await self.orchestrator.run(
            user_input=user_input,
            previous_response_id=None,
        )

        decision = result["decision"]
        orchestrator_response_id = result["final_response_id"]

        print("ORCHESTRATOR PARSED:", decision)
        print("ORCHESTRATOR RESPONSE ID:", orchestrator_response_id)

        yield {
            "type": "chunk",
            "content": (
                f"Target: {decision.target}\n"
                f"Destination: {decision.destination}\n"
                f"Duration: {decision.duration_days}\n"
                f"Start date: {decision.start_date}\n"
                f"End date: {decision.end_date}\n"
                f"Date clear: {decision.is_date_range_clear}\n"
                f"Missing: {', '.join(decision.missing_fields) or 'None'}\n"
                f"Blocking: {', '.join(decision.blocking_missing_fields) or 'None'}\n"
            ),
        }

        yield {
            "type": "completed",
            "final_response_id": None,
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
     