from collections.abc import AsyncIterator
from typing import Any

from app.agent.core.base import BaseAgent
from app.agent.orchestrator import OrchestratorDecision
from app.providers.openai_responses import OpenAIResponsesClient


class VacationPlannerAgent(BaseAgent):
    def __init__(
        self,
        llm: OpenAIResponsesClient,
    ) -> None:
        super().__init__(llm)

    async def run_stream(
        self,
        *,
        user_input: str,
        planning_state: OrchestratorDecision,
        previous_response_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        messages = self.build_messages(
            system_prompt=self._build_system_prompt(),
            user_content=self._build_user_content(
                user_input=user_input,
                planning_state=planning_state,
            ),
        )

        final_response_id: str | None = None

        async for event_type, chunk, response in self.llm.stream_response(
            input_data=messages,
            tools=[],
            previous_response_id=previous_response_id,
        ):
            if event_type == "chunk" and chunk:
                yield {
                    "type": "chunk",
                    "content": chunk,
                }

            elif event_type == "reasoning" and chunk:
                yield {
                    "type": "reasoning",
                    "content": chunk,
                }

            elif event_type == "final_response" and response is not None:
                final_response_id = getattr(response, "id", None)

        yield {
            "type": "completed",
            "final_response_id": final_response_id,
        }

    def _build_system_prompt(self) -> str:
        return """
You are a vacation-planning specialist.

Your job:
- Create practical, enjoyable travel plans.
- Use the provided planning state as the source of truth.
- Do not ask for missing optional information unless it is truly blocking.
- If dates are provided, organize the plan by day.
- If exact dates are missing but duration is known, organize by Day 1, Day 2, etc.
- Prefer realistic pacing over cramming too many activities.
- Include food, neighborhoods, transport tips, and timing suggestions when useful.
- Be honest about uncertainty.
- Do not claim to know live availability, opening hours, ticket prices, or weather unless tools/data are provided.

Output style:
- Start with a short summary.
- Then provide a day-by-day itinerary.
- Keep the answer useful and readable.
""".strip()

    def _build_user_content(
        self,
        *,
        user_input: str,
        planning_state: OrchestratorDecision,
    ) -> str:
        return (
            "Create a vacation plan for the user.\n\n"
            f"Original user request:\n{user_input}\n\n"
            "Planning state extracted by the orchestrator:\n"
            f"{planning_state.model_dump_json(indent=2)}"
        )