import json
from datetime import UTC, datetime

from ideaos_agent.application.follow_up_session_service import FollowUpSessionService
from ideaos_agent.config import AppSettings
from ideaos_agent.domain.analysis import IdeaAnalysis
from ideaos_agent.domain.archive import (
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionRecord,
)
from ideaos_agent.domain.session import SessionKind, SessionSnapshot
from ideaos_agent.infrastructure.llm.client import LlmClient
from ideaos_agent.models import ComposeFullPlanInput, FollowUpInput
from ideaos_agent.prompts.follow_up import FollowUpPromptBuilder


class MockLlmClient(LlmClient):
    """Configurable mock client for follow-up service tests."""

    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = [json.dumps(item, ensure_ascii=False) for item in responses]

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt
        del user_prompt
        return self._responses.pop(0)


class InMemoryArchiveStore:
    """Combined archive index store for follow-up tests."""

    def __init__(self) -> None:
        self.records: dict[str, SessionRecord] = {}

    def save_session_record(self, record: SessionRecord) -> SessionRecord:
        existing = self.records.get(record.session_id)
        persisted = record
        if existing is not None:
            persisted = record.model_copy(update={"created_at": existing.created_at})
        self.records[persisted.session_id] = persisted
        return persisted

    def get_session_record(self, session_id: str) -> SessionRecord | None:
        return self.records.get(session_id)


class InMemorySnapshotStore:
    """Combined snapshot store for follow-up tests."""

    def __init__(self) -> None:
        self.snapshots: dict[str, SessionSnapshot] = {}

    def save_session_snapshot(self, snapshot: SessionSnapshot) -> SessionSnapshot:
        existing = self.snapshots.get(snapshot.session_id)
        persisted = snapshot
        if existing is not None:
            persisted = snapshot.model_copy(update={"created_at": existing.created_at})
        self.snapshots[persisted.session_id] = persisted
        return persisted

    def get_session_snapshot(self, session_id: str) -> SessionSnapshot | None:
        return self.snapshots.get(session_id)


class FakeSessionArchiver:
    """Simple archiver used for follow-up service unit tests."""

    def __init__(self) -> None:
        self.calls: list[SessionArchivePayload] = []

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        self.calls.append(payload)
        return ArchiveResult(
            archive_status=ArchiveStatus.SUCCEEDED,
            archive_url=f"https://feishu.example.com/docx/{payload.session_id}",
            archive_error=None,
            archived_at=payload.completed_at,
        )


def seed_parent(snapshot_store: InMemorySnapshotStore, archive_store: InMemoryArchiveStore) -> None:
    """Seed one completed root analysis session as the follow-up parent."""

    now = datetime.now(UTC)
    snapshot_store.save_session_snapshot(
        SessionSnapshot(
            session_id="sess_root",
            parent_session_id=None,
            session_kind=SessionKind.ANALYSIS,
            archive_title="独立开发者产品验证工具",
            original_content="我想做一个帮助独立开发者验证产品想法的工具。",
            input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
            clarifications=[],
            assumptions=["假设它以 Web 形式提供。"],
            open_questions=["是否需要在首版支持报告分享？"],
            analysis=IdeaAnalysis(
                summary="这是一个帮助独立开发者验证产品想法的 Web 工具。",
                feasibility="技术可行。",
                market="目标用户较明确。",
                knowledge_gaps=["产品验证方法"],
                resource_gaps=["种子用户"],
                team_requirements=["产品负责人"],
                similar_projects=["创业想法分析工具"],
                mvp_roadmap=["定义最小输入输出"],
                long_term_roadmap=["迭代交互体验"],
            ),
            refinement_result=None,
            completed_at=now,
        )
    )
    archive_store.save_session_record(
        SessionRecord(
            session_id="sess_root",
            parent_session_id=None,
            session_kind=SessionKind.ANALYSIS,
            original_content="我想做一个帮助独立开发者验证产品想法的工具。",
            input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
            clarification_count=0,
            archive_status=ArchiveStatus.SUCCEEDED,
            archive_url="https://feishu.example.com/docx/sess_root",
            archived_at=now,
            completed_at=now,
        )
    )


def build_service(
    responses: list[dict[str, object]],
) -> tuple[
    FollowUpSessionService,
    InMemoryArchiveStore,
    InMemorySnapshotStore,
    FakeSessionArchiver,
]:
    archive_store = InMemoryArchiveStore()
    snapshot_store = InMemorySnapshotStore()
    seed_parent(snapshot_store, archive_store)
    archiver = FakeSessionArchiver()

    service = FollowUpSessionService(
        settings=AppSettings(llm_api_key="fake-key", use_fake_llm=False, max_input_chars=4000),
        llm_client=MockLlmClient(responses),
        prompt_builder=FollowUpPromptBuilder(),
        session_archive_store=archive_store,
        session_snapshot_store=snapshot_store,
        session_archiver=archiver,
    )
    return service, archive_store, snapshot_store, archiver


def test_follow_up_refine_creates_new_session_and_snapshot() -> None:
    service, archive_store, snapshot_store, archiver = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具优化",
                "input_echo": "我想进一步收窄目标用户。",
                "needs_clarification": False,
                "assumptions": ["假设本次仍围绕独立开发者，不更换主方向。"],
                "open_questions": ["下一轮可以继续打磨报告模板。"],
                "refinement_result": {
                    "question_summary": "进一步收窄目标用户",
                    "refinement_answer": "建议聚焦缺少研究资源的独立开发者。",
                    "affected_sections": ["market"],
                    "proposed_section_updates": [
                        {
                            "section_key": "market",
                            "change_summary": "明确目标用户聚焦。",
                            "updated_text": "目标用户聚焦为缺少研究资源的独立开发者。",
                            "updated_items": [],
                        }
                    ],
                    "next_actions": ["确认后生成新版完整方案。"],
                },
            }
        ]
    )

    result = service.refine(
        FollowUpInput(
            parent_session_id="sess_root",
            question="我想进一步收窄目标用户。",
            clarifications=[],
        )
    )

    assert result.session_id.startswith("sess_")
    assert result.parent_session_id == "sess_root"
    assert result.archive_status == ArchiveStatus.SUCCEEDED
    persisted_record = archive_store.get_session_record(result.session_id)
    assert persisted_record is not None
    assert persisted_record.session_kind == SessionKind.FOLLOW_UP_REFINEMENT
    persisted_snapshot = snapshot_store.get_session_snapshot(result.session_id)
    assert persisted_snapshot is not None
    assert persisted_snapshot.refinement_result is not None
    assert len(archiver.calls) == 1


def test_follow_up_compose_full_plan_applies_section_updates() -> None:
    service, archive_store, snapshot_store, _archiver = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具优化",
                "input_echo": "我想进一步收窄目标用户。",
                "needs_clarification": False,
                "assumptions": ["假设本次仍围绕独立开发者，不更换主方向。"],
                "open_questions": [],
                "refinement_result": {
                    "question_summary": "进一步收窄目标用户",
                    "refinement_answer": "建议聚焦缺少研究资源的独立开发者。",
                    "affected_sections": ["market"],
                    "proposed_section_updates": [
                        {
                            "section_key": "market",
                            "change_summary": "明确目标用户聚焦。",
                            "updated_text": "目标用户聚焦为缺少研究资源的独立开发者。",
                            "updated_items": [],
                        }
                    ],
                    "next_actions": ["确认后生成新版完整方案。"],
                },
            }
        ]
    )

    refine_result = service.refine(
        FollowUpInput(
            parent_session_id="sess_root",
            question="我想进一步收窄目标用户。",
            clarifications=[],
        )
    )

    composed = service.compose_full_plan(
        ComposeFullPlanInput(parent_session_id=refine_result.session_id)
    )

    assert composed.session_id.startswith("sess_")
    assert composed.parent_session_id == refine_result.session_id
    assert composed.session_kind == SessionKind.FULL_PLAN_COMPOSED
    assert composed.analysis is not None
    assert composed.analysis.market == "目标用户聚焦为缺少研究资源的独立开发者。"
    persisted_record = archive_store.get_session_record(composed.session_id)
    assert persisted_record is not None
    assert persisted_record.session_kind == SessionKind.FULL_PLAN_COMPOSED
    persisted_snapshot = snapshot_store.get_session_snapshot(composed.session_id)
    assert persisted_snapshot is not None
    assert persisted_snapshot.analysis is not None
