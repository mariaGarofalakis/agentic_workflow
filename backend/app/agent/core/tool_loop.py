from typing import Any

from app.tools.core.executor import ToolExecutor
from app.tools.core.registry import ToolRegistry, ToolSet
from app.core.logging import get_logger

class ToolLoopRunner:
    def __init__(self, tools: ToolRegistry | ToolSet) -> None:
        self.tools = tools
        self.executor = ToolExecutor(tools)
        self.logger = get_logger(__name__)

    async def collect_tool_outputs(
        self,
        response: Any,
    ) -> list[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []

        for item in getattr(response, "output", []):
            item_type = getattr(item, "type", None)

            self.logger.info(
                "MODEL OUTPUT ITEM: type=%s name=%s call_id=%s",
                item_type,
                getattr(item, "name", None),
                getattr(item, "call_id", None),
            )

            if item_type not in {"function_call", "tool_call"}:
                continue

            tool_name = getattr(item, "name", "")
            call_id = getattr(item, "call_id", None)
            raw_args = getattr(item, "arguments", {})

            self.logger.info(
                "EXECUTING TOOL CALL: name=%s args=%s",
                tool_name,
                raw_args,
            )

            parsed_args = self.executor.parse_arguments(raw_args)
            executed = await self.executor.execute(tool_name, parsed_args)

            self.logger.info(
                "TOOL EXECUTED: name=%s ok=%s result=%s",
                executed.name,
                executed.ok,
                executed.result,
            )

            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": self.executor.serialize_result(executed.result),
                }
            )

        return outputs