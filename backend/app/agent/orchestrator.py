import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.core.base import BaseAgent
from app.providers.openai_responses import OpenAIResponsesClient


class OrchestratorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: Literal["VacationPlanner", "Clarifier", "GeneralAssistant"] = Field(
        description="The worker agent that should handle the request."
    )

    destination: str | None = None
    duration_days: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_date_range_clear: bool = False

    travelers: int | None = None
    budget: str | None = None

    interests: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    blocking_missing_fields: list[str] = Field(default_factory=list)

    @field_validator("interests", "missing_fields", "blocking_missing_fields", mode="before")
    @classmethod
    def none_to_empty_list(cls, value: Any) -> Any:
        if value is None:
            return []
        return value


class OrchestratorAgent(BaseAgent):
    async def run(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> dict[str, Any]:
        decision, response_id = await self.decide(
            user_input=user_input,
            previous_response_id=previous_response_id,
        )

        return {
            "decision": decision,
            "final_response_id": response_id,
        }

    async def decide(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> tuple[OrchestratorDecision, str | None]:
        current_date = datetime.now(UTC).date().isoformat()

        schema_json = json.dumps(
            OrchestratorDecision.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )

        system_prompt = f"""
You are the orchestrator for a vacation-planning multi-agent system.

Your job:
- Route the user request to exactly one target worker.
- Extract structured travel-planning state.
- Do not create an itinerary.
- Do not recommend places.
- Do not answer the user's request.

Current date: {current_date}

Routing rules:
- If the user asks about vacations, trips, itineraries, hotels, flights, destinations, travel budgets, or travel weather, use target="VacationPlanner".
- If the user request is too unclear to act on, use target="Clarifier".
- Otherwise, use target="GeneralAssistant".

Date rules:
- Always output start_date and end_date as top-level fields.
- Use ISO date format: YYYY-MM-DD.
- Resolve relative dates using the current date.
- If the user explicitly gives duration_days, do not change it.
- If the user asks for a 3 day plan, duration_days must be 3.
- If the user gives a duration and a clear start date, infer end_date.
- end_date should equal start_date + duration_days - 1 days.
- If the date is vague and cannot be normalized, use start_date=null, end_date=null, is_date_range_clear=false.

Clarification rules:
- destination is blocking for vacation planning.
- duration is blocking only when both duration_days and clear dates are missing.
- dates are blocking only for date-specific planning, weather, events, availability, or when the user explicitly asks for dates.
- budget, travelers, and interests are useful, but usually not blocking.

Output rules:
- Return JSON only.
- Return exactly one flat JSON object.
- Do not use markdown.
- Do not use nested objects.
- Do not use planning_state.
- Do not use routing_target.
- Use [] for empty list fields.
- Never use null for interests, missing_fields, or blocking_missing_fields.
- Do not include fields that are not in the schema.

JSON Schema:
{schema_json}
""".strip()

        messages = self.build_messages(
            system_prompt=system_prompt,
            user_content=(
                "Extract planning state and route this message. "
                "Return only the JSON object.\n\n"
                f"User message: {user_input}"
            ),
        )

        return await self._get_structured_response(
            messages=messages,
            schema=OrchestratorDecision,
            previous_response_id=None,
            max_retries=2,
        )