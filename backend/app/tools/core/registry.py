import inspect
from app.core.logging import get_logger
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

logger = get_logger(__name__)

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
    

    def describe(self, names: list[str] | None = None) -> str:
        """
        Return a compact, human-readable description of tools for prompting.

        Output is optimized for LLM consumption:
        - deterministic ordering
        - no extra verbosity
        - clear parameter structure
        """

        tools = (
            [self.get_tool(name) for name in names]
            if names is not None
            else list(self._tools.values())
        )

        lines: list[str] = []

        for tool in tools:
            schema = tool.schema
            name = schema.get("name", "unknown_tool")
            description = schema.get("description", "").strip()

            lines.append(f"Tool: {name}")
            if description:
                lines.append(f"Description: {description}")

            params = schema.get("parameters", {})
            properties: dict[str, Any] = params.get("properties", {}) or {}
            required: set[str] = set(params.get("required", []) or [])

            if properties:
                lines.append("Arguments:")

                for param_name in sorted(properties.keys()):
                    prop = properties[param_name] or {}
                    p_type = prop.get("type", "any")
                    p_desc = prop.get("description", "").strip()

                    req = "required" if param_name in required else "optional"

                    if p_desc:
                        lines.append(
                            f"  - {param_name} ({p_type}, {req}): {p_desc}"
                        )
                    else:
                        lines.append(
                            f"  - {param_name} ({p_type}, {req})"
                        )
            else:
                lines.append("Arguments: none")

            lines.append("")  # spacing between tools

        return "\n".join(lines).strip()

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