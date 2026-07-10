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
from ideaos_agent.domain.errors import SessionNotFoundError, SessionStateError
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
        formal_version_number=1,
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
        formal_version_number=1,
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
        formal_version_number=2,
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
        formal_version_number=2,
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
    assert response.items[0].formal_version_number == 2
    assert response.items[0].parent_formal_version_number == 1
    assert response.items[0].can_delete_leaf is True
    assert response.items[0].delete_block_reason is None
    assert response.items[0].can_continue_follow_up is True
    assert response.items[1].session_id == "sess_root"
    assert response.items[1].formal_version_number == 1
    assert response.items[1].parent_formal_version_number is None
    assert response.items[1].can_delete_leaf is False
    assert response.items[1].delete_block_reason == "ROOT version must be deleted at thread level."
    assert response.items[1].can_continue_follow_up is True


def test_get_session_detail_returns_children_and_follow_up_flag() -> None:
    service = build_service()

    response = service.get_session_detail("sess_root")

    assert response.session_id == "sess_root"
    assert response.formal_version_number == 1
    assert response.parent_formal_version_number is None
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
    assert response.items[0].latest_formal_version_number == 2
    assert response.items[0].session_count == 2


def test_list_threads_filters_by_local_history_search_query() -> None:
    service = build_service()
    archive_store = service._session_archive_store
    snapshot_store = service._session_snapshot_store
    assert isinstance(archive_store, InMemoryArchiveStore)
    assert isinstance(snapshot_store, InMemorySnapshotStore)

    second_time = datetime.now(UTC) - timedelta(hours=4)
    second_snapshot = SessionSnapshot(
        session_id="sess_other_root",
        root_session_id="sess_other_root",
        parent_session_id=None,
        session_kind=SessionKind.ANALYSIS,
        archive_title="AI 面试助手",
        original_content="我想做一个帮助候选人准备 AI 面试的问题整理工具。",
        input_echo="我想做一个帮助候选人准备 AI 面试的问题整理工具。",
        clarifications=[],
        assumptions=["先以 Web 端验证。"],
        open_questions=[],
        analysis=IdeaAnalysis(
            summary="这是一个帮助候选人准备 AI 面试的整理工具。",
            feasibility="可以先做轻量版本。",
            market="面向求职用户。",
            knowledge_gaps=["渠道验证"],
            resource_gaps=["种子用户"],
            team_requirements=["独立开发者"],
            similar_projects=["面试题库"],
            mvp_roadmap=["整理题目"],
            long_term_roadmap=["补面试反馈"],
        ),
        refinement_result=None,
        completed_at=second_time,
        updated_at=second_time,
    )
    second_record = SessionRecord(
        session_id="sess_other_root",
        root_session_id="sess_other_root",
        parent_session_id=None,
        session_kind=SessionKind.ANALYSIS,
        original_content=second_snapshot.original_content,
        input_echo=second_snapshot.input_echo,
        clarification_count=0,
        archive_status=ArchiveStatus.SUCCEEDED,
        archive_url="https://feishu.example.com/docx/sess_other_root",
        completed_at=second_time,
        archived_at=second_time,
        updated_at=second_time,
    )
    snapshot_store.save_session_snapshot(second_snapshot)
    archive_store.save_session_record(second_record)

    response = service.list_threads(limit=10, query="独立开发者 验证")

    assert [item.root_session_id for item in response.items] == ["sess_root"]


def test_list_threads_search_excludes_follow_up_draft_only_matches() -> None:
    service = build_service()
    archive_store = service._session_archive_store
    snapshot_store = service._session_snapshot_store
    assert isinstance(archive_store, InMemoryArchiveStore)
    assert isinstance(snapshot_store, InMemorySnapshotStore)

    root_time = datetime.now(UTC) - timedelta(hours=2)
    draft_time = root_time + timedelta(minutes=30)
    root_snapshot = SessionSnapshot(
        session_id="sess_search_root",
        root_session_id="sess_search_root",
        parent_session_id=None,
        session_kind=SessionKind.ANALYSIS,
        archive_title="本地搜索测试根节点",
        original_content="我想做一个普通的知识整理工具。",
        input_echo="我想做一个普通的知识整理工具。",
        clarifications=[],
        assumptions=["先做最小版本。"],
        open_questions=[],
        analysis=IdeaAnalysis(
            summary="这是一个普通的知识整理工具。",
            feasibility="技术实现简单。",
            market="适合轻量验证。",
            knowledge_gaps=["用户场景"],
            resource_gaps=["种子内容"],
            team_requirements=["独立开发者"],
            similar_projects=["笔记工具"],
            mvp_roadmap=["完成输入输出"],
            long_term_roadmap=["补协作能力"],
        ),
        refinement_result=None,
        completed_at=root_time,
        updated_at=root_time,
    )
    root_record = SessionRecord(
        session_id="sess_search_root",
        root_session_id="sess_search_root",
        parent_session_id=None,
        session_kind=SessionKind.ANALYSIS,
        original_content=root_snapshot.original_content,
        input_echo=root_snapshot.input_echo,
        clarification_count=0,
        archive_status=ArchiveStatus.SUCCEEDED,
        archive_url="https://feishu.example.com/docx/sess_search_root",
        completed_at=root_time,
        archived_at=root_time,
        updated_at=root_time,
    )
    draft_snapshot = SessionSnapshot(
        session_id="sess_search_draft",
        root_session_id="sess_search_root",
        parent_session_id="sess_search_root",
        session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
        archive_title="只在草稿里出现的方案",
        original_content=root_snapshot.original_content,
        input_echo="这是只在草稿里出现的关键短语。",
        clarifications=[],
        assumptions=["草稿仍未合成。"],
        open_questions=[],
        follow_up_question="这是只在草稿里出现的关键短语。",
        analysis=None,
        refinement_result=RefinementResult(
            question_summary="草稿关键短语",
            refinement_answer="这里只存在于草稿缓存中。",
            affected_sections=[AnalysisSectionKey.SUMMARY],
            proposed_section_updates=[
                SectionUpdate(
                    section_key=AnalysisSectionKey.SUMMARY,
                    change_summary="补一个只存在于草稿中的表达。",
                    updated_text="这是只在草稿里出现的关键短语。",
                    updated_items=[],
                )
            ],
            next_actions=["确认后再生成正式版本。"],
        ),
        completed_at=draft_time,
        updated_at=draft_time,
    )
    draft_record = SessionRecord(
        session_id="sess_search_draft",
        root_session_id="sess_search_root",
        parent_session_id="sess_search_root",
        session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
        original_content=root_snapshot.original_content,
        input_echo=draft_snapshot.input_echo,
        clarification_count=0,
        archive_status=ArchiveStatus.NOT_TRIGGERED,
        completed_at=draft_time,
        updated_at=draft_time,
    )
    snapshot_store.save_session_snapshot(root_snapshot)
    snapshot_store.save_session_snapshot(draft_snapshot)
    archive_store.save_session_record(root_record)
    archive_store.save_session_record(draft_record)

    response = service.list_threads(limit=10, query="只在草稿里出现的关键短语")

    assert response.items == []


def test_get_thread_returns_sessions_ordered_by_creation_time() -> None:
    service = build_service()

    response = service.get_thread("sess_root")

    assert response.root_session_id == "sess_root"
    assert [item.session_id for item in response.items] == [
        "sess_root",
        "sess_composed",
    ]
    assert [item.formal_version_number for item in response.items] == [1, 2]
    assert [item.parent_formal_version_number for item in response.items] == [None, 1]


def test_branch_follow_up_keeps_linear_global_version_order_and_parent_markers() -> None:
    service = build_service()
    archive_store = service._session_archive_store
    snapshot_store = service._session_snapshot_store
    assert isinstance(archive_store, InMemoryArchiveStore)
    assert isinstance(snapshot_store, InMemorySnapshotStore)

    branch_time = datetime.now(UTC)
    branch_snapshot = SessionSnapshot(
        session_id="sess_branch",
        root_session_id="sess_root",
        parent_session_id="sess_root",
        session_kind=SessionKind.FULL_PLAN_COMPOSED,
        formal_version_number=3,
        archive_title="从 ROOT 分出的新分支方案",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想从 ROOT 版本重新追问分发渠道。",
        clarifications=[],
        assumptions=["保留原有产品边界。"],
        open_questions=[],
        follow_up_question="我想从 ROOT 版本重新追问分发渠道。",
        analysis=IdeaAnalysis(
            summary="这是一个帮助独立开发者验证产品想法的 Web 工具。",
            feasibility="技术可行。",
            market="目标用户明确。",
            knowledge_gaps=["渠道验证方式"],
            resource_gaps=["首批种子用户"],
            team_requirements=["产品负责人"],
            similar_projects=["创业想法分析工具"],
            mvp_roadmap=["补一个渠道验证步骤"],
            long_term_roadmap=["继续迭代交互体验"],
        ),
        refinement_result=RefinementResult(
            question_summary="从旧版本重新分支",
            refinement_answer="保留旧链路，同时新增渠道验证分支。",
            affected_sections=[AnalysisSectionKey.MVP_ROADMAP],
            proposed_section_updates=[
                SectionUpdate(
                    section_key=AnalysisSectionKey.MVP_ROADMAP,
                    change_summary="补充渠道验证步骤。",
                    updated_text=None,
                    updated_items=["先验证 1 个可重复获客渠道。"],
                )
            ],
            next_actions=["确认后继续比较不同分支。"],
        ),
        completed_at=branch_time,
        updated_at=branch_time,
    )
    branch_record = SessionRecord(
        session_id="sess_branch",
        root_session_id="sess_root",
        parent_session_id="sess_root",
        session_kind=SessionKind.FULL_PLAN_COMPOSED,
        formal_version_number=3,
        original_content=branch_snapshot.original_content,
        input_echo=branch_snapshot.input_echo,
        clarification_count=0,
        archive_status=ArchiveStatus.SUCCEEDED,
        archive_url="https://feishu.example.com/docx/sess_branch",
        completed_at=branch_time,
        archived_at=branch_time,
        updated_at=branch_time,
    )
    snapshot_store.save_session_snapshot(branch_snapshot)
    archive_store.save_session_record(branch_record)

    thread_response = service.get_thread("sess_root")

    assert [item.session_id for item in thread_response.items] == [
        "sess_root",
        "sess_composed",
        "sess_branch",
    ]
    assert [item.formal_version_number for item in thread_response.items] == [1, 2, 3]
    assert [item.parent_formal_version_number for item in thread_response.items] == [
        None,
        1,
        1,
    ]

    threads_response = service.list_threads(limit=10)
    assert threads_response.items[0].latest_session_id == "sess_branch"
    assert threads_response.items[0].latest_formal_version_number == 3


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


def test_delete_leaf_session_removes_formal_leaf_and_attached_drafts() -> None:
    service = build_service()
    archive_store = service._session_archive_store
    snapshot_store = service._session_snapshot_store
    archiver = service._session_archiver
    assert isinstance(archive_store, InMemoryArchiveStore)
    assert isinstance(snapshot_store, InMemorySnapshotStore)
    assert isinstance(archiver, InMemoryArchiver)

    composed_snapshot = snapshot_store.get_session_snapshot("sess_composed")
    composed_record = archive_store.get_session_record("sess_composed")
    refinement_snapshot = snapshot_store.get_session_snapshot("sess_refine")
    assert composed_snapshot is not None
    assert composed_record is not None
    assert refinement_snapshot is not None
    assert refinement_snapshot.refinement_result is not None

    draft_time = composed_snapshot.updated_at + timedelta(minutes=20)
    attached_draft_snapshot = SessionSnapshot(
        session_id="sess_composed_draft",
        root_session_id="sess_root",
        parent_session_id="sess_composed",
        session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
        archive_title="Composed leaf draft",
        original_content=composed_snapshot.original_content,
        input_echo="Refine the composed leaf further.",
        clarifications=[],
        assumptions=["Keep the product boundary stable."],
        open_questions=[],
        follow_up_question="Refine the composed leaf further.",
        analysis=None,
        refinement_result=refinement_snapshot.refinement_result,
        completed_at=draft_time,
        updated_at=draft_time,
    )
    attached_draft_record = SessionRecord(
        session_id="sess_composed_draft",
        root_session_id="sess_root",
        parent_session_id="sess_composed",
        session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
        original_content=composed_snapshot.original_content,
        input_echo=attached_draft_snapshot.input_echo,
        clarification_count=0,
        archive_status=ArchiveStatus.NOT_TRIGGERED,
        completed_at=draft_time,
        updated_at=draft_time,
    )
    snapshot_store.save_session_snapshot(attached_draft_snapshot)
    archive_store.save_session_record(attached_draft_record)

    response = service.delete_leaf_session("sess_composed")

    assert response.session_id == "sess_composed"
    assert response.root_session_id == "sess_root"
    assert response.parent_session_id == "sess_root"
    assert response.deleted_session_count == 2
    assert response.deleted_draft_count == 1
    assert response.deleted_archive_count == 1
    assert response.deleted_session_ids == ["sess_composed", "sess_composed_draft"]
    assert response.archive_delete_failures == []
    assert "https://feishu.example.com/docx/sess_composed" in archiver.deleted_urls
    assert snapshot_store.get_session_snapshot("sess_composed") is None
    assert archive_store.get_session_record("sess_composed") is None
    assert snapshot_store.get_session_snapshot("sess_composed_draft") is None
    assert archive_store.get_session_record("sess_composed_draft") is None

    thread_response = service.get_thread("sess_root")
    assert [item.session_id for item in thread_response.items] == ["sess_root"]


def test_delete_leaf_session_blocks_root_delete() -> None:
    service = build_service()

    try:
        service.delete_leaf_session("sess_root")
    except SessionStateError as exc:
        assert str(exc) == "ROOT version must be deleted at thread level."
    else:
        raise AssertionError("Expected ROOT single-session delete to be blocked.")


def test_delete_leaf_session_blocks_non_leaf_formal_version() -> None:
    service = build_service()
    archive_store = service._session_archive_store
    snapshot_store = service._session_snapshot_store
    assert isinstance(archive_store, InMemoryArchiveStore)
    assert isinstance(snapshot_store, InMemorySnapshotStore)

    composed_snapshot = snapshot_store.get_session_snapshot("sess_composed")
    composed_record = archive_store.get_session_record("sess_composed")
    assert composed_snapshot is not None
    assert composed_record is not None

    child_time = composed_snapshot.updated_at + timedelta(hours=1)
    child_snapshot = composed_snapshot.model_copy(
        update={
            "session_id": "sess_composed_child",
            "parent_session_id": "sess_composed",
            "formal_version_number": 3,
            "archive_title": "Composed child version",
            "input_echo": "Branch again from V02.",
            "follow_up_question": "Branch again from V02.",
            "created_at": child_time,
            "completed_at": child_time,
            "archived_at": child_time,
            "updated_at": child_time,
        }
    )
    child_record = composed_record.model_copy(
        update={
            "session_id": "sess_composed_child",
            "parent_session_id": "sess_composed",
            "formal_version_number": 3,
            "input_echo": child_snapshot.input_echo,
            "archive_url": "https://feishu.example.com/docx/sess_composed_child",
            "created_at": child_time,
            "completed_at": child_time,
            "archived_at": child_time,
            "updated_at": child_time,
        }
    )
    snapshot_store.save_session_snapshot(child_snapshot)
    archive_store.save_session_record(child_record)

    try:
        service.delete_leaf_session("sess_composed")
    except SessionStateError as exc:
        assert str(exc) == "Only leaf versions can be deleted individually."
    else:
        raise AssertionError("Expected non-leaf formal version delete to be blocked.")


def test_delete_leaf_session_allows_branch_leaf_even_when_not_latest() -> None:
    service = build_service()
    archive_store = service._session_archive_store
    snapshot_store = service._session_snapshot_store
    assert isinstance(archive_store, InMemoryArchiveStore)
    assert isinstance(snapshot_store, InMemorySnapshotStore)

    composed_snapshot = snapshot_store.get_session_snapshot("sess_composed")
    composed_record = archive_store.get_session_record("sess_composed")
    assert composed_snapshot is not None
    assert composed_record is not None

    branch_time = composed_snapshot.updated_at + timedelta(hours=2)
    branch_snapshot = composed_snapshot.model_copy(
        update={
            "session_id": "sess_branch_latest",
            "parent_session_id": "sess_root",
            "formal_version_number": 3,
            "archive_title": "Latest branch version",
            "input_echo": "Go back to ROOT and branch into a new path.",
            "follow_up_question": "Go back to ROOT and branch into a new path.",
            "created_at": branch_time,
            "completed_at": branch_time,
            "archived_at": branch_time,
            "updated_at": branch_time,
        }
    )
    branch_record = composed_record.model_copy(
        update={
            "session_id": "sess_branch_latest",
            "parent_session_id": "sess_root",
            "formal_version_number": 3,
            "input_echo": branch_snapshot.input_echo,
            "archive_url": "https://feishu.example.com/docx/sess_branch_latest",
            "created_at": branch_time,
            "completed_at": branch_time,
            "archived_at": branch_time,
            "updated_at": branch_time,
        }
    )
    snapshot_store.save_session_snapshot(branch_snapshot)
    archive_store.save_session_record(branch_record)

    response = service.delete_leaf_session("sess_composed")

    assert response.session_id == "sess_composed"
    assert response.parent_session_id == "sess_root"

    thread_response = service.get_thread("sess_root")
    assert [item.session_id for item in thread_response.items] == [
        "sess_root",
        "sess_branch_latest",
    ]
    assert [item.formal_version_number for item in thread_response.items] == [1, 3]


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
