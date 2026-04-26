from typing import Any


class ResponseTextExtractor:
    @staticmethod
    def extract_text(response: Any) -> str:
        """
        Extract assistant text from a final Responses API object.

        Supports:
        - response.output_text
        - response.output[].content[].text
        """
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text:
            return output_text

        parts: list[str] = []

        for item in getattr(response, "output", []):
            if getattr(item, "type", None) != "message":
                continue

            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    parts.append(getattr(content, "text", ""))

        return "".join(parts)