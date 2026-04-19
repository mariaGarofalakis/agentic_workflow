import inspect
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(slots=True, frozen=True)
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

            name = schema.get("name")
            if not name or not isinstance(name, str):
                raise ValueError("Tool schema must include a non-empty 'name'")

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

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool(self, name: str) -> RegisteredTool:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        return tool

    def get_schemas(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        if names is None:
            return [tool.schema for tool in self._tools.values()]
        return [self.get_tool(name).schema for name in names]

    async def run(self, name: str, tool_input: dict[str, Any]) -> Any:
        tool = self.get_tool(name)
        return await tool.handler(**tool_input)

    def subset(self, names: list[str]) -> "ToolSet":
        return ToolSet(registry=self, allowed_names=names)


class ToolSet:
    def __init__(self, registry: ToolRegistry, allowed_names: list[str]) -> None:
        unique_names: list[str] = []
        seen: set[str] = set()

        for name in allowed_names:
            if name in seen:
                continue
            if not registry.has_tool(name):
                raise ValueError(f"Cannot create ToolSet: unknown tool '{name}'")
            seen.add(name)
            unique_names.append(name)

        self._registry = registry
        self._allowed_names = unique_names

    @property
    def names(self) -> list[str]:
        return list(self._allowed_names)

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return self._registry.get_schemas(self._allowed_names)

    def has_tool(self, name: str) -> bool:
        return name in self._allowed_names

    async def run(self, name: str, tool_input: dict[str, Any]) -> Any:
        if name not in self._allowed_names:
            raise PermissionError(f"Tool '{name}' is not available in this ToolSet")
        return await self._registry.run(name, tool_input)