import json
import logging
import re

logger = logging.getLogger(__name__)


def parse_ai_response(response: str) -> dict:
    """
    Convert the raw Gemini response into a Python dictionary.

    Handles multiple code fence formats and validates
    the response against the expected schema.
    """

    text = response.strip()

    # Strip various code fence formats
    # Match ```json, ```JSON, ``` or any other language tag
    fence_pattern = re.compile(
        r"^```(?:json|JSON)?\s*\n?(.*?)\n?```$",
        re.DOTALL
    )
    match = fence_pattern.match(text)
    if match:
        text = match.group(1).strip()

    # Try to parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        preview = text[:500] + ("..." if len(text) > 500 else "")
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.error(f"Response preview: {preview}")
        raise ValueError(
            f"AI returned invalid JSON: {e}. "
            f"Response preview: {preview[:200]}"
        ) from e

    # Validate expected schema
    _validate_schema(data)

    return data


def _validate_schema(data: dict) -> None:
    """Validate that the parsed JSON matches the expected schema."""

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a JSON object, got {type(data).__name__}"
        )

    if "knowledge_units" not in data:
        raise ValueError(
            "AI response missing required field: 'knowledge_units'"
        )

    units = data["knowledge_units"]
    if not isinstance(units, list):
        raise ValueError(
            f"'knowledge_units' must be a list, got {type(units).__name__}"
        )

    if len(units) == 0:
        raise ValueError(
            "AI returned zero knowledge units"
        )

    for i, unit in enumerate(units):
        if "title" not in unit:
            raise ValueError(f"Knowledge unit {i} missing 'title'")
        if "segments" not in unit:
            raise ValueError(f"Knowledge unit {i} missing 'segments'")

        # Validate each segment has the required fields
        for j, segment in enumerate(unit["segments"]):
            if not isinstance(segment, dict):
                raise ValueError(
                    f"Knowledge unit {i} ('{unit['title']}'), "
                    f"segment {j}: expected a dict, got {type(segment).__name__}"
                )
            for field in ("page", "start_paragraph", "end_paragraph"):
                if field not in segment:
                    raise ValueError(
                        f"Knowledge unit {i} ('{unit['title']}'), "
                        f"segment {j}: missing required field '{field}'"
                    )
                if not isinstance(segment[field], int):
                    raise ValueError(
                        f"Knowledge unit {i} ('{unit['title']}'), "
                        f"segment {j}: '{field}' must be an integer, "
                        f"got {type(segment[field]).__name__}"
                    )

        # Validate page range fields (used by generator for metadata)
        for field in ("start_page", "end_page"):
            if field not in unit:
                raise ValueError(
                    f"Knowledge unit {i} ('{unit['title']}') "
                    f"missing required field '{field}'"
                )
            if not isinstance(unit[field], int):
                raise ValueError(
                    f"Knowledge unit {i} ('{unit['title']}'): "
                    f"'{field}' must be an integer, "
                    f"got {type(unit[field]).__name__}"
                )

        # Validate metadata enrichment fields exist
        if "type" not in unit or not unit["type"]:
            logger.warning(
                f"Knowledge unit {i} ('{unit['title']}') "
                f"missing 'type', defaulting to 'Concept'"
            )

        if "category" not in unit or not unit["category"]:
            logger.warning(
                f"Knowledge unit {i} ('{unit['title']}') "
                f"missing 'category', defaulting to 'concepts'"
            )