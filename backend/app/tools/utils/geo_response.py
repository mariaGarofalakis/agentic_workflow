import httpx


async def geo_response(location: str):
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
        return lat, lon, place

    except httpx.HTTPError as exc:
            return {
                "ok": False,
                "error": {
                    "type": "http_error",
                    "message": str(exc),
                },
            }