from app.core.logging import get_logger
from collections.abc import AsyncIterator
from typing import Any

from app.providers.openai_responses import OpenAIResponsesClient
from app.tools.core.executor import ToolExecutor
from app.tools.core.registry import ToolRegistry
from app.agent.orchestrator import OrchestratorAgent

from app.agent.vacation_planner import VacationPlannerAgent


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
        self.vacation_planner = VacationPlannerAgent(
            llm=llm,
        )

    
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

        logger.info("ORCHESTRATOR PARSED: %s", decision)
        logger.info("ORCHESTRATOR RESPONSE ID: %s", orchestrator_response_id)

        if decision.target == "VacationPlanner":
            if not decision.duration_days and not decision.is_date_range_clear:
                decision.blocking_missing_fields = ["start_date", "end_date"]
            if decision.blocking_missing_fields:
                text = (
                    "I need a few details before I can plan this trip properly. "
                    "Please fill in the travel preference card, then I’ll continue."
                )

                async for event in self._stream_static_text(text):
                    yield event

                yield {
                    "type": "ui_hint",
                    "component": "travel_preferences_card",
                    "missing_fields": decision.blocking_missing_fields,
                    "saveable_fields": self._saveable_preference_fields(),
                }

                yield {
                    "type": "completed",
                    "final_response_id": None,
                }
                return

            async for event in self.vacation_planner.run_stream(
                user_input=user_input,
                planning_state=decision,
                previous_response_id=previous_response_id,
            ):
                yield event

            return

        if decision.target == "GeneralAssistant":
            text = (
                "I’m a vacation planner assistant, so I can help with trip planning, "
                "itineraries, destinations, dates, budgets, travel pace, and activity ideas.\n\n"
                "Try asking something like:\n"
                "- Plan a 5-day trip to Rome\n"
                "- Give me a weekend itinerary for Athens\n"
                "- Help me plan a budget-friendly beach vacation\n"
                "- Suggest a family trip in Spain for 7 days"
            )

            async for event in self._stream_static_text(text):
                yield event

            yield {
                "type": "completed",
                "final_response_id": None,
            }
            return
        return

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

    async def _stream_static_text(
        self,
        text: str,
        chunk_size: int = 24,
    ) -> AsyncIterator[dict[str, Any]]:
        for index in range(0, len(text), chunk_size):
            yield {
                "type": "chunk",
                "content": text[index : index + chunk_size],
            }




    def _saveable_preference_fields(self) -> list[str]:
        return [
            "home_city",
            "home_airport",
            "default_travelers",
            "budget_style",
            "pace",
            "interests",
            "dietary_needs",
            "accessibility_needs",
        ]

