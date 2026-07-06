"""Render completed session archives into Feishu Docx XML content."""

from datetime import datetime
from html import escape

from ideaos_agent.domain.archive import SessionArchivePayload, SessionClarificationRecord

ARCHIVE_TITLE_PREFIX = "IdeaOS Archive | "
FALLBACK_COPY = "暂无补充内容。"


def build_feishu_archive_title(payload: SessionArchivePayload) -> str:
    """Build the final human-facing Feishu document title."""

    semantic_title = _normalize_archive_title(
        payload.archive_title,
        fallback_candidates=[payload.summary, payload.input_echo],
    )
    return f"{ARCHIVE_TITLE_PREFIX}{semantic_title}"


def render_feishu_archive_xml(
    payload: SessionArchivePayload,
    *,
    generated_at: datetime,
) -> str:
    """Render a completed session archive into Feishu Docx XML."""

    semantic_title = _normalize_archive_title(
        payload.archive_title,
        fallback_candidates=[payload.summary, payload.input_echo],
    )
    document_title = f"{ARCHIVE_TITLE_PREFIX}{semantic_title}"
    sections = [
        f"<title>{_escape_text(document_title)}</title>",
        f"<h1>{_escape_text(semantic_title)}</h1>",
        "<p>本页为 IdeaOS Archive 自动生成的单次会话归档文档。</p>",
        "<h2>Session Info</h2>",
        _render_session_info(payload, generated_at),
        "<h2>Original Idea</h2>",
        _render_paragraph(payload.original_content),
        "<h2>Input Echo</h2>",
        _render_paragraph(payload.input_echo),
        "<h2>Clarification Record</h2>",
        _render_clarifications(payload.clarifications),
        "<h2>System Assumptions</h2>",
        _render_string_list(payload.assumptions, empty_copy="本次无额外系统假设。"),
        "<hr/>",
        "<h2>Analysis</h2>",
        "<h3>Summary</h3>",
        _render_paragraph(payload.summary),
        "<h3>Feasibility</h3>",
        _render_paragraph(payload.feasibility),
        "<h3>Market</h3>",
        _render_paragraph(payload.market),
        "<h3>Knowledge Gaps</h3>",
        _render_string_list(payload.knowledge_gaps),
        "<h3>Resource Gaps</h3>",
        _render_string_list(payload.resource_gaps),
        "<h3>Team Requirements</h3>",
        _render_string_list(payload.team_requirements),
        "<h3>Similar Projects</h3>",
        _render_string_list(payload.similar_projects),
        "<h3>MVP Roadmap</h3>",
        _render_string_list(payload.mvp_roadmap),
        "<h3>Long-term Roadmap</h3>",
        _render_string_list(payload.long_term_roadmap),
        "<h2>Open Questions</h2>",
        _render_string_list(payload.open_questions, empty_copy="本次无额外后续问题。"),
    ]
    return "\n".join(sections)


def _render_session_info(payload: SessionArchivePayload, generated_at: datetime) -> str:
    """Render the minimal session metadata section."""

    items = [
        f"<li><b>Session ID:</b> {_escape_text(payload.session_id)}</li>",
        f"<li><b>Created At:</b> {_escape_text(_format_datetime(payload.created_at))}</li>",
        f"<li><b>Completed At:</b> {_escape_text(_format_datetime(payload.completed_at))}</li>",
        f"<li><b>Archived At:</b> {_escape_text(_format_datetime(generated_at))}</li>",
    ]
    return f"<ul>{''.join(items)}</ul>"


def _render_clarifications(items: list[SessionClarificationRecord]) -> str:
    """Render clarification records for the archive."""

    if not items:
        return f"<p>{_escape_text('本次会话未进入澄清补充。')}</p>"

    rows = []
    for item in items:
        rows.append(
            "<li>"
            f"<b>问题：</b>{_escape_inline_text(item.question)}<br/>"
            f"<b>回答：</b>{_escape_inline_text(item.answer)}"
            "</li>"
        )
    return f"<ul>{''.join(rows)}</ul>"


def _render_string_list(items: list[str], *, empty_copy: str = FALLBACK_COPY) -> str:
    """Render a plain string list as XML list blocks."""

    if not items:
        return f"<p>{_escape_text(empty_copy)}</p>"

    rows = [f"<li>{_escape_inline_text(item)}</li>" for item in items]
    return f"<ul>{''.join(rows)}</ul>"


def _render_paragraph(text: str) -> str:
    """Render plain text as one XML paragraph with preserved newlines."""

    return f"<p>{_escape_inline_text(text)}</p>"


def _escape_inline_text(text: str) -> str:
    """Escape XML-sensitive text while preserving user-visible newlines."""

    return _escape_text(text).replace("\n", "<br/>")


def _escape_text(text: str) -> str:
    """Escape Feishu XML text content."""

    return escape(text, quote=False)


def _format_datetime(value: datetime) -> str:
    """Format timestamps for human-readable archive metadata."""

    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _normalize_archive_title(title: str, *, fallback_candidates: list[str]) -> str:
    """Normalize a semantic archive title and fall back when needed."""

    candidate = _cleanup_title_candidate(title)
    if candidate:
        return candidate

    for fallback in fallback_candidates:
        normalized = _cleanup_title_candidate(fallback)
        if normalized:
            return normalized

    return "Idea Session"


def _cleanup_title_candidate(value: str) -> str:
    """Clean up a semantic title candidate into a short noun-style phrase."""

    normalized = value.strip()
    if not normalized:
        return ""

    prefixes = (
        "我想做一个",
        "我想做一款",
        "我想做一套",
        "我想做",
        "有没有办法",
        "能不能做一个",
        "能不能做",
        "这是一个",
        "这是面向",
        "该想法是",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
            break

    normalized = normalized.splitlines()[0].strip()
    for separator in ("。", "！", "？", ".", "!", "?", "；", ";", "，", ","):
        if separator in normalized:
            normalized = normalized.split(separator, maxsplit=1)[0].strip()
            break

    normalized = normalized.strip("《》\"'“”‘’：: ")
    if len(normalized) > 28:
        normalized = normalized[:28].rstrip()
    return normalized
