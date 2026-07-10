import json
from datetime import UTC, datetime

from ideaos_agent.application.follow_up_session_service import FollowUpSessionService
from ideaos_agent.config import AppSettings
from ideaos_agent.domain.analysis import IdeaAnalysis
from ideaos_agent.domain.archive import (
    ArchiveDeleteResult,
    ArchiveProbeResult,
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

    def list_session_records(
        self,
        *,
        limit: int | None = None,
        root_session_id: str | None = None,
        session_kind: SessionKind | None = None,
    ) -> list[SessionRecord]:
        items = list(self.records.values())
        if root_session_id is not None:
            items = [item for item in items if item.root_session_id == root_session_id]
        if session_kind is not None:
            items = [item for item in items if item.session_kind == session_kind]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        if limit is not None:
            items = items[:limit]
        return items

    def delete_session_records(self, *, root_session_id: str) -> int:
        keys_to_delete = [
            session_id
            for session_id, record in self.records.items()
            if record.root_session_id == root_session_id
        ]
        for session_id in keys_to_delete:
            del self.records[session_id]
        return len(keys_to_delete)

    def delete_session_record(self, session_id: str) -> bool:
        if session_id not in self.records:
            return False
        del self.records[session_id]
        return True


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

    def list_session_snapshots(
        self,
        *,
        limit: int | None = None,
        root_session_id: str | None = None,
        session_kind: SessionKind | None = None,
    ) -> list[SessionSnapshot]:
        items = list(self.snapshots.values())
        if root_session_id is not None:
            items = [item for item in items if item.root_session_id == root_session_id]
        if session_kind is not None:
            items = [item for item in items if item.session_kind == session_kind]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        if limit is not None:
            items = items[:limit]
        return items

    def delete_session_snapshots(self, *, root_session_id: str) -> int:
        keys_to_delete = [
            session_id
            for session_id, snapshot in self.snapshots.items()
            if snapshot.root_session_id == root_session_id
        ]
        for session_id in keys_to_delete:
            del self.snapshots[session_id]
        return len(keys_to_delete)

    def delete_session_snapshot(self, session_id: str) -> bool:
        if session_id not in self.snapshots:
            return False
        del self.snapshots[session_id]
        return True


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

    def delete_archive(self, archive_url: str) -> ArchiveDeleteResult:
        return ArchiveDeleteResult(
            archive_url=archive_url,
            deleted=True,
            archive_error=None,
        )

    def probe_archive(self, archive_url: str) -> ArchiveProbeResult:
        return ArchiveProbeResult(
            archive_url=archive_url,
            found=True,
            archive_error=None,
        )


def seed_parent(snapshot_store: InMemorySnapshotStore, archive_store: InMemoryArchiveStore) -> None:
    """Seed one completed root analysis session as the follow-up parent."""

    now = datetime.now(UTC)
    snapshot_store.save_session_snapshot(
        SessionSnapshot(
            session_id="sess_root",
            root_session_id="sess_root",
            parent_session_id=None,
            session_kind=SessionKind.ANALYSIS,
            formal_version_number=1,
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
            root_session_id="sess_root",
            parent_session_id=None,
            session_kind=SessionKind.ANALYSIS,
            formal_version_number=1,
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
    assert result.root_session_id == "sess_root"
    assert result.parent_session_id == "sess_root"
    assert result.formal_version_number is None
    assert result.parent_formal_version_number == 1
    assert result.archive_status == ArchiveStatus.NOT_TRIGGERED
    assert result.archive_url is None
    persisted_record = archive_store.get_session_record(result.session_id)
    assert persisted_record is not None
    assert persisted_record.root_session_id == "sess_root"
    assert persisted_record.formal_version_number is None
    assert persisted_record.session_kind == SessionKind.FOLLOW_UP_REFINEMENT
    assert persisted_record.completed_at is not None
    persisted_snapshot = snapshot_store.get_session_snapshot(result.session_id)
    assert persisted_snapshot is not None
    assert persisted_snapshot.root_session_id == "sess_root"
    assert persisted_snapshot.formal_version_number is None
    assert persisted_snapshot.refinement_result is not None
    assert len(archiver.calls) == 0


def test_follow_up_compose_full_plan_applies_section_updates() -> None:
    service, archive_store, snapshot_store, archiver = build_service(
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
    assert composed.root_session_id == "sess_root"
    assert composed.parent_session_id == "sess_root"
    assert composed.formal_version_number == 2
    assert composed.parent_formal_version_number == 1
    assert composed.session_kind == SessionKind.FULL_PLAN_COMPOSED
    assert composed.analysis is not None
    assert composed.analysis.market == "目标用户聚焦为缺少研究资源的独立开发者。"
    persisted_record = archive_store.get_session_record(composed.session_id)
    assert persisted_record is not None
    assert persisted_record.root_session_id == "sess_root"
    assert persisted_record.formal_version_number == 2
    assert persisted_record.session_kind == SessionKind.FULL_PLAN_COMPOSED
    assert persisted_record.parent_session_id == "sess_root"
    persisted_snapshot = snapshot_store.get_session_snapshot(composed.session_id)
    assert persisted_snapshot is not None
    assert persisted_snapshot.root_session_id == "sess_root"
    assert persisted_snapshot.formal_version_number == 2
    assert persisted_snapshot.analysis is not None
    assert persisted_snapshot.parent_session_id == "sess_root"
    assert snapshot_store.get_session_snapshot(refine_result.session_id) is None
    assert archive_store.get_session_record(refine_result.session_id) is None
    assert len(archiver.calls) == 1
    assert archiver.calls[0].root_session_id == "sess_root"
    assert archiver.calls[0].root_archive_url == "https://feishu.example.com/docx/sess_root"
    assert archiver.calls[0].parent_session_id == "sess_root"
    assert archiver.calls[0].parent_archive_url == "https://feishu.example.com/docx/sess_root"


def test_follow_up_compose_from_old_version_keeps_global_version() -> None:
    service, archive_store, snapshot_store, _archiver = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具优化版 A",
                "input_echo": "我想先把目标用户收窄到缺少研究资源的独立开发者。",
                "needs_clarification": False,
                "assumptions": ["仍然围绕独立开发者。"],
                "open_questions": [],
                "refinement_result": {
                    "question_summary": "先收窄目标用户",
                    "refinement_answer": "建议先聚焦缺少研究资源的独立开发者。",
                    "affected_sections": ["market"],
                    "proposed_section_updates": [
                        {
                            "section_key": "market",
                            "change_summary": "先收窄到研究资源不足的独立开发者。",
                            "updated_text": "目标用户聚焦为缺少研究资源的独立开发者。",
                            "updated_items": [],
                        }
                    ],
                    "next_actions": ["确认后生成新版本完整方案。"],
                },
            },
            {
                "archive_title": "独立开发者产品验证工具优化版 B",
                "input_echo": "我想改从获客渠道切入，而不是沿用上一条分支。",
                "needs_clarification": False,
                "assumptions": ["仍然围绕独立开发者。"],
                "open_questions": [],
                "refinement_result": {
                    "question_summary": "从 ROOT 改走获客渠道分支",
                    "refinement_answer": "建议优先补获客与分发路径。",
                    "affected_sections": ["mvp_roadmap"],
                    "proposed_section_updates": [
                        {
                            "section_key": "mvp_roadmap",
                            "change_summary": "新增获客验证步骤。",
                            "updated_text": None,
                            "updated_items": ["先验证 1 个可重复获客渠道。"],
                        }
                    ],
                    "next_actions": ["确认后生成新版本完整方案。"],
                },
            },
        ]
    )

    first_refine = service.refine(
        FollowUpInput(
            parent_session_id="sess_root",
            question="我想先把目标用户收窄到缺少研究资源的独立开发者。",
            clarifications=[],
        )
    )
    first_composed = service.compose_full_plan(
        ComposeFullPlanInput(parent_session_id=first_refine.session_id)
    )

    second_refine = service.refine(
        FollowUpInput(
            parent_session_id="sess_root",
            question="我想改从获客渠道切入，而不是沿用上一条分支。",
            clarifications=[],
        )
    )
    second_composed = service.compose_full_plan(
        ComposeFullPlanInput(parent_session_id=second_refine.session_id)
    )

    assert first_composed.formal_version_number == 2
    assert first_composed.parent_formal_version_number == 1
    assert second_refine.parent_formal_version_number == 1
    assert second_composed.formal_version_number == 3
    assert second_composed.parent_formal_version_number == 1

    persisted_first = snapshot_store.get_session_snapshot(first_composed.session_id)
    persisted_second = snapshot_store.get_session_snapshot(second_composed.session_id)
    assert persisted_first is not None
    assert persisted_second is not None
    assert persisted_first.parent_session_id == "sess_root"
    assert persisted_second.parent_session_id == "sess_root"
    assert persisted_first.formal_version_number == 2
    assert persisted_second.formal_version_number == 3

    root_record = archive_store.get_session_record("sess_root")
    assert root_record is not None
    assert root_record.formal_version_number == 1
