from app.tools.core.registry import ToolRegistry
from app.tools.weather import register_weather_tool


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_weather_tool(registry)
    return registry