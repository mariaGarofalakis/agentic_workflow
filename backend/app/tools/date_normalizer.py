from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import dateparser

from app.core.logging import get_logger
from app.tools.core.registry import ToolRegistry


logger = get_logger()

def register_date_normalizer_tool(registry: ToolRegistry) -> None:
    @registry.register(
        {
            "type": "function",
            "name": "normalize_travel_dates",
            "description": (
                "Normalize natural-language travel date phrases into ISO start_date "
                "and end_date values. Useful for phrases like 'next weekend', "
                "'tomorrow', 'in two weeks', 'May 3rd', or 'from June 1 to June 5'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_text": {
                        "type": "string",
                        "description": (
                            "The natural-language date phrase from the user, "
                            "e.g. 'next weekend', 'tomorrow', 'May 3rd', "
                            "'from June 1 to June 5'."
                        ),
                    },
                    "duration_days": {
                        "type": "integer",
                        "description": (
                            "Trip duration in days if known. Used to infer end_date "
                            "when the date phrase only gives a start date."
                        ),
                    },
                    "timezone": {
                        "type": "string",
                        "description": (
                            "IANA timezone used as the relative base. "
                            "Default is Europe/Copenhagen."
                        ),
                    },
                },
                "required": ["date_text"],
                "additionalProperties": False,
            },
        }
    )
    async def normalize_travel_dates(
        date_text: str,
        duration_days: int | None = None,
        timezone: str = "Europe/Copenhagen",
    ) -> dict[str, Any]:
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = UTC

        today_dt = datetime.now(tz)
        today = today_dt.date()

        cleaned = date_text.strip()
        lowered = cleaned.lower()

        logger.info("DATE NORMALIZER IS CALLED")

        if not cleaned:
            return {
                "ok": False,
                "error": {
                    "type": "empty_date_text",
                    "message": "date_text was empty.",
                },
            }

        # Travel-specific rule because generic parsers often do not define
        # what "weekend" means as a date range.
        if "weekend" in lowered:
            start = _resolve_weekend_start(
                text=lowered,
                today=today,
            )
            days = _safe_duration_days(duration_days, default=2)
            end = start + timedelta(days=days - 1)

            return {
                "ok": True,
                "data": {
                    "date_text": date_text,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "duration_days": days,
                    "is_date_range_clear": True,
                    "timezone": str(tz),
                    "method": "weekend_rule",
                },
            }

        parsed = dateparser.parse(
            cleaned,
            settings={
                "RELATIVE_BASE": today_dt,
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TIMEZONE": str(tz),
            },
        )

        if parsed is None:
            return {
                "ok": False,
                "error": {
                    "type": "unparseable_date",
                    "message": f"Could not normalize date phrase: {date_text}",
                },
            }

        start = parsed.date()
        days = _safe_duration_days(duration_days, default=1)
        end = start + timedelta(days=days - 1)

        return {
            "ok": True,
            "data": {
                "date_text": date_text,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "duration_days": days,
                "is_date_range_clear": True,
                "timezone": str(tz),
                "method": "dateparser",
            },
        }


def _safe_duration_days(
    duration_days: int | None,
    default: int,
) -> int:
    if duration_days is None:
        return default

    return max(1, min(duration_days, 60))


def _resolve_weekend_start(
    text: str,
    today: date,
) -> date:
    # Python weekday: Monday=0, Saturday=5, Sunday=6.
    days_until_saturday = (5 - today.weekday()) % 7

    if "next weekend" in text:
        # Product choice:
        # "next weekend" means the upcoming Saturday if today is before Saturday,
        # and the following Saturday if today is already Saturday/Sunday.
        if today.weekday() >= 5:
            days_until_saturday += 7

        if days_until_saturday == 0:
            days_until_saturday = 7

        return today + timedelta(days=days_until_saturday)

    if "this weekend" in text:
        if days_until_saturday == 0:
            return today

        if today.weekday() == 6:
            # It is already Sunday. Treat this weekend as today.
            return today

        return today + timedelta(days=days_until_saturday)

    # Plain "weekend" defaults to upcoming Saturday.
    if days_until_saturday == 0:
        return today

    return today + timedelta(days=days_until_saturday)