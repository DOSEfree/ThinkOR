"""Application-layer history queries for v0.3.0 thread navigation."""

from datetime import UTC, datetime, timedelta

from ideaos_agent.domain.archive import (
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionArchiver,
    SessionArchiveStore,
    SessionRecord,
)
from ideaos_agent.domain.errors import SessionNotFoundError, SessionStateError
from ideaos_agent.domain.session import SessionKind, SessionSnapshot, SessionSnapshotStore
from ideaos_agent.models import (
    ArchiveDeleteFailure,
    ArchiveProbeFailure,
    ArchiveRetryResponse,
    ArchiveSyncResponse,
    ClarificationAnswer,
    SessionDetailResponse,
    SessionHistoryItem,
    SessionLeafDeleteResponse,
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
        all_snapshots = sorted(
            [
                snapshot
                for snapshot in self._session_snapshot_store.list_session_snapshots()
                if self._is_formal_session(snapshot.session_kind)
            ],
            key=lambda item: item.updated_at,
            reverse=True,
        )
        snapshots = all_snapshots
        if limit > 0:
            snapshots = snapshots[:limit]

        records = self._records_by_session_id(self._session_archive_store.list_session_records())
        version_maps = self._build_formal_version_maps(all_snapshots)
        child_parent_maps = self._build_formal_child_parent_id_maps(
            all_snapshots,
            list(records.values()),
        )
        return SessionListResponse(
            items=[
                self._build_history_item(
                    snapshot=snapshot,
                    record=records.get(snapshot.session_id),
                    version_lookup=version_maps.get(snapshot.root_session_id, {}),
                    formal_child_parent_ids=child_parent_maps.get(
                        snapshot.root_session_id,
                        set(),
                    ),
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
        formal_snapshots = [
            item for item in children if self._is_formal_session(item.session_kind)
        ]
        version_lookup = self._build_formal_version_lookup(formal_snapshots)
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
            formal_version_number=self._resolve_snapshot_formal_version_number(
                snapshot,
                version_lookup,
            ),
            parent_formal_version_number=self._resolve_parent_formal_version_number(
                snapshot,
                version_lookup,
            ),
            session_kind=snapshot.session_kind,
            archive_status=record.archive_status,
            archive_url=record.archive_url,
            archive_error=self._safe_archive_error(record.archive_error),
            archive_title=snapshot.archive_title,
            original_content=snapshot.original_content,
            input_echo=snapshot.input_echo,
            intent=snapshot.intent,
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

    def retry_failed_archive(self, session_id: str) -> ArchiveRetryResponse:
        """Retry one failed Feishu archive without regenerating the local session."""

        snapshot = self._require_snapshot(session_id)
        record = self._require_record(session_id)
        if record.archive_status != ArchiveStatus.FAILED:
            raise SessionStateError("Only failed Feishu archives can be retried.")

        root_record = self._require_record(snapshot.root_session_id)
        parent_record = (
            self._require_record(snapshot.parent_session_id)
            if snapshot.parent_session_id is not None
            else None
        )
        archive_payload = SessionArchivePayload(
            session_id=snapshot.session_id,
            root_session_id=snapshot.root_session_id,
            root_archive_url=root_record.archive_url,
            parent_session_id=snapshot.parent_session_id,
            parent_archive_url=(parent_record.archive_url if parent_record is not None else None),
            session_kind=snapshot.session_kind,
            archive_title=snapshot.archive_title,
            original_content=snapshot.original_content,
            input_echo=snapshot.input_echo,
            intent=snapshot.intent,
            clarifications=snapshot.clarifications,
            assumptions=snapshot.assumptions,
            open_questions=snapshot.open_questions,
            follow_up_question=snapshot.follow_up_question,
            analysis=snapshot.analysis,
            refinement_result=snapshot.refinement_result,
            created_at=snapshot.created_at,
            completed_at=snapshot.completed_at,
        )
        archive_result = self._try_archive_session(archive_payload)
        updated_record = self._session_archive_store.save_session_record(
            record.model_copy(
                update={
                    "archive_status": archive_result.archive_status,
                    "archive_url": archive_result.archive_url,
                    "archive_error": archive_result.archive_error,
                    "archived_at": archive_result.archived_at,
                    "updated_at": archive_result.archived_at,
                }
            )
        )
        self._session_snapshot_store.save_session_snapshot(
            snapshot.model_copy(
                update={
                    "archived_at": archive_result.archived_at,
                    "updated_at": archive_result.archived_at,
                }
            )
        )
        return ArchiveRetryResponse(
            session_id=updated_record.session_id,
            archive_status=updated_record.archive_status,
            archive_url=updated_record.archive_url,
            archive_error=self._safe_archive_error(updated_record.archive_error),
            archived_at=archive_result.archived_at,
        )

    def list_threads(
        self,
        *,
        limit: int = 20,
        query: str | None = None,
    ) -> ThreadListResponse:
        """Return recent thread summaries grouped by root session ID."""

        self._prune_expired_follow_up_drafts()
        normalized_query = self._normalize_history_query(query)
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
            if normalized_query is not None and not self._thread_matches_query(
                thread_snapshots,
                normalized_query,
            ):
                continue
            version_lookup = self._build_formal_version_lookup(thread_snapshots)
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
                    latest_formal_version_number=version_lookup.get(latest.session_id),
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
        version_lookup = self._build_formal_version_lookup(snapshots)
        snapshots.sort(
            key=lambda item: (
                version_lookup.get(item.session_id, item.formal_version_number or 10**9),
                item.created_at,
                item.session_id,
            )
        )
        records = self._records_by_session_id(
            self._records_for_root(
                normalized_root_session_id,
                include_drafts=False,
            )
        )
        formal_child_parent_ids = self._build_formal_child_parent_ids(
            snapshots,
            list(records.values()),
        )

        return SessionThreadResponse(
            root_session_id=normalized_root_session_id,
            items=[
                self._build_history_item(
                    snapshot=snapshot,
                    record=records.get(snapshot.session_id),
                    version_lookup=version_lookup,
                    formal_child_parent_ids=formal_child_parent_ids,
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
            try:
                delete_result = self._session_archiver.delete_archive(archive_url)
            except Exception as exc:
                archive_delete_failures.append(
                    ArchiveDeleteFailure(
                        archive_url=archive_url,
                        error=f"Remote archive delete raised an error: {exc}",
                    )
                )
                continue
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

    def delete_leaf_session(self, session_id: str) -> SessionLeafDeleteResponse:
        """Delete one non-root formal leaf session and its attached local draft cache."""

        self._prune_expired_follow_up_drafts()
        normalized_session_id = session_id.strip()
        if not normalized_session_id:
            raise ValueError("session_id must not be blank.")

        snapshot = self._require_snapshot(normalized_session_id)
        record = self._require_record(normalized_session_id)
        if not self._is_formal_session(snapshot.session_kind) or not self._is_formal_session(
            record.session_kind
        ):
            raise SessionStateError(
                "Only formal non-root leaf versions can be deleted individually."
            )
        if snapshot.parent_session_id is None or snapshot.session_id == snapshot.root_session_id:
            raise SessionStateError("ROOT version must be deleted at thread level.")
        if self._has_formal_child_session(
            parent_session_id=normalized_session_id,
            root_session_id=snapshot.root_session_id,
        ):
            raise SessionStateError("Only leaf versions can be deleted individually.")

        draft_snapshots = self._list_attached_follow_up_draft_snapshots(
            parent_session_id=normalized_session_id,
            root_session_id=snapshot.root_session_id,
        )
        draft_records = self._list_attached_follow_up_draft_records(
            parent_session_id=normalized_session_id,
            root_session_id=snapshot.root_session_id,
        )
        draft_session_ids = {
            item.session_id for item in draft_snapshots
        } | {item.session_id for item in draft_records}
        deleted_session_ids = [normalized_session_id, *sorted(draft_session_ids)]

        records_by_session_id = {item.session_id: item for item in [record, *draft_records]}
        deleted_archive_count = 0
        archive_delete_failures: list[ArchiveDeleteFailure] = []
        deleted_archive_urls: set[str] = set()
        for deleted_session_id in deleted_session_ids:
            current_record = records_by_session_id.get(deleted_session_id)
            if current_record is None or current_record.archive_url is None:
                continue
            if current_record.archive_url in deleted_archive_urls:
                continue

            deleted_archive_urls.add(current_record.archive_url)
            try:
                delete_result = self._session_archiver.delete_archive(current_record.archive_url)
            except Exception as exc:
                archive_delete_failures.append(
                    ArchiveDeleteFailure(
                        archive_url=current_record.archive_url,
                        error=f"Remote archive delete raised an error: {exc}",
                    )
                )
                continue
            if delete_result.deleted:
                deleted_archive_count += 1
                continue
            archive_delete_failures.append(
                ArchiveDeleteFailure(
                    archive_url=delete_result.archive_url,
                    error=delete_result.archive_error or "Remote archive delete failed.",
                )
            )

        for deleted_session_id in deleted_session_ids:
            self._session_snapshot_store.delete_session_snapshot(deleted_session_id)
            self._session_archive_store.delete_session_record(deleted_session_id)

        return SessionLeafDeleteResponse(
            session_id=normalized_session_id,
            root_session_id=snapshot.root_session_id,
            parent_session_id=snapshot.parent_session_id,
            deleted_session_count=len(deleted_session_ids),
            deleted_draft_count=len(draft_session_ids),
            deleted_archive_count=deleted_archive_count,
            deleted_session_ids=deleted_session_ids,
            archive_delete_failures=archive_delete_failures,
        )

    def _build_history_item(
        self,
        *,
        snapshot: SessionSnapshot,
        record: SessionRecord | None,
        version_lookup: dict[str, int],
        formal_child_parent_ids: set[str],
    ) -> SessionHistoryItem:
        """Project one local session into a compact history item."""

        archive_status = (
            record.archive_status if record is not None else ArchiveStatus.NOT_TRIGGERED
        )
        archive_url = record.archive_url if record is not None else None
        can_delete_leaf, delete_block_reason = self._resolve_leaf_delete_state(
            snapshot,
            formal_child_parent_ids,
        )
        return SessionHistoryItem(
            session_id=snapshot.session_id,
            root_session_id=snapshot.root_session_id,
            parent_session_id=snapshot.parent_session_id,
            formal_version_number=self._resolve_snapshot_formal_version_number(
                snapshot,
                version_lookup,
            ),
            parent_formal_version_number=self._resolve_parent_formal_version_number(
                snapshot,
                version_lookup,
            ),
            session_kind=snapshot.session_kind,
            archive_title=snapshot.archive_title,
            archive_status=archive_status,
            archive_url=archive_url,
            intent=snapshot.intent,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            can_delete_leaf=can_delete_leaf,
            delete_block_reason=delete_block_reason,
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
        if record.archive_status not in {
            ArchiveStatus.SIMULATED,
            ArchiveStatus.SUCCEEDED,
            ArchiveStatus.FAILED,
        }:
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

    def _normalize_history_query(self, query: str | None) -> str | None:
        """Normalize one local history search query for substring matching."""

        if query is None:
            return None
        normalized = "".join(query.casefold().split())
        return normalized or None

    def _build_formal_version_maps(
        self,
        snapshots: list[SessionSnapshot],
    ) -> dict[str, dict[str, int]]:
        """Build stable formal-version lookups grouped by root session ID."""

        grouped: dict[str, list[SessionSnapshot]] = {}
        for snapshot in snapshots:
            grouped.setdefault(snapshot.root_session_id, []).append(snapshot)
        return {
            root_session_id: self._build_formal_version_lookup(thread_snapshots)
            for root_session_id, thread_snapshots in grouped.items()
        }

    def _build_formal_version_lookup(
        self,
        snapshots: list[SessionSnapshot],
    ) -> dict[str, int]:
        """Build one stable formal-version lookup with legacy fallback."""

        formal_snapshots = [
            snapshot for snapshot in snapshots if self._is_formal_session(snapshot.session_kind)
        ]
        formal_snapshots.sort(key=lambda item: (item.created_at, item.session_id))

        used_numbers = {
            snapshot.formal_version_number
            for snapshot in formal_snapshots
            if snapshot.formal_version_number is not None
        }
        next_number = 1
        resolved: dict[str, int] = {}
        for snapshot in formal_snapshots:
            if snapshot.formal_version_number is not None:
                resolved[snapshot.session_id] = snapshot.formal_version_number
                continue
            while next_number in used_numbers:
                next_number += 1
            resolved[snapshot.session_id] = next_number
            used_numbers.add(next_number)
            next_number += 1
        return resolved

    def _build_formal_child_parent_id_maps(
        self,
        snapshots: list[SessionSnapshot],
        records: list[SessionRecord],
    ) -> dict[str, set[str]]:
        """Build grouped parent-ID sets for formal child existence checks."""

        grouped_snapshots: dict[str, list[SessionSnapshot]] = {}
        grouped_records: dict[str, list[SessionRecord]] = {}
        root_session_ids: set[str] = set()

        for snapshot in snapshots:
            grouped_snapshots.setdefault(snapshot.root_session_id, []).append(snapshot)
            root_session_ids.add(snapshot.root_session_id)
        for record in records:
            grouped_records.setdefault(record.root_session_id, []).append(record)
            root_session_ids.add(record.root_session_id)

        return {
            root_session_id: self._build_formal_child_parent_ids(
                grouped_snapshots.get(root_session_id, []),
                grouped_records.get(root_session_id, []),
            )
            for root_session_id in root_session_ids
        }

    def _build_formal_child_parent_ids(
        self,
        snapshots: list[SessionSnapshot],
        records: list[SessionRecord],
    ) -> set[str]:
        """Collect parent session IDs that already own a formal child session."""

        parent_session_ids: set[str] = set()
        for snapshot in snapshots:
            if not self._is_formal_session(snapshot.session_kind):
                continue
            if snapshot.parent_session_id is not None:
                parent_session_ids.add(snapshot.parent_session_id)
        for record in records:
            if not self._is_formal_session(record.session_kind):
                continue
            if record.parent_session_id is not None:
                parent_session_ids.add(record.parent_session_id)
        return parent_session_ids

    def _resolve_leaf_delete_state(
        self,
        snapshot: SessionSnapshot,
        formal_child_parent_ids: set[str],
    ) -> tuple[bool, str | None]:
        """Resolve whether one formal node can be deleted individually."""

        if snapshot.parent_session_id is None or snapshot.session_id == snapshot.root_session_id:
            return False, "ROOT version must be deleted at thread level."
        if snapshot.session_id in formal_child_parent_ids:
            return False, "Only leaf versions can be deleted individually."
        return True, None

    def _resolve_snapshot_formal_version_number(
        self,
        snapshot: SessionSnapshot,
        version_lookup: dict[str, int],
    ) -> int | None:
        """Resolve the current snapshot's stable formal version number."""

        if not self._is_formal_session(snapshot.session_kind):
            return None
        if snapshot.formal_version_number is not None:
            return snapshot.formal_version_number
        return version_lookup.get(snapshot.session_id)

    def _resolve_parent_formal_version_number(
        self,
        snapshot: SessionSnapshot,
        version_lookup: dict[str, int],
    ) -> int | None:
        """Resolve the direct parent's stable formal version number."""

        if snapshot.parent_session_id is None:
            return None
        return version_lookup.get(snapshot.parent_session_id)

    def _thread_matches_query(
        self,
        snapshots: list[SessionSnapshot],
        query: str,
    ) -> bool:
        """Return whether any formal session in one thread matches the local query."""

        return any(self._snapshot_matches_query(snapshot, query) for snapshot in snapshots)

    def _snapshot_matches_query(self, snapshot: SessionSnapshot, query: str) -> bool:
        """Return whether one formal snapshot contains the query in key local fields."""

        for part in self._iter_snapshot_search_parts(snapshot):
            normalized_part = self._normalize_history_query(part)
            if normalized_part is not None and query in normalized_part:
                return True
        return False

    def _iter_snapshot_search_parts(self, snapshot: SessionSnapshot) -> list[str]:
        """Collect the local text fields that should participate in history search."""

        parts: list[str] = [
            snapshot.archive_title,
            snapshot.original_content,
            snapshot.input_echo,
        ]
        if snapshot.follow_up_question is not None:
            parts.append(snapshot.follow_up_question)

        if snapshot.analysis is not None:
            parts.extend(
                [
                    snapshot.analysis.summary,
                    snapshot.analysis.feasibility,
                    snapshot.analysis.market,
                    *snapshot.analysis.knowledge_gaps,
                    *snapshot.analysis.resource_gaps,
                    *snapshot.analysis.team_requirements,
                    *snapshot.analysis.similar_projects,
                    *snapshot.analysis.mvp_roadmap,
                    *snapshot.analysis.long_term_roadmap,
                ]
            )

        if snapshot.refinement_result is not None:
            parts.extend(
                [
                    snapshot.refinement_result.question_summary,
                    snapshot.refinement_result.refinement_answer,
                    *[item.value for item in snapshot.refinement_result.affected_sections],
                    *snapshot.refinement_result.next_actions,
                ]
            )
            for update in snapshot.refinement_result.proposed_section_updates:
                parts.append(update.section_key.value)
                parts.append(update.change_summary)
                if update.updated_text is not None:
                    parts.append(update.updated_text)
                parts.extend(update.updated_items)

        return parts

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

    def _try_archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        """Run one archive attempt without letting adapter exceptions escape history flow."""

        try:
            return self._session_archiver.archive_session(payload)
        except Exception as exc:
            archived_at = datetime.now(UTC)
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error=f"Feishu archive exception: {exc}",
                archived_at=archived_at,
            )

    @staticmethod
    def _safe_archive_error(archive_error: str | None) -> str | None:
        """Convert external CLI details into concise, actionable UI feedback."""

        if archive_error is None:
            return None

        normalized_error = archive_error.lower()
        if "need_user_authorization" in normalized_error:
            return "飞书当前用户尚未完成文档创建授权，请完成 lark-cli 授权后再次尝试。"
        if "timed out" in normalized_error or "timeout" in normalized_error:
            return "飞书归档请求超时，请确认网络和飞书服务后再次尝试。"
        if "command is unavailable" in normalized_error:
            return "本机未能调用 lark-cli，请检查 CLI 安装和命令配置后再次尝试。"
        return "飞书归档未完成，请检查 lark-cli 登录状态和文档创建权限后再次尝试。"

    def _has_formal_child_session(
        self,
        *,
        parent_session_id: str,
        root_session_id: str,
    ) -> bool:
        """Return whether one formal session already has a formal child."""

        for snapshot in self._snapshots_for_root(root_session_id, include_drafts=False):
            if snapshot.parent_session_id == parent_session_id:
                return True
        for record in self._records_for_root(root_session_id, include_drafts=False):
            if record.parent_session_id == parent_session_id:
                return True
        return False

    def _list_attached_follow_up_draft_snapshots(
        self,
        *,
        parent_session_id: str,
        root_session_id: str,
    ) -> list[SessionSnapshot]:
        """List local follow-up draft snapshots that hang directly under one formal session."""

        return [
            snapshot
            for snapshot in self._session_snapshot_store.list_session_snapshots(
                session_kind=SessionKind.FOLLOW_UP_REFINEMENT
            )
            if snapshot.parent_session_id == parent_session_id
            and snapshot.root_session_id == root_session_id
        ]

    def _list_attached_follow_up_draft_records(
        self,
        *,
        parent_session_id: str,
        root_session_id: str,
    ) -> list[SessionRecord]:
        """List local follow-up draft records that hang directly under one formal session."""

        return [
            record
            for record in self._session_archive_store.list_session_records(
                session_kind=SessionKind.FOLLOW_UP_REFINEMENT
            )
            if record.parent_session_id == parent_session_id
            and record.root_session_id == root_session_id
        ]
