import httpx
from typing import Any

from app.tools.core.registry import ToolRegistry
from app.tools.utils.geo_response import geo_response


def register_weather_forecast_tool(registry: ToolRegistry) -> None:
    @registry.register(
        {
            "type": "function",
            "name": "get_weather_forecast",
            "description": (
                "Get a multi-day weather forecast for a given location. "
                "Returns daily high/low temperatures, precipitation probability, "
                "and weather codes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or place name, e.g. 'Copenhagen' or 'New York'",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of forecast days (1-14, default 7)",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit (default: celsius)",
                    },
                },
                "required": ["location"],
                "additionalProperties": False,
            },
        }
    )
    async def get_weather_forecast(
        location: str, days: int = 7, unit: str = "celsius"
    ) -> dict[str, Any]:
        days = max(1, min(days, 14))
        temperature_unit = "fahrenheit" if unit == "fahrenheit" else "celsius"

        result =  await geo_response(location=location)
        
        lat,lon, place = result

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                weather_response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "daily": (
                            "temperature_2m_max,"
                            "temperature_2m_min,"
                            "precipitation_probability_max,"
                            "weather_code"
                        ),
                        "temperature_unit": temperature_unit,
                        "timezone": "auto",
                        "forecast_days": days,
                    },
                )
                weather_response.raise_for_status()
                weather_data = weather_response.json()

            daily = weather_data.get("daily", {})
            dates = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_probability_max", [])
            codes = daily.get("weather_code", [])

            forecast = []
            for i, date in enumerate(dates):
                forecast.append(
                    {
                        "date": date,
                        "temp_high": temp_max[i] if i < len(temp_max) else None,
                        "temp_low": temp_min[i] if i < len(temp_min) else None,
                        "precipitation_probability": precip[i] if i < len(precip) else None,
                        "weather_code": codes[i] if i < len(codes) else None,
                    }
                )

            unit_symbol = "°F" if unit == "fahrenheit" else "°C"

            return {
                "ok": True,
                "data": {
                    "location": f"{place['name']}, {place.get('country', '')}".strip(", "),
                    "latitude": lat,
                    "longitude": lon,
                    "temperature_unit": unit_symbol,
                    "forecast_days": days,
                    "forecast": forecast,
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