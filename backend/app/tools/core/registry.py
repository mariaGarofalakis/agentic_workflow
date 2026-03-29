import inspect
import logging
from typing import Any
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


logger = logging.getLogger(__name__)


ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(slots=True)
class RegisteredTool:
    name: str
    schema: dict[str, Any]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, schema: dict[str, Any]):
        def decorator(func: ToolHandler) -> ToolHandler:
            if not inspect.iscoroutinefunction(func):
                raise TypeError(f"Tool '{schema.get('name')}' must be async")

            name = schema["name"]
            if name in self._tools:
                raise ValueError(f"Tool '{name}' already registered")

            self._tools[name] = RegisteredTool(
                name=name,
                schema=schema,
                handler=func,
            )
            logger.debug("Registered tool: %s", name)
            return func

        return decorator

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema for tool in self._tools.values()]

    async def run(self, name: str, tool_input: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")

        return await tool.handler(**tool_input)

    def has_tool(self, name: str) -> bool:
        return name in self._tools
