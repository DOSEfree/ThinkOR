import json
from datetime import UTC, datetime

from ideaos_agent.application.idea_analysis_service import IdeaAnalysisService
from ideaos_agent.application.idea_analysis_session_service import IdeaAnalysisSessionService
from ideaos_agent.config import AppSettings
from ideaos_agent.domain.archive import (
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionRecord,
)
from ideaos_agent.domain.session import SessionSnapshot
from ideaos_agent.infrastructure.llm.client import LlmClient
from ideaos_agent.models import IdeaInput
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder


class MockLlmClient(LlmClient):
    """Configurable mock client that returns queued JSON payloads."""

    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = [json.dumps(item, ensure_ascii=False) for item in responses]

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt
        del user_prompt
        return self._responses.pop(0)


class InMemorySessionArchiveStore:
    """Simple in-memory index store used for session-service unit tests."""

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


class InMemorySessionSnapshotStore:
    """Simple in-memory snapshot store used for session-service unit tests."""

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
    """Simple archiver used for session-service unit tests."""

    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[SessionArchivePayload] = []

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        self.calls.append(payload)
        archived_at = datetime.now(UTC)
        if self.should_fail:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error="飞书归档失败。",
                archived_at=archived_at,
            )
        return ArchiveResult(
            archive_status=ArchiveStatus.SUCCEEDED,
            archive_url=f"https://feishu.example.com/docx/{payload.session_id}",
            archive_error=None,
            archived_at=archived_at,
        )


def build_session_service(
    responses: list[dict[str, object]],
    *,
    should_fail_archive: bool = False,
) -> tuple[
    IdeaAnalysisSessionService,
    InMemorySessionArchiveStore,
    InMemorySessionSnapshotStore,
    FakeSessionArchiver,
]:
    analysis_service = IdeaAnalysisService(
        settings=AppSettings(
            llm_api_key="fake-key",
            use_fake_llm=False,
            max_input_chars=4000,
        ),
        llm_client=MockLlmClient(responses),
        prompt_builder=IdeaAnalysisPromptBuilder(),
    )
    archive_store = InMemorySessionArchiveStore()
    snapshot_store = InMemorySessionSnapshotStore()
    archiver = FakeSessionArchiver(should_fail=should_fail_archive)
    return (
        IdeaAnalysisSessionService(
            analysis_service=analysis_service,
            session_archive_store=archive_store,
            session_snapshot_store=snapshot_store,
            session_archiver=archiver,
        ),
        archive_store,
        snapshot_store,
        archiver,
    )


def test_session_service_generates_session_id_for_first_request() -> None:
    service, archive_store, snapshot_store, archiver = build_session_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": "我想做一个帮助独立开发者验证产品想法的工具。",
                "needs_clarification": True,
                "assumptions": ["假设目标用户是独立开发者。"],
                "open_questions": [
                    "你最想验证什么？",
                    "希望输出建议还是执行计划？",
                ],
                "analysis": None,
            }
        ]
    )

    result = service.analyze(IdeaInput(content="我想做一个帮助独立开发者验证产品想法的工具。"))

    assert result.session_id.startswith("sess_")
    assert result.archive_status == ArchiveStatus.NOT_TRIGGERED
    assert result.archive_url is None
    persisted_record = archive_store.get_session_record(result.session_id)
    assert persisted_record is not None
    assert persisted_record.archive_status == ArchiveStatus.NOT_TRIGGERED
    assert persisted_record.completed_at is None
    assert snapshot_store.get_session_snapshot(result.session_id) is None
    assert archiver.calls == []


def test_session_service_reuses_existing_session_id_for_completed_analysis() -> None:
    service, archive_store, snapshot_store, archiver = build_session_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": "我想做一个帮助独立开发者验证产品想法的工具。",
                "needs_clarification": False,
                "assumptions": ["假设它以 Web 形式提供。"],
                "open_questions": [],
                "analysis": {
                    "summary": "这是一个帮助独立开发者验证产品想法的 Web 工具。",
                    "feasibility": "技术可行。",
                    "market": "目标用户较明确。",
                    "knowledge_gaps": ["产品验证方法"],
                    "resource_gaps": ["种子用户"],
                    "team_requirements": ["产品负责人"],
                    "similar_projects": ["创业想法分析工具"],
                    "mvp_roadmap": ["定义最小输入输出"],
                    "long_term_roadmap": ["迭代交互体验"],
                },
            }
        ]
    )

    result = service.analyze(
        IdeaInput(
            session_id="sess_existing",
            content="我想做一个帮助独立开发者验证产品想法的工具。",
        )
    )

    assert result.session_id == "sess_existing"
    assert result.archive_status == ArchiveStatus.SUCCEEDED
    assert result.archive_url == "https://feishu.example.com/docx/sess_existing"
    persisted_record = archive_store.get_session_record("sess_existing")
    assert persisted_record is not None
    assert persisted_record.archive_status == ArchiveStatus.SUCCEEDED
    assert persisted_record.completed_at is not None
    assert persisted_record.archived_at is not None
    assert persisted_record.completed_at.tzinfo == UTC
    assert persisted_record.completed_at <= datetime.now(UTC)
    assert persisted_record.archive_url == "https://feishu.example.com/docx/sess_existing"
    persisted_snapshot = snapshot_store.get_session_snapshot("sess_existing")
    assert persisted_snapshot is not None
    assert persisted_snapshot.analysis is not None
    assert len(archiver.calls) == 1
    assert archiver.calls[0].archive_title == "独立开发者产品验证工具"


def test_session_service_marks_archive_failed_without_blocking_response() -> None:
    service, archive_store, snapshot_store, _archiver = build_session_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": "我想做一个帮助独立开发者验证产品想法的工具。",
                "needs_clarification": False,
                "assumptions": ["假设它以 Web 形式提供。"],
                "open_questions": [],
                "analysis": {
                    "summary": "这是一个帮助独立开发者验证产品想法的 Web 工具。",
                    "feasibility": "技术可行。",
                    "market": "目标用户较明确。",
                    "knowledge_gaps": ["产品验证方法"],
                    "resource_gaps": ["种子用户"],
                    "team_requirements": ["产品负责人"],
                    "similar_projects": ["创业想法分析工具"],
                    "mvp_roadmap": ["定义最小输入输出"],
                    "long_term_roadmap": ["迭代交互体验"],
                },
            }
        ],
        should_fail_archive=True,
    )

    result = service.analyze(
        IdeaInput(
            session_id="sess_failed",
            content="我想做一个帮助独立开发者验证产品想法的工具。",
        )
    )

    assert result.session_id == "sess_failed"
    assert result.archive_status == ArchiveStatus.FAILED
    assert result.archive_url is None
    assert result.analysis is not None
    persisted_record = archive_store.get_session_record("sess_failed")
    assert persisted_record is not None
    assert persisted_record.archive_status == ArchiveStatus.FAILED
    assert persisted_record.archive_error == "飞书归档失败。"
    assert persisted_record.archived_at is not None
    persisted_snapshot = snapshot_store.get_session_snapshot("sess_failed")
    assert persisted_snapshot is not None
    assert persisted_snapshot.archived_at is not None
