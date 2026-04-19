from app.agent.core.worker import WorkerAgent
from pydantic import BaseModel
from typing import Literal


class OrchestratorAction(BaseModel):
    action: Literal[
        "extract_request",
        "research_destinations",
        "finalize"
    ]
    reason: str


class OrchestratorAgent(WorkerAgent):
    system_prompt = """
You are the workflow orchestrator for a vacation planning system.

Your job is to choose exactly one next action.

Allowed actions:
- extract_request
- research_destinations
- finalize

You must return ONLY valid JSON.
Do not return markdown.
Do not return explanations outside JSON.
Do not return extra keys.

Return exactly this shape:
{
  "action": "extract_request" | "research_destinations" | "finalize",
  "reason": "short explanation"
}

Decision rules:
- If the request has not yet been extracted, choose "extract_request".
- If the request is extracted but destination options are missing, choose "research_destinations".
- If destination options already exist, choose "finalize".
"""

    async def decide(self, state_json: str) -> OrchestratorAction:
        return await self.run_structured(state_json, OrchestratorAction)