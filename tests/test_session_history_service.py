from datetime import UTC, datetime, timedelta

from ideaos_agent.application.session_history_service import SessionHistoryService
from ideaos_agent.domain.analysis import (
    AnalysisSectionKey,
    IdeaAnalysis,
    RefinementResult,
    SectionUpdate,
)
from ideaos_agent.domain.archive import (
    ArchiveDeleteResult,
    ArchiveProbeResult,
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionRecord,
)
from ideaos_agent.domain.errors import SessionNotFoundError
from ideaos_agent.domain.session import (
    SessionClarificationRecord,
    SessionKind,
    SessionSnapshot,
)


class InMemoryArchiveStore:
    """Simple archive store for history-service unit tests."""

    def __init__(self) -> None:
        self.records: dict[str, SessionRecord] = {}

    def save_session_record(self, record: SessionRecord) -> SessionRecord:
        self.records[record.session_id] = record
        return record

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
    """Simple snapshot store for history-service unit tests."""

    def __init__(self) -> None:
        self.snapshots: dict[str, SessionSnapshot] = {}

    def save_session_snapshot(self, snapshot: SessionSnapshot) -> SessionSnapshot:
        self.snapshots[snapshot.session_id] = snapshot
        return snapshot

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


class InMemoryArchiver:
    """Simple delete-capable archiver for history-service unit tests."""

    def __init__(self) -> None:
        self.deleted_urls: list[str] = []
        self.probe_results: dict[str, bool | None] = {}
        self.probe_failures: dict[str, str] = {}

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        del payload
        raise AssertionError("History service tests should not call archive_session.")

    def delete_archive(self, archive_url: str) -> ArchiveDeleteResult:
        self.deleted_urls.append(archive_url)
        return ArchiveDeleteResult(
            archive_url=archive_url,
            deleted=True,
            archive_error=None,
        )

    def probe_archive(self, archive_url: str) -> ArchiveProbeResult:
        if archive_url in self.probe_failures:
            return ArchiveProbeResult(
                archive_url=archive_url,
                found=None,
                archive_error=self.probe_failures[archive_url],
            )
        return ArchiveProbeResult(
            archive_url=archive_url,
            found=self.probe_results.get(archive_url, True),
            archive_error=None,
        )


def build_service() -> SessionHistoryService:
    archive_store = InMemoryArchiveStore()
    snapshot_store = InMemorySnapshotStore()
    archiver = InMemoryArchiver()

    root_time = datetime.now(UTC) - timedelta(days=1)
    refine_time = root_time + timedelta(hours=1)
    composed_time = refine_time + timedelta(hours=1)

    root_snapshot = SessionSnapshot(
        session_id="sess_root",
        root_session_id="sess_root",
        parent_session_id=None,
        session_kind=SessionKind.ANALYSIS,
        archive_title="独立开发者产品验证工具",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarifications=[],
        assumptions=["假设它以 Web 形式提供。"],
        open_questions=[],
        analysis=IdeaAnalysis(
            summary="这是一个帮助独立开发者验证产品想法的 Web 工具。",
            feasibility="技术可行。",
            market="目标用户明确。",
            knowledge_gaps=["产品验证方法"],
            resource_gaps=["种子用户"],
            team_requirements=["产品负责人"],
            similar_projects=["创业想法分析工具"],
            mvp_roadmap=["定义最小输入输出"],
            long_term_roadmap=["迭代交互体验"],
        ),
        refinement_result=None,
        completed_at=root_time,
        updated_at=root_time,
    )
    root_record = SessionRecord(
        session_id="sess_root",
        root_session_id="sess_root",
        parent_session_id=None,
        session_kind=SessionKind.ANALYSIS,
        original_content=root_snapshot.original_content,
        input_echo=root_snapshot.input_echo,
        clarification_count=0,
        archive_status=ArchiveStatus.SUCCEEDED,
        archive_url="https://feishu.example.com/docx/sess_root",
        completed_at=root_time,
        archived_at=root_time,
        updated_at=root_time,
    )

    refinement_snapshot = SessionSnapshot(
        session_id="sess_refine",
        root_session_id="sess_root",
        parent_session_id="sess_root",
        session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
        archive_title="独立开发者产品验证工具优化",
        original_content=root_snapshot.original_content,
        input_echo="我想进一步收窄目标用户。",
        clarifications=[
            SessionClarificationRecord(
                question="是否继续面向独立开发者？",
                answer="是，先不改变大方向。",
            )
        ],
        assumptions=["假设仍围绕独立开发者。"],
        open_questions=[],
        follow_up_question="我想进一步收窄目标用户。",
        analysis=None,
        refinement_result=RefinementResult(
            question_summary="进一步收窄目标用户",
            refinement_answer="建议先聚焦缺少研究资源的独立开发者。",
            affected_sections=[AnalysisSectionKey.MARKET],
            proposed_section_updates=[
                SectionUpdate(
                    section_key=AnalysisSectionKey.MARKET,
                    change_summary="明确更聚焦的用户画像。",
                    updated_text="目标用户聚焦为缺少研究资源的独立开发者。",
                    updated_items=[],
                )
            ],
            next_actions=["确认后生成新版完整方案。"],
        ),
        completed_at=refine_time,
        updated_at=refine_time,
    )
    refinement_record = SessionRecord(
        session_id="sess_refine",
        root_session_id="sess_root",
        parent_session_id="sess_root",
        session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
        original_content=root_snapshot.original_content,
        input_echo=refinement_snapshot.input_echo,
        clarification_count=1,
        archive_status=ArchiveStatus.NOT_TRIGGERED,
        completed_at=refine_time,
        updated_at=refine_time,
    )

    composed_snapshot = SessionSnapshot(
        session_id="sess_composed",
        root_session_id="sess_root",
        parent_session_id="sess_root",
        session_kind=SessionKind.FULL_PLAN_COMPOSED,
        archive_title="独立开发者产品验证工具优化",
        original_content=root_snapshot.original_content,
        input_echo="我想进一步收窄目标用户。",
        clarifications=refinement_snapshot.clarifications,
        assumptions=refinement_snapshot.assumptions,
        open_questions=[],
        follow_up_question="我想进一步收窄目标用户。",
        analysis=IdeaAnalysis(
            summary="这是一个帮助独立开发者验证产品想法的 Web 工具。",
            feasibility="技术可行。",
            market="目标用户聚焦为缺少研究资源的独立开发者。",
            knowledge_gaps=["产品验证方法"],
            resource_gaps=["种子用户"],
            team_requirements=["产品负责人"],
            similar_projects=["创业想法分析工具"],
            mvp_roadmap=["定义最小输入输出"],
            long_term_roadmap=["迭代交互体验"],
        ),
        refinement_result=refinement_snapshot.refinement_result,
        completed_at=composed_time,
        updated_at=composed_time,
    )
    composed_record = SessionRecord(
        session_id="sess_composed",
        root_session_id="sess_root",
        parent_session_id="sess_root",
        session_kind=SessionKind.FULL_PLAN_COMPOSED,
        original_content=root_snapshot.original_content,
        input_echo=composed_snapshot.input_echo,
        clarification_count=1,
        archive_status=ArchiveStatus.SUCCEEDED,
        archive_url="https://feishu.example.com/docx/sess_composed",
        completed_at=composed_time,
        archived_at=composed_time,
        updated_at=composed_time,
    )

    for snapshot in [root_snapshot, refinement_snapshot, composed_snapshot]:
        snapshot_store.save_session_snapshot(snapshot)
    for record in [root_record, refinement_record, composed_record]:
        archive_store.save_session_record(record)

    return SessionHistoryService(
        follow_up_draft_retention_days=7,
        session_archive_store=archive_store,
        session_snapshot_store=snapshot_store,
        session_archiver=archiver,
    )


def test_list_sessions_returns_recent_history_items() -> None:
    service = build_service()

    response = service.list_sessions(limit=10)

    assert len(response.items) == 2
    assert response.items[0].session_id == "sess_composed"
    assert response.items[0].root_session_id == "sess_root"
    assert response.items[0].can_continue_follow_up is True
    assert response.items[1].session_id == "sess_root"
    assert response.items[1].can_continue_follow_up is True


def test_get_session_detail_returns_children_and_follow_up_flag() -> None:
    service = build_service()

    response = service.get_session_detail("sess_root")

    assert response.session_id == "sess_root"
    assert response.child_session_ids == ["sess_composed"]
    assert response.can_continue_follow_up is True
    assert response.analysis is not None
    assert response.active_follow_up_draft_id == "sess_refine"
    assert response.active_follow_up_draft_question is not None
    assert response.active_follow_up_draft_updated_at is not None


def test_list_threads_groups_sessions_by_root_session_id() -> None:
    service = build_service()

    response = service.list_threads(limit=10)

    assert len(response.items) == 1
    assert response.items[0].root_session_id == "sess_root"
    assert response.items[0].latest_session_id == "sess_composed"
    assert response.items[0].session_count == 2


def test_get_thread_returns_sessions_ordered_by_creation_time() -> None:
    service = build_service()

    response = service.get_thread("sess_root")

    assert response.root_session_id == "sess_root"
    assert [item.session_id for item in response.items] == [
        "sess_root",
        "sess_composed",
    ]


def test_get_thread_raises_when_root_is_missing() -> None:
    service = build_service()

    try:
        service.get_thread("sess_missing")
    except SessionNotFoundError as exc:
        assert "Thread root session not found" in str(exc)
    else:
        raise AssertionError("Expected SessionNotFoundError for missing thread root.")


def test_get_session_detail_prunes_expired_follow_up_draft_cache() -> None:
    service = build_service()
    archive_store = service._session_archive_store
    snapshot_store = service._session_snapshot_store
    assert isinstance(archive_store, InMemoryArchiveStore)
    assert isinstance(snapshot_store, InMemorySnapshotStore)

    expired_time = datetime.now(UTC) - timedelta(days=8)
    draft_snapshot = snapshot_store.get_session_snapshot("sess_refine")
    draft_record = archive_store.get_session_record("sess_refine")
    assert draft_snapshot is not None
    assert draft_record is not None

    snapshot_store.save_session_snapshot(
        draft_snapshot.model_copy(
            update={
                "completed_at": expired_time,
                "updated_at": expired_time,
            }
        )
    )
    archive_store.save_session_record(
        draft_record.model_copy(
            update={
                "completed_at": expired_time,
                "updated_at": expired_time,
            }
        )
    )

    response = service.get_session_detail("sess_root")

    assert response.active_follow_up_draft_id is None
    assert snapshot_store.get_session_snapshot("sess_refine") is None
    assert archive_store.get_session_record("sess_refine") is None


def test_delete_thread_removes_local_records_and_snapshots() -> None:
    service = build_service()

    response = service.delete_thread("sess_root")

    assert response.root_session_id == "sess_root"
    assert response.deleted_session_count == 3
    assert response.deleted_archive_count == 2
    assert response.archive_delete_failures == []

    try:
        service.get_thread("sess_root")
    except SessionNotFoundError:
        pass
    else:
        raise AssertionError("Expected deleted thread to disappear from history service.")


def test_sync_remote_archive_deletions_removes_only_missing_sessions() -> None:
    service = build_service()
    archiver = service._session_archiver
    assert isinstance(archiver, InMemoryArchiver)
    archiver.probe_results["https://feishu.example.com/docx/sess_root"] = True
    archiver.probe_results["https://feishu.example.com/docx/sess_composed"] = True

    response = service.sync_remote_archive_deletions()

    assert response.checked_archive_count == 2
    assert response.removed_session_count == 0
    assert response.removed_session_ids == []
    assert response.probe_failures == []

    thread = service.get_thread("sess_root")
    assert [item.session_id for item in thread.items] == ["sess_root", "sess_composed"]


def test_sync_remote_archive_deletions_keeps_local_history_on_probe_error() -> None:
    service = build_service()
    archiver = service._session_archiver
    assert isinstance(archiver, InMemoryArchiver)
    archiver.probe_failures["https://feishu.example.com/docx/sess_composed"] = (
        "temporary inspect failure"
    )

    response = service.sync_remote_archive_deletions()

    assert response.checked_archive_count == 2
    assert response.removed_session_count == 0
    assert response.removed_session_ids == []
    assert len(response.probe_failures) == 1
    assert response.probe_failures[0].archive_url.endswith("sess_composed")
    assert response.probe_failures[0].error == "temporary inspect failure"

    thread = service.get_thread("sess_root")
    assert [item.session_id for item in thread.items] == [
        "sess_root",
        "sess_composed",
    ]
