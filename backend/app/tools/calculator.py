import ast
import operator
from app.core.logging import get_logger
from typing import Any

from app.tools.core.registry import ToolRegistry

logger = get_logger(__name__)


# Supported operators
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    elif isinstance(node, ast.Constant):  # numbers
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Invalid constant")

    elif isinstance(node, ast.BinOp):  # binary ops
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        op_type = type(node.op)

        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type}")

        return _OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):  # -x, +x
        operand = _safe_eval(node.operand)
        op_type = type(node.op)

        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type}")

        return _OPERATORS[op_type](operand)

    else:
        raise ValueError(f"Unsupported expression: {type(node)}")


def register_calculator_tool(registry: ToolRegistry) -> None:
    @registry.register(
        {
            "type": "function",
            "name": "calculator",
            "description": (
                "Evaluate a mathematical expression. Supports +,-,*,/,//,%,** and parenthesis "
                "example: (150 * 3) + 50"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate e.g. '100*7/3'",
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        }
    )
    async def calculator(expression: str) -> dict[str, Any]:
        try:
            parsed = ast.parse(expression, mode="eval")
            result = _safe_eval(parsed)

            return {
                "ok": True,
                "data": {
                    "expression": expression,
                    "result": result,
                },
            }

        except Exception:
            logger.exception(
                "Error evaluating expression",
                extra={"expression": expression},
            )
            return {
                "ok": False,
                "error": {
                    "type": "evaluation_error",
                    "message": "Invalid mathematical expression",
                },
            }