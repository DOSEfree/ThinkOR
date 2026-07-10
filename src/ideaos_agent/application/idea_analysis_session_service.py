"""Application-layer session orchestration for root idea analysis responses."""

from datetime import UTC, datetime
from uuid import uuid4

from ideaos_agent.application.idea_analysis_service import IdeaAnalysisService
from ideaos_agent.domain.archive import (
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionArchiver,
    SessionArchiveStore,
    SessionRecord,
)
from ideaos_agent.domain.session import (
    SessionClarificationRecord,
    SessionKind,
    SessionSnapshot,
    SessionSnapshotStore,
)
from ideaos_agent.models import IdeaAnalysisLlmOutput, IdeaAnalysisResponse, IdeaInput


class IdeaAnalysisSessionService:
    """Attach session metadata, snapshots, and archive state around root analysis."""

    def __init__(
        self,
        *,
        analysis_service: IdeaAnalysisService,
        session_archive_store: SessionArchiveStore,
        session_snapshot_store: SessionSnapshotStore,
        session_archiver: SessionArchiver,
    ) -> None:
        self._analysis_service = analysis_service
        self._session_archive_store = session_archive_store
        self._session_snapshot_store = session_snapshot_store
        self._session_archiver = session_archiver

    def analyze(self, payload: IdeaInput) -> IdeaAnalysisResponse:
        """Analyze an idea and enrich the result with session/archive metadata."""

        session_id = resolve_session_id(payload.session_id)
        llm_output = self._analysis_service.analyze(payload)
        archive_status = determine_archive_status(llm_output)

        session_record = self.build_session_record(
            payload=payload,
            session_id=session_id,
            llm_output=llm_output,
            archive_status=archive_status,
            archive_url=None,
        )
        persisted_record = self._session_archive_store.save_session_record(session_record)

        final_record = persisted_record
        if persisted_record.archive_status == ArchiveStatus.PENDING:
            snapshot = self.build_completed_snapshot(
                payload=payload,
                session_record=persisted_record,
                llm_output=llm_output,
            )
            persisted_snapshot = self._session_snapshot_store.save_session_snapshot(snapshot)

            archive_payload = self.build_archive_payload(
                session_record=persisted_record,
                snapshot=persisted_snapshot,
            )
            archive_result = self.try_archive_session(archive_payload)
            final_record = self.apply_archive_result(
                session_record=persisted_record,
                archive_result=archive_result,
            )
            final_record = self._session_archive_store.save_session_record(final_record)
            updated_snapshot = persisted_snapshot.model_copy(
                update={
                    "archived_at": archive_result.archived_at,
                    "updated_at": archive_result.archived_at,
                }
            )
            self._session_snapshot_store.save_session_snapshot(updated_snapshot)

        return IdeaAnalysisResponse(
            session_id=session_id,
            root_session_id=session_id,
            session_kind=SessionKind.ANALYSIS,
            parent_session_id=None,
            formal_version_number=1,
            parent_formal_version_number=None,
            archive_status=final_record.archive_status,
            archive_url=final_record.archive_url,
            **llm_output.model_dump(),
        )

    def build_session_record(
        self,
        *,
        payload: IdeaInput,
        session_id: str,
        llm_output: IdeaAnalysisLlmOutput,
        archive_status: ArchiveStatus,
        archive_url: str | None,
    ) -> SessionRecord:
        """Create the minimal typed session record used by archive milestones."""

        completed_at = None
        if archive_status != ArchiveStatus.NOT_TRIGGERED:
            completed_at = datetime.now(UTC)

        return SessionRecord(
            session_id=session_id,
            root_session_id=session_id,
            parent_session_id=None,
            session_kind=SessionKind.ANALYSIS,
            formal_version_number=1,
            original_content=payload.content,
            input_echo=llm_output.input_echo,
            clarification_count=len(payload.clarifications),
            archive_status=archive_status,
            archive_url=archive_url,
            completed_at=completed_at,
        )

    def build_completed_snapshot(
        self,
        *,
        payload: IdeaInput,
        session_record: SessionRecord,
        llm_output: IdeaAnalysisLlmOutput,
    ) -> SessionSnapshot:
        """Build the structured snapshot needed for follow-up reasoning."""

        if llm_output.analysis is None:
            raise ValueError("Completed root analysis snapshots require analysis.")
        if session_record.completed_at is None:
            raise ValueError("Completed root analysis snapshots require completed_at.")

        return SessionSnapshot(
            session_id=session_record.session_id,
            root_session_id=session_record.session_id,
            parent_session_id=None,
            session_kind=SessionKind.ANALYSIS,
            formal_version_number=1,
            archive_title=llm_output.archive_title,
            original_content=payload.content,
            input_echo=llm_output.input_echo,
            clarifications=[
                SessionClarificationRecord(question=item.question, answer=item.answer)
                for item in payload.clarifications
            ],
            assumptions=llm_output.assumptions,
            open_questions=llm_output.open_questions,
            analysis=llm_output.analysis,
            refinement_result=None,
            completed_at=session_record.completed_at,
            updated_at=session_record.completed_at,
        )

    def build_archive_payload(
        self,
        *,
        session_record: SessionRecord,
        snapshot: SessionSnapshot,
    ) -> SessionArchivePayload:
        """Build the external archive payload from the completed root snapshot."""

        return SessionArchivePayload(
            session_id=session_record.session_id,
            root_session_id=session_record.root_session_id,
            root_archive_url=session_record.archive_url,
            parent_session_id=None,
            parent_archive_url=None,
            session_kind=SessionKind.ANALYSIS,
            archive_title=snapshot.archive_title,
            original_content=snapshot.original_content,
            input_echo=snapshot.input_echo,
            clarifications=snapshot.clarifications,
            assumptions=snapshot.assumptions,
            open_questions=snapshot.open_questions,
            follow_up_question=None,
            analysis=snapshot.analysis,
            refinement_result=None,
            created_at=snapshot.created_at,
            completed_at=snapshot.completed_at,
        )

    def try_archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        """Archive a completed session without letting failures break the main flow."""

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

    def apply_archive_result(
        self,
        *,
        session_record: SessionRecord,
        archive_result: ArchiveResult,
    ) -> SessionRecord:
        """Apply one archive attempt result back to the persisted session record."""

        return session_record.model_copy(
            update={
                "archive_status": archive_result.archive_status,
                "archive_url": archive_result.archive_url,
                "archive_error": archive_result.archive_error,
                "archived_at": archive_result.archived_at,
                "updated_at": archive_result.archived_at,
            }
        )


def resolve_session_id(provided_session_id: str | None) -> str:
    """Reuse the provided session ID or create a new one for first-time requests."""

    if provided_session_id is not None:
        return provided_session_id
    return f"sess_{uuid4().hex}"


def determine_archive_status(llm_output: IdeaAnalysisLlmOutput) -> ArchiveStatus:
    """Map the current analysis state to the archive lifecycle state."""

    if llm_output.needs_clarification:
        return ArchiveStatus.NOT_TRIGGERED
    return ArchiveStatus.PENDING
