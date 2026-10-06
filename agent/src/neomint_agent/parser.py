"""Model output parser for NeoMint.

Extracts and validates structured JSON from the LLM's raw text response.
Handles common LLM quirks: JSON wrapped in markdown code fences,
trailing commas, and extra whitespace.

If parsing fails, a Refusal is returned — the system never crashes
due to unexpected model output.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from neomint_agent.schemas import Clarification, Plan, PlannerOutput, Refusal

logger = logging.getLogger("neomint-agent.parser")

# Pattern to extract JSON from markdown code fences
_CODE_FENCE_PATTERN = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?\s*```",
    re.DOTALL,
)

# Pattern to find the outermost JSON object
_JSON_OBJECT_PATTERN = re.compile(
    r"\{.*\}",
    re.DOTALL,
)


def _extract_json_string(raw: str) -> str | None:
    """Extract a JSON object string from raw model output.

    Tries in order:
    1. JSON inside markdown code fences
    2. First bare JSON object in the text
    3. The entire string as JSON
    """
    # Try code fence extraction first
    fence_match = _CODE_FENCE_PATTERN.search(raw)
    if fence_match:
        return fence_match.group(1).strip()

    # Try to find a bare JSON object
    obj_match = _JSON_OBJECT_PATTERN.search(raw)
    if obj_match:
        return obj_match.group(0).strip()

    # Last resort: try the entire string
    stripped = raw.strip()
    if stripped.startswith("{"):
        return stripped

    return None


def _clean_json_string(raw_json: str) -> str:
    """Clean common LLM JSON quirks.

    - Remove trailing commas before } or ]
    - Strip BOM and zero-width characters
    """
    # Remove BOM and zero-width chars
    cleaned = raw_json.replace("\ufeff", "").replace("\u200b", "")

    # Remove trailing commas (common LLM error)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    return cleaned


def parse_model_output(raw: str) -> PlannerOutput:
    """Parse raw model text into a structured PlannerOutput.

    Args:
        raw: The raw text response from the Ollama model.

    Returns:
        A Plan, Clarification, or Refusal. Never raises — returns
        a Refusal with error details if parsing fails.
    """
    if not raw or not raw.strip():
        return Refusal(
            kind="refusal",
            message="The model returned an empty response.",
        )

    json_str = _extract_json_string(raw)
    if json_str is None:
        logger.warning("No JSON found in model output: %s", raw[:200])
        return Refusal(
            kind="refusal",
            message=(
                "The model did not return valid JSON. "
                "Raw response has been logged for debugging."
            ),
        )

    json_str = _clean_json_string(json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error: %s — raw: %s", exc, json_str[:200])
        return Refusal(
            kind="refusal",
            message=f"The model returned malformed JSON: {exc}",
        )

    if not isinstance(data, dict):
        return Refusal(
            kind="refusal",
            message="The model returned a JSON value that is not an object.",
        )

    kind = data.get("kind")
    if kind not in {"plan", "clarification", "refusal"}:
        logger.warning("Unknown 'kind' in model output: %s", kind)
        return Refusal(
            kind="refusal",
            message=f"Unknown response kind: '{kind}'. Expected plan, clarification, or refusal.",
        )

    try:
        if kind == "plan":
            return Plan.model_validate(data)
        elif kind == "clarification":
            return Clarification.model_validate(data)
        else:
            return Refusal.model_validate(data)
    except ValidationError as exc:
        logger.warning("Schema validation failed: %s", exc)
        return Refusal(
            kind="refusal",
            message=f"The model's response failed schema validation: {exc.error_count()} error(s).",
        )
