from datetime import UTC, datetime

from ideaos_agent.domain.archive import SessionArchivePayload, SessionClarificationRecord
from ideaos_agent.infrastructure.archive.feishu_doc_renderer import (
    build_feishu_archive_title,
    render_feishu_archive_xml,
)


def build_payload() -> SessionArchivePayload:
    return SessionArchivePayload(
        session_id="sess_archive",
        archive_title="独立开发者产品验证工具",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarifications=[
            SessionClarificationRecord(
                question="你最想验证什么？",
                answer="先判断想法值不值得继续做。",
            )
        ],
        assumptions=["假设它以 Web 形式提供。"],
        open_questions=["是否需要在首版支持报告分享？"],
        summary="这是一个帮助独立开发者验证产品想法的 Web 工具。",
        feasibility="技术可行。",
        market="目标用户较明确。",
        knowledge_gaps=["产品验证方法"],
        resource_gaps=["种子用户"],
        team_requirements=["产品负责人"],
        similar_projects=["创业想法分析工具"],
        mvp_roadmap=["定义最小输入输出"],
        long_term_roadmap=["迭代交互体验"],
        created_at=datetime(2026, 7, 5, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 5, 10, 5, tzinfo=UTC),
    )


def test_build_feishu_archive_title_keeps_fixed_prefix() -> None:
    payload = build_payload()

    title = build_feishu_archive_title(payload)

    assert title == "IdeaOS Archive | 独立开发者产品验证工具"


def test_render_feishu_archive_xml_contains_core_sections() -> None:
    payload = build_payload()

    xml = render_feishu_archive_xml(
        payload,
        generated_at=datetime(2026, 7, 5, 10, 6, tzinfo=UTC),
    )

    assert "<title>IdeaOS Archive | 独立开发者产品验证工具</title>" in xml
    assert "<h1>独立开发者产品验证工具</h1>" in xml
    assert "<h2>Original Idea</h2>" in xml
    assert "<h2>Clarification Record</h2>" in xml
    assert "<h2>Analysis</h2>" in xml
    assert "<h3>Summary</h3>" in xml
    assert "先判断想法值不值得继续做。" in xml
