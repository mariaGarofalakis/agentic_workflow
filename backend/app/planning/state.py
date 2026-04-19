from pydantic import BaseModel, Field
from typing import Literal


class TripRequest(BaseModel):
    origin: str | None = None
    destination: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    interests: list[str] = Field(default_factory=list)
    budget: float | None = None


class DestinationOption(BaseModel):
    name: str
    country: str | None = None
    reason: str


class TripPlanState(BaseModel):
    request: TripRequest = Field(default_factory=TripRequest)
    destinations: list[DestinationOption] = Field(default_factory=list)
    chosen_destination: DestinationOption | None = None
    step: str = "start"
    messages: list[str] = Field(default_factory=list)