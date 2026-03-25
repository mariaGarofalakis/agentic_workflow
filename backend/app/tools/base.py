from dataclasses import dataclass
from typing import Any, Awaitable, Callable


ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(slots=True)
class RegisteredTool:
    name: str
    schema: dict[str, Any]
    handler: ToolHandler