import httpx
from typing import Any

from app.tools.core.registry import ToolRegistry


def register_weather_tool(registry: ToolRegistry) -> None:
    @registry.register(
        {
            "type": "function",
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or place name, e.g. 'Copenhagen' or 'New York'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                    },
                },
                "required": ["location"],
                "additionalProperties": False,
            },
        }
    )
    async def get_current_weather(location: str, unit: str = "celsius") -> dict[str, Any]:
        temperature_unit = "fahrenheit" if unit == "fahrenheit" else "celsius"

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                geo_response = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={
                        "name": location,
                        "count": 1,
                        "language": "en",
                        "format": "json",
                    },
                )
                geo_response.raise_for_status()
                geo_data = geo_response.json()

                results = geo_data.get("results", [])
                if not results:
                    return {
                        "ok": False,
                        "error": {
                            "type": "not_found",
                            "message": f"Could not find location: {location}",
                        },
                    }

                place = results[0]
                lat = place["latitude"]
                lon = place["longitude"]

                weather_response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,weather_code,wind_speed_10m",
                        "temperature_unit": temperature_unit,
                        "timezone": "auto",
                    },
                )
                weather_response.raise_for_status()
                weather_data = weather_response.json()

            current = weather_data.get("current", {})

            return {
                "ok": True,
                "data": {
                    "location": f'{place["name"]}, {place.get("country", "")}'.strip(", "),
                    "latitude": lat,
                    "longitude": lon,
                    "temperature": current.get("temperature_2m"),
                    "temperature_unit": "°F" if unit == "fahrenheit" else "°C",
                    "weather_code": current.get("weather_code"),
                    "wind_speed_10m": current.get("wind_speed_10m"),
                },
            }

        except httpx.HTTPError as exc:
            return {
                "ok": False,
                "error": {
                    "type": "http_error",
                    "message": str(exc),
                },
            }