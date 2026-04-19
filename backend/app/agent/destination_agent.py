from pydantic import BaseModel, Field
from app.agent.core.worker import WorkerAgent
from app.planning.state import DestinationOption


class DestinationResult(BaseModel):
    options: list[DestinationOption] = Field(default_factory=list)


class DestinationAgent(WorkerAgent):
    system_prompt = """
You are a travel destination expert.

Suggest 3 destinations based on user request.

Keep answers realistic and concise.
Return only structured JSON.
"""