"""Response parsing helpers for analysis and follow-up LLM flows."""

import json
from json import JSONDecodeError

from pydantic import ValidationError

from ideaos_agent.domain.errors import LlmResponseFormatError
from ideaos_agent.models import FollowUpLlmOutput, IdeaAnalysisLlmOutput


def parse_idea_analysis_response(raw_text: str) -> IdeaAnalysisLlmOutput:
    """Parse raw LLM output into the root-analysis wrapper contract."""

    normalized = _strip_code_fence(raw_text)
    payload = _parse_json_object(normalized)
    coerced = _coerce_payload(payload)

    try:
        return IdeaAnalysisLlmOutput.model_validate(coerced)
    except ValidationError as exc:
        summary = _summarize_validation_error(exc)
        raise LlmResponseFormatError(
            "LLM output could not be parsed into IdeaAnalysisLlmOutput: "
            f"{summary}",
            raw_output=raw_text,
        ) from exc


def parse_follow_up_response(raw_text: str) -> FollowUpLlmOutput:
    """Parse raw LLM output into the follow-up wrapper contract."""

    normalized = _strip_code_fence(raw_text)
    payload = _parse_json_object(normalized)
    coerced = _coerce_payload(payload)

    try:
        return FollowUpLlmOutput.model_validate(coerced)
    except ValidationError as exc:
        summary = _summarize_validation_error(exc)
        raise LlmResponseFormatError(
            "LLM output could not be parsed into FollowUpLlmOutput: "
            f"{summary}",
            raw_output=raw_text,
        ) from exc


def _strip_code_fence(raw_text: str) -> str:
    """Remove optional markdown code fences from model output."""

    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return text


def _parse_json_object(raw_text: str) -> dict[str, object]:
    """Parse a JSON object from text, allowing simple surrounding noise."""

    try:
        payload = json.loads(raw_text)
    except JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LlmResponseFormatError("LLM did not return a parseable JSON object.") from None
        try:
            payload = json.loads(raw_text[start : end + 1])
        except JSONDecodeError as exc:
            raise LlmResponseFormatError("LLM JSON parsing failed.") from exc

    if not isinstance(payload, dict):
        raise LlmResponseFormatError("LLM top-level output must be a JSON object.")

    return payload


def _coerce_payload(payload: dict[str, object]) -> dict[str, object]:
    """Apply minimal local coercion before Pydantic validation."""

    list_fields = {
        "assumptions",
        "open_questions",
        "affected_sections",
        "updated_items",
        "knowledge_gaps",
        "resource_gaps",
        "team_requirements",
        "similar_projects",
        "mvp_roadmap",
        "long_term_roadmap",
        "proposed_section_updates",
        "next_actions",
    }
    dict_fields = {"analysis", "refinement_result"}
    coerced: dict[str, object] = {}

    for key, value in payload.items():
        if key in list_fields and value is None:
            coerced[key] = []
            continue
        if key in list_fields and isinstance(value, dict):
            coerced[key] = [_coerce_payload(value)]
            continue
        if key in dict_fields and value is None:
            coerced[key] = None
            continue
        if key in dict_fields and isinstance(value, dict):
            coerced[key] = _coerce_payload(value)
            continue
        if isinstance(value, list):
            coerced[key] = [
                (
                    _coerce_payload(item)
                    if isinstance(item, dict)
                    else item.strip()
                    if isinstance(item, str)
                    else item
                )
                for item in value
            ]
            continue
        if key in list_fields and isinstance(value, str):
            coerced[key] = [value.strip()] if value.strip() else []
            continue
        if isinstance(value, str):
            coerced[key] = value.strip()
            continue
        coerced[key] = value

    return coerced


def _summarize_validation_error(exc: ValidationError) -> str:
    """Render the first validation error as a short human-readable summary."""

    details = exc.errors()
    if not details:
        return "unknown validation error"

    first = details[0]
    loc = ".".join(str(part) for part in first.get("loc", [])) or "root"
    message = str(first.get("msg", "validation error"))
    return f"{loc}: {message}"
