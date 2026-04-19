import logging
from typing import Any

from app.agent.core.base import BaseAgent
from app.agent.schemas import Plan
from app.tools.core.registry import ToolRegistry
from app.providers.openai_responses import OpenAIResponsesClient

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """
You are a planning agent for a trip-planning assistant.

Your task is to create a minimal execution plan for answering the user's request using the available tools.

Return exactly one JSON object matching the required schema.
Do not include markdown.
Do not include code fences.
Do not include any text before or after the JSON.

Planning rules:
- Each step must call exactly one tool.
- Use the exact tool name.
- tool_args must be a JSON object matching the tool arguments.
- Only include steps that are actually needed.
- Keep the plan as short as possible.
- step_id must be a unique integer starting at 1.
- depends_on must contain prior step_ids required before the current step can run.
- If one step depends on information from another step, include that dependency.
- If the user can be answered without tools, return an empty "steps" list.
- Do not invent tool names or tool arguments.
- Do not add steps for tools that are irrelevant to the request.

Available tools:
{tool_description}

Output requirements:
- reasoning: short internal summary of why these tool steps are needed
- steps: ordered list of tool steps
"""


class Planner(BaseAgent):
    def __init__(
        self,
        llm: OpenAIResponsesClient,
        registry: ToolRegistry,
    ) -> None:
        super().__init__(llm)
        self.registry = registry

    def _build_system_prompt(self, tool_names: list[str] | None = None) -> str:
        if tool_names is None:
            tool_description = self.registry.describe()
        else:
            tool_description = self.registry.describe(tool_names)

        return PLANNER_SYSTEM_PROMPT.format(
            tool_description=tool_description,
        )

    async def create_plan(
        self,
        user_input: str,
        tool_names: list[str] | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> Plan:
        system_prompt = self._build_system_prompt(tool_names)

        if extra_context:
            context_lines = ["Context:"]
            for key, value in extra_context.items():
                context_lines.append(f"- {key}: {value}")
            context_text = "\n".join(context_lines)
            prompt_input = f"{context_text}\n\nUser request:\n{user_input}"
        else:
            prompt_input = user_input

        messages = self.build_message(system_prompt, prompt_input)

        plan = await self._get_structured_response(
            messages=messages,
            schema=Plan,
        )

        return self._normalize_plan(plan, allowed_tool_names=tool_names)

    def _normalize_plan(
        self,
        plan: Plan,
        allowed_tool_names: list[str] | None = None,
    ) -> Plan:
        allowed = (
            set(allowed_tool_names)
            if allowed_tool_names is not None
            else {tool["name"] for tool in self.registry.schemas}
        )

        normalized_steps = []
        seen_step_ids: set[int] = set()

        for index, step in enumerate(plan.steps, start=1):
            if step.tool_name not in allowed:
                raise ValueError(f"Planner returned unknown/disallowed tool: {step.tool_name}")

            if step.step_id in seen_step_ids:
                raise ValueError(f"Duplicate step_id returned by planner: {step.step_id}")

            seen_step_ids.add(step.step_id)

            # Normalize dependency ordering and remove self-dependency
            depends_on = sorted(
                dep for dep in step.depends_on
                if dep != step.step_id
            )

            normalized_steps.append(
                step.model_copy(
                    update={
                        "depends_on": depends_on,
                    }
                )
            )

        # Optional strict safety checks
        self._validate_step_sequence(normalized_steps)

        return plan.model_copy(update={"steps": normalized_steps})

    @staticmethod
    def _validate_step_sequence(steps) -> None:
        step_ids = {step.step_id for step in steps}

        for expected_id, step in enumerate(steps, start=1):
            if step.step_id != expected_id:
                raise ValueError(
                    f"Plan step_ids must be sequential starting at 1. "
                    f"Expected {expected_id}, got {step.step_id}."
                )

            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(
                        f"Plan step {step.step_id} depends on unknown step_id {dep}."
                    )
                if dep >= step.step_id:
                    raise ValueError(
                        f"Plan step {step.step_id} has invalid dependency {dep}. "
                        "Dependencies must reference earlier steps only."
                    )