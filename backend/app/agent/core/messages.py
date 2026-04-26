import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError


class MessageBuilder:
    @staticmethod
    def current_date_utc() -> str:
        return datetime.now(UTC).date().isoformat()

    @staticmethod
    def schema_to_prompt(schema: type[BaseModel]) -> str:
        return json.dumps(
            schema.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )

    @staticmethod
    def build_messages(
        system_prompt: str,
        user_content: str,
    ) -> list[dict[str, Any]]:
        return [
            # Keep "developer" because your project has been using it.
            # If your local model behaves strangely, try "system".
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    @staticmethod
    def build_text_format(schema: type[BaseModel]) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": schema.__name__,
            "schema": schema.model_json_schema(),
            "strict": True,
        }

    @staticmethod
    def build_repair_message(exc: ValidationError) -> dict[str, str]:
        return {
            "role": "developer",
            "content": (
                "Your previous response did not match the required JSON schema.\n"
                "Return ONLY valid JSON that matches the schema exactly.\n"
                "Do not include markdown fences, prose, or extra keys.\n"
                f"Validation error:\n{exc}"
            ),
        }