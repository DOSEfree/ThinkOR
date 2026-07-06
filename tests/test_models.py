import pytest
from pydantic import ValidationError

from ideaos_agent.domain.analysis import IdeaAnalysis
from ideaos_agent.domain.archive import ArchiveStatus
from ideaos_agent.models import IdeaAnalysisResponse, IdeaInput


def test_idea_input_accepts_content() -> None:
    payload = IdeaInput(content="我想做一个帮助孩子学习的应用。")

    assert payload.content.startswith("我想做")


def test_idea_input_accepts_optional_session_id() -> None:
    payload = IdeaInput(
        session_id="sess_existing",
        content="我想做一个帮助孩子学习的应用。",
    )

    assert payload.session_id == "sess_existing"


def test_idea_input_rejects_blank_session_id() -> None:
    with pytest.raises(ValidationError, match="session_id must not be blank"):
        IdeaInput(
            session_id="   ",
            content="我想做一个帮助孩子学习的应用。",
        )


def test_idea_analysis_response_requires_archive_url_when_succeeded() -> None:
    with pytest.raises(ValidationError, match="archive_url is required when archive succeeds"):
        IdeaAnalysisResponse(
            session_id="sess_existing",
            archive_status=ArchiveStatus.SUCCEEDED,
            archive_url=None,
            archive_title="儿童学习应用",
            input_echo="我想做一个帮助孩子学习的应用。",
            needs_clarification=False,
            assumptions=[],
            open_questions=[],
            analysis=IdeaAnalysis(
                summary="这是一个帮助孩子学习的应用。",
                feasibility="技术上可行。",
                market="目标用户明确。",
                knowledge_gaps=["儿童教育场景"],
                resource_gaps=["种子用户"],
                team_requirements=["产品负责人"],
                similar_projects=["儿童学习应用"],
                mvp_roadmap=["定义最小功能"],
                long_term_roadmap=["扩大内容供给"],
            ),
        )
