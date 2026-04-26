from typing import Any, Literal, TypedDict


class AgentChunkEvent(TypedDict):
    type: Literal["chunk"]
    content: str


class AgentCompletedEvent(TypedDict):
    type: Literal["completed"]
    final_response_id: str | None


class AgentErrorEvent(TypedDict):
    type: Literal["error"]
    message: str


AgentEvent = AgentChunkEvent | AgentCompletedEvent | AgentErrorEvent