import json
from app.core.logging import get_logger
from dataclasses import dataclass
from typing import Any

from app.providers.openai_responses import safe_json_dumps
from app.tools.core.registry import ToolRegistry, ToolSet

logger = get_logger(__name__)


@dataclass(slots=True)
class ExecutedToolCall:
    name: str
    arguments: dict[str, Any]
    result: Any
    ok: bool


class ToolExecutor:
    def __init__(self, tools: ToolRegistry | ToolSet) -> None:
        self.tools = tools

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ExecutedToolCall:
        try:
            result = await self.tools.run(tool_name, arguments)
            return ExecutedToolCall(
                name=tool_name,
                arguments=arguments,
                result=result,
                ok=True,
            )
        except Exception as exc:
            logger.exception("Tool execution failed: %s", tool_name)
            return ExecutedToolCall(
                name=tool_name,
                arguments=arguments,
                result={
                    "ok": False,
                    "error": {
                        "type": exc.__class__.__name__,
                        "tool_name": tool_name,
                        "message": str(exc),
                    },
                },
                ok=False,
            )

    @staticmethod
    def parse_arguments(raw_arguments: Any) -> dict[str, Any]:
        if isinstance(raw_arguments, dict):
            return raw_arguments

        if isinstance(raw_arguments, str):
            if not raw_arguments.strip():
                return {}
            try:
                parsed = json.loads(raw_arguments)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}

        return {}

    @staticmethod
    def serialize_result(result: Any) -> str:
        if isinstance(result, str):
            return result
        return safe_json_dumps(result)