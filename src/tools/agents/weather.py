import httpx
from src.tools.tool_reginstry import tool_registry

@tool_registry.register(
    {
        "type": "function",
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["location"],
        },
    }
)
async def get_current_weather(location: str, unit: str = "celsius") -> dict:
    temp_unit = "fahrenheit" if unit == "fahrenheit" else "celsius"

    async with httpx.AsyncClient(timeout=20.0) as client:
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "en", "format": "json"},
        )
        geo.raise_for_status()
        geo_data = geo.json()

        results = geo_data.get("results", [])
        if not results:
            return {"error": f"Could not find location: {location}"}

        place = results[0]
        lat = place["latitude"]
        lon = place["longitude"]

        weather = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "temperature_unit": temp_unit,
                "timezone": "auto",
            },
        )
        weather.raise_for_status()
        weather_data = weather.json()

    current = weather_data.get("current", {})

    return {
        "location": f'{place["name"]}, {place.get("country", "")}'.strip(", "),
        "latitude": lat,
        "longitude": lon,
        "temperature": current.get("temperature_2m"),
        "temperature_unit": "°F" if unit == "fahrenheit" else "°C",
        "weather_code": current.get("weather_code"),
        "wind_speed_10m": current.get("wind_speed_10m"),
    }