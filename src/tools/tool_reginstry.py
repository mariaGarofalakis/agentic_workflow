from typing import Any, Callable, Awaitable
import src.tools.agents.weather

class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Callable[..., Awaitable[Any]]] = {}
        self.schemas: list[dict[str, Any]] = []

    def register(self, schema: dict[str, Any]):
        def decorator(func: Callable[..., Awaitable[Any]]):
            name = schema["name"]

            self.tools[name] = func
            self.schemas.append(schema)

            return func
        return decorator

    async def run(self, name: str, tool_input: dict[str, Any]):
        tool = self.tools.get(name)

        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        return await tool(**tool_input)


# global singleton
tool_registry = ToolRegistry()