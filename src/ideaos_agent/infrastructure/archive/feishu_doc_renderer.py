"""Render session archives into Feishu Docx XML content."""

from datetime import datetime
from html import escape

from ideaos_agent.domain.archive import SessionArchivePayload
from ideaos_agent.domain.session import SessionClarificationRecord, SessionKind

ARCHIVE_TITLE_PREFIX = "IdeaOS Archive | "
FALLBACK_COPY = "暂无补充内容。"


def build_feishu_archive_title(payload: SessionArchivePayload) -> str:
    """Build the final human-facing Feishu document title."""

    fallback_candidates = [payload.input_echo]
    if payload.analysis is not None:
        fallback_candidates.insert(0, payload.analysis.summary)
    if payload.refinement_result is not None:
        fallback_candidates.insert(0, payload.refinement_result.question_summary)

    semantic_title = _normalize_archive_title(
        payload.archive_title,
        fallback_candidates=fallback_candidates,
    )
    return f"{ARCHIVE_TITLE_PREFIX}{semantic_title}"


def render_feishu_archive_xml(
    payload: SessionArchivePayload,
    *,
    generated_at: datetime,
) -> str:
    """Render one completed session archive into Feishu Docx XML."""

    semantic_title = _normalize_archive_title(
        payload.archive_title,
        fallback_candidates=_build_fallback_candidates(payload),
    )
    document_title = f"{ARCHIVE_TITLE_PREFIX}{semantic_title}"
    sections = [
        f"<title>{_escape_text(document_title)}</title>",
        f"<h1>{_escape_text(semantic_title)}</h1>",
        f"<p>{_escape_text(_session_intro_copy(payload.session_kind))}</p>",
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
    ]

    if payload.follow_up_question is not None:
        sections.extend(
            [
                "<h2>Follow-up Question</h2>",
                _render_paragraph(payload.follow_up_question),
            ]
        )

    if payload.parent_session_id is not None:
        sections.extend(
            [
                "<h2>Parent Session</h2>",
                _render_parent_session(payload),
            ]
        )

    sections.append("<hr/>")

    if payload.refinement_result is not None:
        sections.extend(
            [
                "<h2>Refinement Result</h2>",
                "<h3>Question Summary</h3>",
                _render_paragraph(payload.refinement_result.question_summary),
                "<h3>Refinement Answer</h3>",
                _render_paragraph(payload.refinement_result.refinement_answer),
                "<h3>Affected Sections</h3>",
                _render_string_list(
                    [item.value for item in payload.refinement_result.affected_sections]
                ),
                "<h3>Proposed Section Updates</h3>",
                _render_section_updates(payload),
                "<h3>Next Actions</h3>",
                _render_string_list(
                    payload.refinement_result.next_actions,
                    empty_copy="本次无额外后续动作。",
                ),
            ]
        )

    if payload.analysis is not None:
        sections.extend(
            [
                "<h2>Analysis</h2>",
                "<h3>Summary</h3>",
                _render_paragraph(payload.analysis.summary),
                "<h3>Feasibility</h3>",
                _render_paragraph(payload.analysis.feasibility),
                "<h3>Market</h3>",
                _render_paragraph(payload.analysis.market),
                "<h3>Knowledge Gaps</h3>",
                _render_string_list(payload.analysis.knowledge_gaps),
                "<h3>Resource Gaps</h3>",
                _render_string_list(payload.analysis.resource_gaps),
                "<h3>Team Requirements</h3>",
                _render_string_list(payload.analysis.team_requirements),
                "<h3>Similar Projects</h3>",
                _render_string_list(payload.analysis.similar_projects),
                "<h3>MVP Roadmap</h3>",
                _render_string_list(payload.analysis.mvp_roadmap),
                "<h3>Long-term Roadmap</h3>",
                _render_string_list(payload.analysis.long_term_roadmap),
            ]
        )

    sections.extend(
        [
            "<h2>Open Questions</h2>",
            _render_string_list(payload.open_questions, empty_copy="本次无额外后续问题。"),
        ]
    )
    return "\n".join(sections)


def _render_session_info(payload: SessionArchivePayload, generated_at: datetime) -> str:
    """Render minimal session metadata."""

    items = [
        f"<li><b>Session ID:</b> {_escape_text(payload.session_id)}</li>",
        f"<li><b>Session Kind:</b> {_escape_text(payload.session_kind.value)}</li>",
        f"<li><b>Created At:</b> {_escape_text(_format_datetime(payload.created_at))}</li>",
        f"<li><b>Completed At:</b> {_escape_text(_format_datetime(payload.completed_at))}</li>",
        f"<li><b>Archived At:</b> {_escape_text(_format_datetime(generated_at))}</li>",
    ]
    return f"<ul>{''.join(items)}</ul>"


def _render_parent_session(payload: SessionArchivePayload) -> str:
    """Render parent session metadata for follow-up/composed sessions."""

    items = [f"<li><b>Parent Session ID:</b> {_escape_text(payload.parent_session_id or '')}</li>"]
    if payload.parent_archive_url:
        items.append(
            "<li><b>Parent Archive URL:</b> "
            f"{_escape_text(payload.parent_archive_url)}</li>"
        )
    return f"<ul>{''.join(items)}</ul>"


def _render_clarifications(items: list[SessionClarificationRecord]) -> str:
    """Render clarification records."""

    if not items:
        return "<p>本次会话未进入澄清补充。</p>"

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


def _render_section_updates(payload: SessionArchivePayload) -> str:
    """Render refinement section updates when available."""

    if payload.refinement_result is None:
        return f"<p>{_escape_text(FALLBACK_COPY)}</p>"

    rows = []
    for item in payload.refinement_result.proposed_section_updates:
        replacement = item.updated_text
        if replacement is None:
            replacement = "\n".join(f"- {row}" for row in item.updated_items)
        rows.append(
            "<li>"
            f"<b>{_escape_text(item.section_key.value)}</b><br/>"
            f"{_escape_inline_text(item.change_summary)}<br/>"
            f"<i>{_escape_inline_text(replacement)}</i>"
            "</li>"
        )
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
        "我想做一次",
        "我想做",
        "有没有办法",
        "能不能做一个",
        "能不能做",
        "这是一个",
        "该想法是",
        "进一步完善",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
            break

    normalized = normalized.splitlines()[0].strip()
    for separator in ("。", "，", ".", "!", "?", "；", ";", ":"):
        if separator in normalized:
            normalized = normalized.split(separator, maxsplit=1)[0].strip()
            break

    normalized = normalized.strip("“”\"'：: ")
    if len(normalized) > 28:
        normalized = normalized[:28].rstrip()
    return normalized


def _session_intro_copy(session_kind: SessionKind) -> str:
    """Return the human-facing intro copy for one archive session kind."""

    if session_kind == SessionKind.ANALYSIS:
        return "本页为 IdeaOS Archive 自动生成的单次正式分析归档文档。"
    if session_kind == SessionKind.FOLLOW_UP_REFINEMENT:
        return "本页为 IdeaOS Archive 自动生成的 follow-up 局部完善归档文档。"
    return "本页为 IdeaOS Archive 自动生成的新版完整方案归档文档。"


def _build_fallback_candidates(payload: SessionArchivePayload) -> list[str]:
    """Build ordered fallback title candidates for one archive payload."""

    candidates = [payload.input_echo]
    if payload.refinement_result is not None:
        candidates.insert(0, payload.refinement_result.question_summary)
    if payload.analysis is not None:
        candidates.insert(0, payload.analysis.summary)
    return candidates
