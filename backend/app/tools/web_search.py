import asyncio
from app.core.logging import get_logger
from typing import Any

from app.tools.core.registry import ToolRegistry

logger = get_logger(__name__)


def register_web_search_tool(registry: ToolRegistry) -> None:
    @registry.register(
        {
            "type": "function",
            "name": "search_web_duckduckgo",
            "description": (
                "Search web for information using DuckDuckGo. "
                "Returns a list of results with title, URL, and sinppets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query e.g. best restaurants in New York City",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-10, default 5)",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        }
    )
    async def search_web_duckduckgo(
        query: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        max_results = max(1, min(max_results, 10))

        try:
            from ddgs import DDGS
        except ImportError:
            logger.exception("ddgs dependency is not installed")
            return {
                "ok": False,
                "error": {
                    "type": "missing_dependency",
                    "message": "The 'ddgs' package is not installed",
                },
            }

        try:
            def _search() -> list[dict[str, Any]]:
                with DDGS() as ddgs:
                    raw_results = ddgs.text(query, max_results=max_results)
                    return [
                        {
                            "title": item.get("title"),
                            "url": item.get("href"),
                            "snippet": item.get("body"),
                        }
                        for item in (raw_results or [])
                    ]

            results = await asyncio.to_thread(_search)

            return {
                "ok": True,
                "data": {
                    "query": query,
                    "max_results": max_results,
                    "results": results,
                },
            }

        except Exception:
            logger.exception(
                "Unexpected error in search_web_duckduckgo",
                extra={"query": query, "max_results": max_results},
            )
            return {
                "ok": False,
                "error": {
                    "type": "internal_error",
                    "message": "An unexpected error occurred while searching DuckDuckGo",
                },
            }