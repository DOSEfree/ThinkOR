"""Archive-related domain models for session tracking and Feishu export."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator, model_validator

from ideaos_agent.domain.analysis import IdeaAnalysis, RefinementResult
from ideaos_agent.domain.session import SessionClarificationRecord, SessionKind


class ArchiveStatus(StrEnum):
    """Archive lifecycle states for a single session."""

    NOT_TRIGGERED = "not_triggered"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SessionRecord(BaseModel):
    """Minimal local session index model for status tracking."""

    session_id: str = Field(min_length=1, description="Stable session ID.")
    root_session_id: str = Field(
        min_length=1,
        description="Stable root session ID for the whole idea thread.",
    )
    parent_session_id: str | None = Field(
        default=None,
        description="Immediate parent session, if any.",
    )
    session_kind: SessionKind = Field(
        default=SessionKind.ANALYSIS,
        description="Kind of session represented by the index record.",
    )
    original_content: str = Field(min_length=1, description="Raw/root idea content.")
    input_echo: str = Field(min_length=1, description="Faithful input echo.")
    clarification_count: int = Field(
        ge=0,
        description="Clarification count carried in the current request.",
    )
    archive_status: ArchiveStatus = Field(description="Archive state for the session.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL when the archive succeeds.",
    )
    archive_error: str | None = Field(
        default=None,
        description="Minimal archive error detail when archiving fails.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Session record creation time.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Time when the session reached a completed result.",
    )
    archived_at: datetime | None = Field(
        default=None,
        description="Time when the archive attempt finished.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update time.",
    )

    @field_validator(
        "session_id",
        "root_session_id",
        "parent_session_id",
        "original_content",
        "input_echo",
        "archive_error",
        "archive_url",
    )
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session record text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_archive_consistency(self) -> "SessionRecord":
        """Keep persisted archive state internally consistent."""

        if self.session_kind == SessionKind.ANALYSIS:
            if self.parent_session_id is not None:
                raise ValueError("Analysis session records must not include parent_session_id.")
            if self.root_session_id != self.session_id:
                raise ValueError("Analysis session records must use session_id as root_session_id.")

        if self.session_kind != SessionKind.ANALYSIS:
            if self.parent_session_id is None:
                raise ValueError("Follow-up/composed session records require parent_session_id.")

        if self.archive_status == ArchiveStatus.NOT_TRIGGERED:
            if self.completed_at is not None:
                raise ValueError("NOT_TRIGGERED sessions must not include completed_at.")
            if self.archived_at is not None:
                raise ValueError("NOT_TRIGGERED sessions must not include archived_at.")
            if self.archive_url is not None:
                raise ValueError("NOT_TRIGGERED sessions must not include archive_url.")

        if self.archive_status == ArchiveStatus.PENDING:
            if self.completed_at is None:
                raise ValueError("PENDING sessions must include completed_at.")
            if self.archived_at is not None:
                raise ValueError("PENDING sessions must not include archived_at.")
            if self.archive_url is not None:
                raise ValueError("PENDING sessions must not include archive_url.")

        if self.archive_status == ArchiveStatus.SUCCEEDED:
            if self.completed_at is None:
                raise ValueError("SUCCEEDED sessions must include completed_at.")
            if self.archived_at is None:
                raise ValueError("SUCCEEDED sessions must include archived_at.")
            if self.archive_url is None:
                raise ValueError("SUCCEEDED sessions must include archive_url.")

        if self.archive_status == ArchiveStatus.FAILED:
            if self.completed_at is None:
                raise ValueError("FAILED sessions must include completed_at.")
            if self.archived_at is None:
                raise ValueError("FAILED sessions must include archived_at.")
            if self.archive_url is not None:
                raise ValueError("FAILED sessions must not include archive_url.")

        return self


class SessionArchivePayload(BaseModel):
    """Complete archive payload passed to an archive adapter."""

    session_id: str = Field(min_length=1, description="Session ID.")
    root_session_id: str = Field(
        min_length=1,
        description="Stable root session ID for the whole idea thread.",
    )
    root_archive_url: str | None = Field(
        default=None,
        description="Root archive URL, if the root session was archived successfully.",
    )
    parent_session_id: str | None = Field(
        default=None,
        description="Immediate parent session ID, if any.",
    )
    parent_archive_url: str | None = Field(
        default=None,
        description="Parent archive URL, if available.",
    )
    session_kind: SessionKind = Field(
        default=SessionKind.ANALYSIS,
        description="Session kind for the archive document.",
    )
    archive_title: str = Field(min_length=1, description="Semantic title portion.")
    original_content: str = Field(min_length=1, description="Root/original idea.")
    input_echo: str = Field(min_length=1, description="Faithful current input echo.")
    clarifications: list[SessionClarificationRecord] = Field(
        default_factory=list,
        description="Clarification records for the current session.",
    )
    assumptions: list[str] = Field(default_factory=list, description="System assumptions.")
    open_questions: list[str] = Field(default_factory=list, description="Open questions.")
    follow_up_question: str | None = Field(
        default=None,
        description="Follow-up question, when this is a follow-up session.",
    )
    analysis: IdeaAnalysis | None = Field(
        default=None,
        description="Full analysis when available.",
    )
    refinement_result: RefinementResult | None = Field(
        default=None,
        description="Refinement result when available.",
    )
    created_at: datetime = Field(description="Session creation time.")
    completed_at: datetime = Field(description="Session completion time.")

    @field_validator(
        "session_id",
        "root_session_id",
        "root_archive_url",
        "parent_session_id",
        "parent_archive_url",
        "archive_title",
        "original_content",
        "input_echo",
        "follow_up_question",
    )
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Archive payload text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_shape(self) -> "SessionArchivePayload":
        """Keep archive payload shape aligned with the session kind."""

        if self.session_kind == SessionKind.ANALYSIS:
            if self.root_session_id != self.session_id:
                raise ValueError("Analysis archives must use session_id as root_session_id.")
            if self.parent_session_id is not None:
                raise ValueError("Analysis archives must not include parent_session_id.")
            if self.follow_up_question is not None:
                raise ValueError("Analysis archives must not include follow_up_question.")
            if self.analysis is None:
                raise ValueError("Analysis archives must include analysis.")
            if self.refinement_result is not None:
                raise ValueError("Analysis archives must not include refinement_result.")

        if self.session_kind == SessionKind.FOLLOW_UP_REFINEMENT:
            if self.parent_session_id is None:
                raise ValueError("Refinement archives require parent_session_id.")
            if self.follow_up_question is None:
                raise ValueError("Refinement archives require follow_up_question.")
            if self.analysis is not None:
                raise ValueError("Refinement archives must not include analysis.")
            if self.refinement_result is None:
                raise ValueError("Refinement archives require refinement_result.")

        if self.session_kind == SessionKind.FULL_PLAN_COMPOSED:
            if self.parent_session_id is None:
                raise ValueError("Composed archives require parent_session_id.")
            if self.follow_up_question is None:
                raise ValueError("Composed archives require follow_up_question.")
            if self.analysis is None:
                raise ValueError("Composed archives require analysis.")
            if self.refinement_result is None:
                raise ValueError("Composed archives require refinement_result.")

        return self


class ArchiveResult(BaseModel):
    """Result returned by an archive adapter after one archive attempt."""

    archive_status: ArchiveStatus = Field(description="Final archive status.")
    archive_url: str | None = Field(default=None, description="Archive URL on success.")
    archive_error: str | None = Field(default=None, description="Archive error on failure.")
    archived_at: datetime = Field(description="When the archive attempt finished.")

    @field_validator("archive_url", "archive_error")
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Archive result text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_result_consistency(self) -> "ArchiveResult":
        """Keep archive attempt results internally consistent."""

        if self.archive_status == ArchiveStatus.SUCCEEDED:
            if self.archive_url is None:
                raise ValueError("archive_url is required for SUCCEEDED archive results.")
            if self.archive_error is not None:
                raise ValueError("archive_error is not allowed for SUCCEEDED archive results.")
        elif self.archive_status == ArchiveStatus.FAILED:
            if self.archive_url is not None:
                raise ValueError("archive_url is not allowed for FAILED archive results.")
        else:
            raise ValueError("ArchiveResult only supports succeeded or failed states.")

        return self


class SessionArchiveStore(Protocol):
    """Storage contract for the minimal session archive index."""

    def save_session_record(self, record: SessionRecord) -> SessionRecord:
        """Create or update the minimal session index record."""

    def get_session_record(self, session_id: str) -> SessionRecord | None:
        """Fetch one session index record by session ID."""

    def list_session_records(
        self,
        *,
        limit: int | None = None,
        root_session_id: str | None = None,
        session_kind: SessionKind | None = None,
    ) -> list[SessionRecord]:
        """List session index records for history and thread queries."""


class SessionArchiver(Protocol):
    """Archive adapter contract for external archive targets."""

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        """Archive one completed session and return the final attempt result."""
