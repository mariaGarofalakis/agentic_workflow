from pydantic import ValidationError


class StructuredOutputError(RuntimeError):
    pass


def build_structured_output_error(
    *,
    max_attempts: int,
    raw_text: str,
    exc: ValidationError,
) -> StructuredOutputError:
    return StructuredOutputError(
        f"Failed to obtain valid structured output after "
        f"{max_attempts} attempts.\n\n"
        f"Last raw output:\n{raw_text}\n\n"
        f"Validation error:\n{exc}"
    )