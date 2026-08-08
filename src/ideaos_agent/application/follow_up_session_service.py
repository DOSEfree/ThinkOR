"""Application-layer orchestration for v0.2.5 follow-up refinement flows."""

from datetime import UTC, datetime, timedelta

from ideaos_agent.application.idea_analysis_session_service import resolve_session_id
from ideaos_agent.config import AppSettings
from ideaos_agent.domain.analysis import apply_section_updates
from ideaos_agent.domain.archive import (
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionArchiver,
    SessionArchiveStore,
    SessionRecord,
)
from ideaos_agent.domain.errors import SessionNotFoundError, SessionStateError
from ideaos_agent.domain.session import (
    SessionClarificationRecord,
    SessionKind,
    SessionSnapshot,
    SessionSnapshotStore,
)
from ideaos_agent.infrastructure.llm.client import LlmClient
from ideaos_agent.models import (
    ComposedPlanResponse,
    ComposeFullPlanInput,
    FollowUpInput,
    FollowUpLlmOutput,
    FollowUpResponse,
)
from ideaos_agent.prompts.follow_up import FollowUpPromptBuilder


class FollowUpSessionService:
    """Coordinate follow-up refinement, composition, snapshots, and archive behavior."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        llm_client: LlmClient,
        prompt_builder: FollowUpPromptBuilder,
        session_archive_store: SessionArchiveStore,
        session_snapshot_store: SessionSnapshotStore,
        session_archiver: SessionArchiver,
    ) -> None:
        self._settings = settings
        self._llm_client = llm_client
        self._prompt_builder = prompt_builder
        self._session_archive_store = session_archive_store
        self._session_snapshot_store = session_snapshot_store
        self._session_archiver = session_archiver

    def refine(self, payload: FollowUpInput) -> FollowUpResponse:
        """Generate one bounded follow-up refinement result."""

        self._prune_expired_drafts()
        parent_snapshot = self._require_parent_snapshot(payload.parent_session_id)
        parent_formal_version_number = self._resolve_formal_version_number(parent_snapshot)
        if parent_snapshot.analysis is None:
            raise SessionStateError(
                "Follow-up parent session must contain a full analysis snapshot."
            )

        reusable_draft = self._find_active_draft(parent_snapshot.session_id)
        requested_session_id = payload.session_id
        if requested_session_id is None and reusable_draft is not None:
            requested_session_id = reusable_draft.session_id

        session_id = resolve_session_id(requested_session_id)
        llm_output = self._generate_refinement_output(parent_snapshot, payload)
        archive_status = determine_follow_up_archive_status(llm_output)
        completed_at = datetime.now(UTC) if llm_output.needs_clarification is False else None

        session_record = SessionRecord(
            session_id=session_id,
            root_session_id=parent_snapshot.root_session_id,
            parent_session_id=parent_snapshot.session_id,
            session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
            formal_version_number=None,
            original_content=parent_snapshot.original_content,
            input_echo=llm_output.input_echo,
            intent=parent_snapshot.intent,
            clarification_count=len(payload.clarifications),
            archive_status=archive_status,
            archive_url=None,
            completed_at=completed_at,
        )
        persisted_record = self._session_archive_store.save_session_record(session_record)

        final_record = persisted_record
        if llm_output.refinement_result is None:
            self._session_snapshot_store.delete_session_snapshot(session_id)
        else:
            if persisted_record.completed_at is None:
                raise ValueError("Completed refinement sessions require completed_at.")

            snapshot = SessionSnapshot(
                session_id=session_id,
                root_session_id=parent_snapshot.root_session_id,
                parent_session_id=parent_snapshot.session_id,
                session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
                formal_version_number=None,
                archive_title=llm_output.archive_title,
                original_content=parent_snapshot.original_content,
                input_echo=llm_output.input_echo,
                intent=parent_snapshot.intent,
                clarifications=[
                    SessionClarificationRecord(question=item.question, answer=item.answer)
                    for item in payload.clarifications
                ],
                assumptions=llm_output.assumptions,
                open_questions=llm_output.open_questions,
                follow_up_question=payload.question,
                analysis=None,
                refinement_result=llm_output.refinement_result,
                completed_at=persisted_record.completed_at,
                updated_at=persisted_record.completed_at,
            )
            self._session_snapshot_store.save_session_snapshot(snapshot)

        return FollowUpResponse(
            session_id=session_id,
            root_session_id=parent_snapshot.root_session_id,
            parent_session_id=parent_snapshot.session_id,
            formal_version_number=None,
            parent_formal_version_number=parent_formal_version_number,
            session_kind=SessionKind.FOLLOW_UP_REFINEMENT,
            archive_status=final_record.archive_status,
            archive_url=final_record.archive_url,
            intent=parent_snapshot.intent,
            **llm_output.model_dump(),
        )

    def compose_full_plan(self, payload: ComposeFullPlanInput) -> ComposedPlanResponse:
        """Compose a new full analysis by applying one refinement to its parent analysis."""

        self._prune_expired_drafts()
        refinement_snapshot = self._require_snapshot(payload.parent_session_id)
        if refinement_snapshot.session_kind != SessionKind.FOLLOW_UP_REFINEMENT:
            raise SessionStateError("Compose full plan requires a follow-up refinement session.")
        if refinement_snapshot.refinement_result is None:
            raise SessionStateError("Compose full plan requires a completed refinement result.")
        if refinement_snapshot.parent_session_id is None:
            raise SessionStateError("Refinement sessions must point to a parent analysis session.")

        parent_snapshot = self._require_snapshot(refinement_snapshot.parent_session_id)
        if parent_snapshot.analysis is None:
            raise SessionStateError(
                "Parent analysis session must include a full analysis snapshot."
            )
        parent_formal_version_number = self._resolve_formal_version_number(parent_snapshot)

        composed_analysis = apply_section_updates(
            parent_snapshot.analysis,
            refinement_snapshot.refinement_result.proposed_section_updates,
        )
        session_id = resolve_session_id(None)
        completed_at = datetime.now(UTC)
        formal_version_number = self._next_formal_version_number(
            refinement_snapshot.root_session_id
        )

        session_record = SessionRecord(
            session_id=session_id,
            root_session_id=refinement_snapshot.root_session_id,
            parent_session_id=parent_snapshot.session_id,
            session_kind=SessionKind.FULL_PLAN_COMPOSED,
            formal_version_number=formal_version_number,
            original_content=parent_snapshot.original_content,
            input_echo=refinement_snapshot.input_echo,
            intent=parent_snapshot.intent,
            clarification_count=len(refinement_snapshot.clarifications),
            archive_status=ArchiveStatus.PENDING,
            archive_url=None,
            completed_at=completed_at,
        )
        persisted_record = self._session_archive_store.save_session_record(session_record)

        snapshot = SessionSnapshot(
            session_id=session_id,
            root_session_id=refinement_snapshot.root_session_id,
            parent_session_id=parent_snapshot.session_id,
            session_kind=SessionKind.FULL_PLAN_COMPOSED,
            formal_version_number=formal_version_number,
            archive_title=refinement_snapshot.archive_title,
            original_content=parent_snapshot.original_content,
            input_echo=refinement_snapshot.input_echo,
            intent=parent_snapshot.intent,
            clarifications=refinement_snapshot.clarifications,
            assumptions=refinement_snapshot.assumptions,
            open_questions=refinement_snapshot.open_questions,
            follow_up_question=refinement_snapshot.follow_up_question,
            analysis=composed_analysis,
            refinement_result=refinement_snapshot.refinement_result,
            completed_at=completed_at,
            updated_at=completed_at,
        )
        persisted_snapshot = self._session_snapshot_store.save_session_snapshot(snapshot)

        parent_record = self._session_archive_store.get_session_record(parent_snapshot.session_id)
        root_record = self._session_archive_store.get_session_record(
            refinement_snapshot.root_session_id
        )
        archive_payload = SessionArchivePayload(
            session_id=session_id,
            root_session_id=refinement_snapshot.root_session_id,
            root_archive_url=(
                root_record.archive_url if root_record is not None else None
            ),
            parent_session_id=parent_snapshot.session_id,
            parent_archive_url=(
                parent_record.archive_url if parent_record is not None else None
            ),
            session_kind=SessionKind.FULL_PLAN_COMPOSED,
            archive_title=persisted_snapshot.archive_title,
            original_content=persisted_snapshot.original_content,
            input_echo=persisted_snapshot.input_echo,
            intent=persisted_snapshot.intent,
            clarifications=persisted_snapshot.clarifications,
            assumptions=persisted_snapshot.assumptions,
            open_questions=persisted_snapshot.open_questions,
            follow_up_question=persisted_snapshot.follow_up_question,
            analysis=persisted_snapshot.analysis,
            refinement_result=persisted_snapshot.refinement_result,
            created_at=persisted_snapshot.created_at,
            completed_at=persisted_snapshot.completed_at,
        )
        archive_result = self._try_archive_session(archive_payload)
        final_record = self._apply_archive_result(persisted_record, archive_result)
        final_record = self._session_archive_store.save_session_record(final_record)
        updated_snapshot = persisted_snapshot.model_copy(
            update={
                "archived_at": archive_result.archived_at,
                "updated_at": archive_result.archived_at,
            }
        )
        self._session_snapshot_store.save_session_snapshot(updated_snapshot)
        self._session_snapshot_store.delete_session_snapshot(refinement_snapshot.session_id)
        self._session_archive_store.delete_session_record(refinement_snapshot.session_id)

        return ComposedPlanResponse(
            session_id=session_id,
            root_session_id=refinement_snapshot.root_session_id,
            session_kind=SessionKind.FULL_PLAN_COMPOSED,
            parent_session_id=parent_snapshot.session_id,
            formal_version_number=formal_version_number,
            parent_formal_version_number=parent_formal_version_number,
            archive_status=final_record.archive_status,
            archive_url=final_record.archive_url,
            archive_title=persisted_snapshot.archive_title,
            input_echo=persisted_snapshot.input_echo,
            intent=persisted_snapshot.intent,
            needs_clarification=False,
            assumptions=persisted_snapshot.assumptions,
            open_questions=persisted_snapshot.open_questions,
            analysis=composed_analysis,
            refinement_result=refinement_snapshot.refinement_result,
        )

    def _generate_refinement_output(
        self,
        parent_snapshot: SessionSnapshot,
        payload: FollowUpInput,
    ) -> FollowUpLlmOutput:
        """Call the LLM for a follow-up refinement result."""

        question_size = len(payload.question.strip())
        clarification_size = sum(
            len(item.question.strip()) + len(item.answer.strip()) for item in payload.clarifications
        )
        if question_size + clarification_size > self._settings.max_input_chars:
            from ideaos_agent.domain.errors import IdeaInputTooLongError

            raise IdeaInputTooLongError(
                f"Follow-up input exceeds the limit of {self._settings.max_input_chars} characters."
            )

        prompt = self._prompt_builder.build_refinement_prompt(
            parent_snapshot=parent_snapshot,
            question=payload.question.strip(),
            clarifications=[
                SessionClarificationRecord(question=item.question, answer=item.answer)
                for item in payload.clarifications
            ],
        )
        from ideaos_agent.infrastructure.llm.parsing import parse_follow_up_response

        raw_output = self._llm_client.generate_text(
            system_prompt=self._prompt_builder.system_prompt,
            user_prompt=prompt,
        )
        return parse_follow_up_response(raw_output)

    def _require_parent_snapshot(self, session_id: str) -> SessionSnapshot:
        """Require a snapshot that can serve as a follow-up parent."""

        snapshot = self._require_snapshot(session_id)
        if snapshot.session_kind == SessionKind.FOLLOW_UP_REFINEMENT:
            raise SessionStateError(
                "Follow-up refinement sessions cannot be refined again before compose."
            )
        if snapshot.analysis is None:
            raise SessionStateError("Follow-up parent must include a full analysis snapshot.")
        return snapshot

    def _require_snapshot(self, session_id: str) -> SessionSnapshot:
        """Fetch one snapshot or raise a domain error."""

        snapshot = self._session_snapshot_store.get_session_snapshot(session_id)
        if snapshot is None:
            raise SessionNotFoundError(f"Session snapshot not found: {session_id}")
        return snapshot

    def _resolve_formal_version_number(self, snapshot: SessionSnapshot) -> int | None:
        """Resolve one stable formal version number with legacy fallback."""

        if snapshot.session_kind == SessionKind.FOLLOW_UP_REFINEMENT:
            return None
        if snapshot.formal_version_number is not None:
            return snapshot.formal_version_number
        return self._build_formal_version_lookup(snapshot.root_session_id).get(snapshot.session_id)

    def _next_formal_version_number(self, root_session_id: str) -> int:
        """Return the next stable formal version number for one root thread."""

        version_lookup = self._build_formal_version_lookup(root_session_id)
        if not version_lookup:
            return 1
        return max(version_lookup.values()) + 1

    def _build_formal_version_lookup(self, root_session_id: str) -> dict[str, int]:
        """Build a stable formal version-number lookup for one root thread."""

        snapshots = [
            snapshot
            for snapshot in self._session_snapshot_store.list_session_snapshots(
                root_session_id=root_session_id
            )
            if snapshot.session_kind in {SessionKind.ANALYSIS, SessionKind.FULL_PLAN_COMPOSED}
        ]
        snapshots.sort(key=lambda item: (item.created_at, item.session_id))

        used_numbers = {
            snapshot.formal_version_number
            for snapshot in snapshots
            if snapshot.formal_version_number is not None
        }
        next_number = 1
        resolved: dict[str, int] = {}
        for snapshot in snapshots:
            if snapshot.formal_version_number is not None:
                resolved[snapshot.session_id] = snapshot.formal_version_number
                continue
            while next_number in used_numbers:
                next_number += 1
            resolved[snapshot.session_id] = next_number
            used_numbers.add(next_number)
            next_number += 1
        return resolved

    def _find_active_draft(self, parent_session_id: str) -> SessionSnapshot | None:
        """Return the latest non-expired draft cached under one formal parent session."""

        candidates = [
            snapshot
            for snapshot in self._session_snapshot_store.list_session_snapshots(
                session_kind=SessionKind.FOLLOW_UP_REFINEMENT
            )
            if snapshot.parent_session_id == parent_session_id
            and snapshot.updated_at >= self._draft_retention_cutoff()
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.updated_at, reverse=True)
        return candidates[0]

    def _prune_expired_drafts(self) -> None:
        """Delete cached follow-up drafts that exceeded the retention window."""

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
        """Return the oldest timestamp still kept as a recoverable local draft."""

        return datetime.now(UTC) - timedelta(
            days=max(self._settings.follow_up_draft_retention_days, 0)
        )

    def _try_archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        """Archive one completed follow-up/composed session without blocking the main result."""

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

    def _apply_archive_result(
        self,
        session_record: SessionRecord,
        archive_result: ArchiveResult,
    ) -> SessionRecord:
        """Apply one archive result back to the persisted session index record."""

        return session_record.model_copy(
            update={
                "archive_status": archive_result.archive_status,
                "archive_url": archive_result.archive_url,
                "archive_error": archive_result.archive_error,
                "archived_at": archive_result.archived_at,
                "updated_at": archive_result.archived_at,
            }
        )


def determine_follow_up_archive_status(llm_output: FollowUpLlmOutput) -> ArchiveStatus:
    """Keep follow-up refinement outputs local until the user confirms compose."""

    del llm_output
    return ArchiveStatus.NOT_TRIGGERED
