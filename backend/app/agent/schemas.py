from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    step_id: int
    description: str
    tool_name: str
    tool_args: str
    depends_on: list[int]= Field(default_factory=list)

class Plan(BaseModel):
    reasoning: str
    steps: list[PlanStep]

class StepResults(BaseModel):
    step_id: int
    tool_name: str
    result: str
    ok: bool = True