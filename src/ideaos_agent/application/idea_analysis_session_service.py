"""Application-layer session orchestration for idea analysis responses."""

from datetime import UTC, datetime
from uuid import uuid4

from ideaos_agent.application.idea_analysis_service import IdeaAnalysisService
from ideaos_agent.domain.archive import (
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionArchiver,
    SessionArchiveStore,
    SessionClarificationRecord,
    SessionRecord,
)
from ideaos_agent.models import IdeaAnalysisLlmOutput, IdeaAnalysisResponse, IdeaInput


class IdeaAnalysisSessionService:
    """Attach session metadata and archive state around the core analysis flow."""

    def __init__(
        self,
        *,
        analysis_service: IdeaAnalysisService,
        session_archive_store: SessionArchiveStore,
        session_archiver: SessionArchiver,
    ) -> None:
        self._analysis_service = analysis_service
        self._session_archive_store = session_archive_store
        self._session_archiver = session_archiver

    def analyze(self, payload: IdeaInput) -> IdeaAnalysisResponse:
        """Analyze an idea and enrich the result with session/archive metadata."""

        session_id = resolve_session_id(payload.session_id)
        llm_output = self._analysis_service.analyze(payload)
        archive_status = determine_archive_status(llm_output)
        archive_url = None

        session_record = self.build_session_record(
            payload=payload,
            session_id=session_id,
            llm_output=llm_output,
            archive_status=archive_status,
            archive_url=archive_url,
        )
        persisted_record = self._session_archive_store.save_session_record(session_record)

        final_record = persisted_record
        if persisted_record.archive_status == ArchiveStatus.PENDING:
            archive_payload = self.build_archive_payload(
                payload=payload,
                session_record=persisted_record,
                llm_output=llm_output,
            )
            archive_result = self.try_archive_session(archive_payload)
            final_record = self.apply_archive_result(
                session_record=persisted_record,
                archive_result=archive_result,
            )
            final_record = self._session_archive_store.save_session_record(final_record)

        return IdeaAnalysisResponse(
            session_id=session_id,
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
        """Create the minimal typed session record used by later archive milestones."""

        completed_at = None
        if archive_status != ArchiveStatus.NOT_TRIGGERED:
            completed_at = datetime.now(UTC)

        return SessionRecord(
            session_id=session_id,
            original_content=payload.content,
            input_echo=llm_output.input_echo,
            clarification_count=len(payload.clarifications),
            archive_status=archive_status,
            archive_url=archive_url,
            completed_at=completed_at,
        )

    def build_archive_payload(
        self,
        *,
        payload: IdeaInput,
        session_record: SessionRecord,
        llm_output: IdeaAnalysisLlmOutput,
    ) -> SessionArchivePayload:
        """Build the full archive payload for external archive adapters."""

        if llm_output.analysis is None:
            raise ValueError("完成态归档要求存在完整 analysis。")
        if session_record.completed_at is None:
            raise ValueError("完成态归档要求 session_record.completed_at 已存在。")

        return SessionArchivePayload(
            session_id=session_record.session_id,
            archive_title=llm_output.archive_title,
            original_content=payload.content,
            input_echo=llm_output.input_echo,
            clarifications=[
                SessionClarificationRecord(question=item.question, answer=item.answer)
                for item in payload.clarifications
            ],
            assumptions=llm_output.assumptions,
            open_questions=llm_output.open_questions,
            summary=llm_output.analysis.summary,
            feasibility=llm_output.analysis.feasibility,
            market=llm_output.analysis.market,
            knowledge_gaps=llm_output.analysis.knowledge_gaps,
            resource_gaps=llm_output.analysis.resource_gaps,
            team_requirements=llm_output.analysis.team_requirements,
            similar_projects=llm_output.analysis.similar_projects,
            mvp_roadmap=llm_output.analysis.mvp_roadmap,
            long_term_roadmap=llm_output.analysis.long_term_roadmap,
            created_at=session_record.created_at,
            completed_at=session_record.completed_at,
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
                archive_error=f"飞书归档异常：{exc}",
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
