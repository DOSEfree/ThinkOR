"""Response parsing helpers for the single-call LLM flow."""

import json
from json import JSONDecodeError

from pydantic import ValidationError

from ideaos_agent.domain.errors import LlmResponseFormatError
from ideaos_agent.models import IdeaAnalysis


def parse_idea_analysis_response(raw_text: str) -> IdeaAnalysis:
    """Parse raw LLM output into the Phase 1 IdeaAnalysis contract."""

    normalized = _strip_code_fence(raw_text)
    payload = _parse_json_object(normalized)
    coerced = _coerce_payload(payload)

    try:
        return IdeaAnalysis.model_validate(coerced)
    except ValidationError as exc:
        raise LlmResponseFormatError("LLM 返回无法解析为 IdeaAnalysis。") from exc


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
            raise LlmResponseFormatError("LLM 未返回可解析的 JSON 对象。") from None
        try:
            payload = json.loads(raw_text[start : end + 1])
        except JSONDecodeError as exc:
            raise LlmResponseFormatError("LLM JSON 解析失败。") from exc

    if not isinstance(payload, dict):
        raise LlmResponseFormatError("LLM 输出的顶层结构不是 JSON 对象。")

    return payload


def _coerce_payload(payload: dict[str, object]) -> dict[str, object]:
    """Apply minimal local coercion before Pydantic validation."""

    list_fields = {
        "knowledge_gaps",
        "resource_gaps",
        "team_requirements",
        "similar_projects",
        "mvp_roadmap",
        "long_term_roadmap",
    }
    coerced: dict[str, object] = {}

    for key, value in payload.items():
        if key in list_fields and isinstance(value, str):
            coerced[key] = [value.strip()] if value.strip() else []
            continue
        if isinstance(value, str):
            coerced[key] = value.strip()
            continue
        coerced[key] = value

    return coerced
