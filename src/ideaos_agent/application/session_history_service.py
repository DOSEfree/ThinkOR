"""Application-layer history queries for v0.3.0 thread navigation."""

from datetime import UTC, datetime, timedelta

from ideaos_agent.domain.archive import (
    ArchiveStatus,
    SessionArchiver,
    SessionArchiveStore,
    SessionRecord,
)
from ideaos_agent.domain.errors import SessionNotFoundError
from ideaos_agent.domain.session import SessionKind, SessionSnapshot, SessionSnapshotStore
from ideaos_agent.models import (
    ArchiveDeleteFailure,
    ArchiveProbeFailure,
    ArchiveSyncResponse,
    ClarificationAnswer,
    SessionDetailResponse,
    SessionHistoryItem,
    SessionListResponse,
    SessionThreadResponse,
    SessionThreadSummary,
    ThreadDeleteResponse,
    ThreadListResponse,
)


class SessionHistoryService:
    """Read and maintain local history/thread views without touching analysis logic."""

    def __init__(
        self,
        *,
        follow_up_draft_retention_days: int,
        session_archive_store: SessionArchiveStore,
        session_snapshot_store: SessionSnapshotStore,
        session_archiver: SessionArchiver,
    ) -> None:
        self._follow_up_draft_retention_days = max(follow_up_draft_retention_days, 0)
        self._session_archive_store = session_archive_store
        self._session_snapshot_store = session_snapshot_store
        self._session_archiver = session_archiver

    def list_sessions(self, *, limit: int = 20) -> SessionListResponse:
        """Return recent formal session history items ordered by last update time."""

        self._prune_expired_follow_up_drafts()
        snapshots = sorted(
            [
                snapshot
                for snapshot in self._session_snapshot_store.list_session_snapshots()
                if self._is_formal_session(snapshot.session_kind)
            ],
            key=lambda item: item.updated_at,
            reverse=True,
        )
        if limit > 0:
            snapshots = snapshots[:limit]

        records = self._records_by_session_id(self._session_archive_store.list_session_records())
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

        self._prune_expired_follow_up_drafts()
        snapshot = self._require_snapshot(session_id)
        record = self._require_record(session_id)
        children = self._snapshots_for_root(snapshot.root_session_id, include_drafts=True)
        child_session_ids = [
            child.session_id
            for child in children
            if child.parent_session_id == snapshot.session_id
            and self._is_formal_session(child.session_kind)
        ]
        active_follow_up_draft = (
            self._find_active_follow_up_draft(snapshot.session_id)
            if self._is_formal_session(snapshot.session_kind)
            else None
        )

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
            active_follow_up_draft_id=(
                active_follow_up_draft.session_id if active_follow_up_draft is not None else None
            ),
            active_follow_up_draft_question=(
                active_follow_up_draft.follow_up_question
                if active_follow_up_draft is not None
                else None
            ),
            active_follow_up_draft_updated_at=(
                active_follow_up_draft.updated_at if active_follow_up_draft is not None else None
            ),
        )

    def list_threads(self, *, limit: int = 20) -> ThreadListResponse:
        """Return recent thread summaries grouped by root session ID."""

        self._prune_expired_follow_up_drafts()
        snapshots = [
            snapshot
            for snapshot in self._session_snapshot_store.list_session_snapshots()
            if self._is_formal_session(snapshot.session_kind)
        ]
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
        """Return all formal sessions in one thread ordered by creation time."""

        self._prune_expired_follow_up_drafts()
        normalized_root_session_id = root_session_id.strip()
        if not normalized_root_session_id:
            raise ValueError("root_session_id must not be blank.")

        snapshots = self._snapshots_for_root(
            normalized_root_session_id,
            include_drafts=False,
        )
        if not snapshots:
            raise SessionNotFoundError(
                f"Thread root session not found: {normalized_root_session_id}"
            )
        snapshots.sort(key=lambda item: item.created_at)
        records = self._records_by_session_id(
            self._records_for_root(
                normalized_root_session_id,
                include_drafts=False,
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

    def sync_remote_archive_deletions(self) -> ArchiveSyncResponse:
        """Remove local sessions whose linked remote archives are no longer present."""

        self._prune_expired_follow_up_drafts()
        records = [
            record
            for record in self._session_archive_store.list_session_records()
            if record.archive_url is not None
        ]

        removed_session_ids: list[str] = []
        probe_failures: list[ArchiveProbeFailure] = []
        for record in records:
            archive_url = record.archive_url
            if archive_url is None:
                continue

            probe_result = self._session_archiver.probe_archive(archive_url)
            if probe_result.found is True:
                continue
            if probe_result.found is None:
                probe_failures.append(
                    ArchiveProbeFailure(
                        archive_url=probe_result.archive_url,
                        error=probe_result.archive_error
                        or "Remote archive probe failed without a readable error.",
                    )
                )
                continue

            self._session_snapshot_store.delete_session_snapshot(record.session_id)
            self._session_archive_store.delete_session_record(record.session_id)
            removed_session_ids.append(record.session_id)

        return ArchiveSyncResponse(
            checked_archive_count=len(records),
            removed_session_count=len(removed_session_ids),
            removed_session_ids=removed_session_ids,
            probe_failures=probe_failures,
        )

    def delete_thread(self, root_session_id: str) -> ThreadDeleteResponse:
        """Delete one thread locally and best-effort delete its Feishu archives."""

        self._prune_expired_follow_up_drafts()
        normalized_root_session_id = root_session_id.strip()
        if not normalized_root_session_id:
            raise ValueError("root_session_id must not be blank.")

        snapshots = self._snapshots_for_root(normalized_root_session_id, include_drafts=True)
        records = self._records_for_root(normalized_root_session_id, include_drafts=True)
        if not snapshots and not records:
            raise SessionNotFoundError(
                f"Thread root session not found: {normalized_root_session_id}"
            )

        archive_urls: list[str] = []
        deleted_session_ids: set[str] = {snapshot.session_id for snapshot in snapshots}
        for record in records:
            deleted_session_ids.add(record.session_id)
            if record.archive_url is None:
                continue
            if record.archive_url not in archive_urls:
                archive_urls.append(record.archive_url)

        deleted_archive_count = 0
        archive_delete_failures: list[ArchiveDeleteFailure] = []
        for archive_url in archive_urls:
            delete_result = self._session_archiver.delete_archive(archive_url)
            if delete_result.deleted:
                deleted_archive_count += 1
                continue
            archive_delete_failures.append(
                ArchiveDeleteFailure(
                    archive_url=delete_result.archive_url,
                    error=delete_result.archive_error or "Remote archive delete failed.",
                )
            )

        for snapshot in snapshots:
            self._session_snapshot_store.delete_session_snapshot(snapshot.session_id)
        for record in records:
            self._session_archive_store.delete_session_record(record.session_id)

        return ThreadDeleteResponse(
            root_session_id=normalized_root_session_id,
            deleted_session_count=len(deleted_session_ids),
            deleted_archive_count=deleted_archive_count,
            archive_delete_failures=archive_delete_failures,
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
        return self._is_formal_session(snapshot.session_kind)

    def _records_by_session_id(
        self,
        records: list[SessionRecord],
    ) -> dict[str, SessionRecord]:
        """Index session records by session ID."""

        return {record.session_id: record for record in records}

    def _snapshots_for_root(
        self,
        root_session_id: str,
        *,
        include_drafts: bool,
    ) -> list[SessionSnapshot]:
        """Resolve all snapshots for one root thread with legacy-root compatibility."""

        snapshots = [
            snapshot
            for snapshot in self._session_snapshot_store.list_session_snapshots()
            if snapshot.root_session_id == root_session_id
        ]
        if include_drafts:
            return snapshots
        return [
            snapshot for snapshot in snapshots if self._is_formal_session(snapshot.session_kind)
        ]

    def _records_for_root(
        self,
        root_session_id: str,
        *,
        include_drafts: bool,
    ) -> list[SessionRecord]:
        """Resolve all records for one root thread with legacy-root compatibility."""

        records = [
            record
            for record in self._session_archive_store.list_session_records()
            if record.root_session_id == root_session_id
        ]
        if include_drafts:
            return records
        return [record for record in records if self._is_formal_session(record.session_kind)]

    def _find_active_follow_up_draft(self, parent_session_id: str) -> SessionSnapshot | None:
        """Return the latest recoverable follow-up draft for one formal parent session."""

        cutoff = self._draft_retention_cutoff()
        candidates = [
            snapshot
            for snapshot in self._session_snapshot_store.list_session_snapshots(
                session_kind=SessionKind.FOLLOW_UP_REFINEMENT
            )
            if snapshot.parent_session_id == parent_session_id and snapshot.updated_at >= cutoff
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.updated_at, reverse=True)
        return candidates[0]

    def _prune_expired_follow_up_drafts(self) -> None:
        """Delete expired draft cache rows from both snapshot and record storage."""

        cutoff = self._draft_retention_cutoff()
        expired_session_ids: set[str] = set()
        for record in self._session_archive_store.list_session_records(
            session_kind=SessionKind.FOLLOW_UP_REFINEMENT
        ):
            if record.updated_at < cutoff:
                expired_session_ids.add(record.session_id)
        for snapshot in self._session_snapshot_store.list_session_snapshots(
            session_kind=SessionKind.FOLLOW_UP_REFINEMENT
        ):
            if snapshot.updated_at < cutoff:
                expired_session_ids.add(snapshot.session_id)

        for session_id in expired_session_ids:
            self._session_snapshot_store.delete_session_snapshot(session_id)
            self._session_archive_store.delete_session_record(session_id)

    def _draft_retention_cutoff(self) -> datetime:
        """Return the oldest timestamp still preserved as a draft cache."""

        return datetime.now(UTC) - timedelta(days=self._follow_up_draft_retention_days)

    def _is_formal_session(self, session_kind: SessionKind) -> bool:
        """Return whether one session kind should appear in formal history."""

        return session_kind in {
            SessionKind.ANALYSIS,
            SessionKind.FULL_PLAN_COMPOSED,
        }

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
