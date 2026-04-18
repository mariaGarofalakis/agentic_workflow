import httpx
import logging
from typing import Any
from urllib.parse import quote

from app.tools.core.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_wikipedia_place_info_tool(registry: ToolRegistry) -> None:
    @registry.register(
        {
            "type": "function",
            "name": "get_wikipedia_place_info",
            "description": (
                "Get summary information about a city, landmark, or topic from wikipedia. "
                "returns a title, description, extract, image URL, and coordinates if available"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to look up, e.g. 'New York', 'Parthenon'",
                    }
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        }
    )
    async def get_wikipedia_place_info(topic: str) -> dict[str, Any]:
        try:
            encoded_topic = quote(topic, safe="")

            headers = {
                "User-Agent": "my-app/1.0 (contact@example.com)"
            }

            async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
                response = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"
                )

                if response.status_code == 404:
                    logger.warning(
                        "Wikipedia page not found",
                        extra={"topic": topic, "encoded_topic": encoded_topic},
                    )
                    return {
                        "ok": False,
                        "error": {
                            "type": "not_found",
                            "message": f"No Wikipedia page found for '{topic}'",
                        },
                    }

                response.raise_for_status()
                data = response.json()

            coordinates = data.get("coordinates")
            thumbnail = data.get("thumbnail", {})
            content_urls = data.get("content_urls", {}).get("desktop", {})

            return {
                "ok": True,
                "data": {
                    "topic": topic,
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "extract": data.get("extract"),
                    "image_url": thumbnail.get("source"),
                    "coordinates": {
                        "lat": coordinates.get("lat"),
                        "lon": coordinates.get("lon"),
                    }
                    if coordinates
                    else None,
                    "wikipedia_url": content_urls.get("page"),
                },
            }

        except httpx.HTTPError as exc:
            logger.error(
                "HTTP error while fetching Wikipedia data",
                exc_info=True,
                extra={"topic": topic},
            )
            return {
                "ok": False,
                "error": {
                    "type": "http_error",
                    "message": str(exc),
                },
            }

        except Exception as exc:
            logger.exception(
                "Unexpected error in get_wikipedia_place_info",
                extra={"topic": topic},
            )
            return {
                "ok": False,
                "error": {
                    "type": "internal_error",
                    "message": "An unexpected error occurred",
                },
            }