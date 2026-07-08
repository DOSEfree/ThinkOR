"""Application-layer history queries for v0.3.0 thread navigation."""

from ideaos_agent.domain.archive import (
    ArchiveStatus,
    SessionArchiveStore,
    SessionRecord,
)
from ideaos_agent.domain.errors import SessionNotFoundError
from ideaos_agent.domain.session import SessionKind, SessionSnapshot, SessionSnapshotStore
from ideaos_agent.models import (
    ClarificationAnswer,
    SessionDetailResponse,
    SessionHistoryItem,
    SessionListResponse,
    SessionThreadResponse,
    SessionThreadSummary,
    ThreadListResponse,
)


class SessionHistoryService:
    """Read local history and thread views without changing analysis behavior."""

    def __init__(
        self,
        *,
        session_archive_store: SessionArchiveStore,
        session_snapshot_store: SessionSnapshotStore,
    ) -> None:
        self._session_archive_store = session_archive_store
        self._session_snapshot_store = session_snapshot_store

    def list_sessions(self, *, limit: int = 20) -> SessionListResponse:
        """Return recent session history items ordered by last update time."""

        snapshots = self._session_snapshot_store.list_session_snapshots(limit=limit)
        records = self._records_by_session_id(
            self._session_archive_store.list_session_records(limit=limit)
        )
        return SessionListResponse(
            items=[
                self._build_history_item(
                    snapshot=snapshot,
                    record=records.get(snapshot.session_id),
                )
                for snapshot in snapshots
            ]
        )

    def get_session_detail(self, session_id: str) -> SessionDetailResponse:
        """Return the detailed local view for one session."""

        snapshot = self._require_snapshot(session_id)
        record = self._require_record(session_id)
        children = self._session_snapshot_store.list_session_snapshots(
            root_session_id=snapshot.root_session_id
        )
        child_session_ids = [
            child.session_id
            for child in children
            if child.parent_session_id == snapshot.session_id
        ]

        return SessionDetailResponse(
            session_id=snapshot.session_id,
            root_session_id=snapshot.root_session_id,
            parent_session_id=snapshot.parent_session_id,
            session_kind=snapshot.session_kind,
            archive_status=record.archive_status,
            archive_url=record.archive_url,
            archive_title=snapshot.archive_title,
            original_content=snapshot.original_content,
            input_echo=snapshot.input_echo,
            clarifications=[
                ClarificationAnswer(question=item.question, answer=item.answer)
                for item in snapshot.clarifications
            ],
            assumptions=snapshot.assumptions,
            open_questions=snapshot.open_questions,
            follow_up_question=snapshot.follow_up_question,
            analysis=snapshot.analysis,
            refinement_result=snapshot.refinement_result,
            created_at=snapshot.created_at,
            completed_at=snapshot.completed_at,
            updated_at=snapshot.updated_at,
            archived_at=snapshot.archived_at,
            can_continue_follow_up=self._can_continue_follow_up(snapshot, record),
            child_session_ids=child_session_ids,
        )

    def list_threads(self, *, limit: int = 20) -> ThreadListResponse:
        """Return recent thread summaries grouped by root session ID."""

        snapshots = self._session_snapshot_store.list_session_snapshots()
        records = self._records_by_session_id(self._session_archive_store.list_session_records())

        grouped: dict[str, list[SessionSnapshot]] = {}
        for snapshot in snapshots:
            grouped.setdefault(snapshot.root_session_id, []).append(snapshot)

        items: list[SessionThreadSummary] = []
        for root_session_id, thread_snapshots in grouped.items():
            sorted_thread = sorted(
                thread_snapshots,
                key=lambda item: item.updated_at,
                reverse=True,
            )
            latest = sorted_thread[0]
            latest_record = records.get(latest.session_id)
            root_snapshot = next(
                (
                    item
                    for item in thread_snapshots
                    if item.session_id == item.root_session_id
                ),
                sorted_thread[-1],
            )
            items.append(
                SessionThreadSummary(
                    root_session_id=root_session_id,
                    root_archive_title=root_snapshot.archive_title,
                    latest_session_id=latest.session_id,
                    latest_session_kind=latest.session_kind,
                    latest_archive_status=(
                        latest_record.archive_status
                        if latest_record is not None
                        else ArchiveStatus.NOT_TRIGGERED
                    ),
                    latest_updated_at=latest.updated_at,
                    session_count=len(thread_snapshots),
                )
            )

        items.sort(key=lambda item: item.latest_updated_at, reverse=True)
        if limit > 0:
            items = items[:limit]
        return ThreadListResponse(items=items)

    def get_thread(self, root_session_id: str) -> SessionThreadResponse:
        """Return all sessions in one thread ordered by creation time."""

        normalized_root_session_id = root_session_id.strip()
        if not normalized_root_session_id:
            raise ValueError("root_session_id must not be blank.")

        snapshots = self._session_snapshot_store.list_session_snapshots(
            root_session_id=normalized_root_session_id
        )
        if not snapshots:
            raise SessionNotFoundError(
                f"Thread root session not found: {normalized_root_session_id}"
            )
        snapshots.sort(key=lambda item: item.created_at)
        records = self._records_by_session_id(
            self._session_archive_store.list_session_records(
                root_session_id=normalized_root_session_id
            )
        )

        return SessionThreadResponse(
            root_session_id=normalized_root_session_id,
            items=[
                self._build_history_item(
                    snapshot=snapshot,
                    record=records.get(snapshot.session_id),
                )
                for snapshot in snapshots
            ],
        )

    def _build_history_item(
        self,
        *,
        snapshot: SessionSnapshot,
        record: SessionRecord | None,
    ) -> SessionHistoryItem:
        """Project one local session into a compact history item."""

        archive_status = (
            record.archive_status if record is not None else ArchiveStatus.NOT_TRIGGERED
        )
        archive_url = record.archive_url if record is not None else None
        return SessionHistoryItem(
            session_id=snapshot.session_id,
            root_session_id=snapshot.root_session_id,
            parent_session_id=snapshot.parent_session_id,
            session_kind=snapshot.session_kind,
            archive_title=snapshot.archive_title,
            archive_status=archive_status,
            archive_url=archive_url,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            can_continue_follow_up=self._can_continue_follow_up(snapshot, record),
        )

    def _can_continue_follow_up(
        self,
        snapshot: SessionSnapshot,
        record: SessionRecord | None,
    ) -> bool:
        """Determine whether one completed session can be used as a follow-up parent."""

        if record is None:
            return False
        if record.archive_status not in {ArchiveStatus.SUCCEEDED, ArchiveStatus.FAILED}:
            return False
        return snapshot.session_kind in {
            SessionKind.ANALYSIS,
            SessionKind.FULL_PLAN_COMPOSED,
        }

    def _records_by_session_id(
        self,
        records: list[SessionRecord],
    ) -> dict[str, SessionRecord]:
        """Index session records by session ID."""

        return {record.session_id: record for record in records}

    def _require_snapshot(self, session_id: str) -> SessionSnapshot:
        """Fetch one session snapshot or raise a domain error."""

        snapshot = self._session_snapshot_store.get_session_snapshot(session_id)
        if snapshot is None:
            raise SessionNotFoundError(f"Session snapshot not found: {session_id}")
        return snapshot

    def _require_record(self, session_id: str) -> SessionRecord:
        """Fetch one session record or raise a domain error."""

        record = self._session_archive_store.get_session_record(session_id)
        if record is None:
            raise SessionNotFoundError(f"Session record not found: {session_id}")
        return record
