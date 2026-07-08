"""Session-domain models shared by storage, archive, and follow-up orchestration."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator, model_validator

from ideaos_agent.domain.analysis import IdeaAnalysis, RefinementResult


class SessionKind(StrEnum):
    """Supported session kinds in the v0.2.x session chain."""

    ANALYSIS = "analysis"
    FOLLOW_UP_REFINEMENT = "follow_up_refinement"
    FULL_PLAN_COMPOSED = "full_plan_composed"


class SessionClarificationRecord(BaseModel):
    """Serializable clarification item stored in snapshots and archive payloads."""

    question: str = Field(min_length=1, description="Clarification question.")
    answer: str = Field(min_length=1, description="User clarification answer.")

    @field_validator("question", "answer")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        """Reject blank-only clarification content."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Clarification content must not be blank.")
        return normalized


class SessionSnapshot(BaseModel):
    """Structured local snapshot used for follow-up reasoning and replay."""

    session_id: str = Field(min_length=1, description="Stable session identifier.")
    root_session_id: str = Field(
        min_length=1,
        description="Stable root session ID for the whole idea thread.",
    )
    parent_session_id: str | None = Field(
        default=None,
        description="Immediate parent session, if this session continues another one.",
    )
    session_kind: SessionKind = Field(
        default=SessionKind.ANALYSIS,
        description="Type of session snapshot.",
    )
    archive_title: str = Field(min_length=1, description="Semantic archive title for the session.")
    original_content: str = Field(
        min_length=1,
        description="Root/original raw idea carried through the session chain.",
    )
    input_echo: str = Field(
        min_length=1,
        description="Faithful echo of the current session input.",
    )
    clarifications: list[SessionClarificationRecord] = Field(
        default_factory=list,
        description="Clarifications used in this session.",
    )
    assumptions: list[str] = Field(default_factory=list, description="System assumptions.")
    open_questions: list[str] = Field(default_factory=list, description="Open questions.")
    follow_up_question: str | None = Field(
        default=None,
        description="Current follow-up question, when this is a follow-up session.",
    )
    analysis: IdeaAnalysis | None = Field(
        default=None,
        description="Full analysis snapshot for analysis/composed sessions.",
    )
    refinement_result: RefinementResult | None = Field(
        default=None,
        description="Refinement result for refinement/composed sessions.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Session creation time.",
    )
    completed_at: datetime = Field(description="Session completion time.")
    archived_at: datetime | None = Field(
        default=None,
        description="Final archive attempt time, if any.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Snapshot last update time.",
    )

    @field_validator(
        "session_id",
        "root_session_id",
        "parent_session_id",
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
            raise ValueError("Session snapshot text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_shape(self) -> "SessionSnapshot":
        """Keep snapshot payload shape aligned with the session kind."""

        if self.session_kind == SessionKind.ANALYSIS:
            if self.root_session_id != self.session_id:
                raise ValueError("Analysis snapshots must use session_id as root_session_id.")
            if self.parent_session_id is not None:
                raise ValueError("Analysis snapshots must not have parent_session_id.")
            if self.analysis is None:
                raise ValueError("Analysis snapshots must include analysis.")
            if self.follow_up_question is not None:
                raise ValueError("Analysis snapshots must not include follow_up_question.")
            if self.refinement_result is not None:
                raise ValueError("Analysis snapshots must not include refinement_result.")

        if self.session_kind == SessionKind.FOLLOW_UP_REFINEMENT:
            if self.parent_session_id is None:
                raise ValueError("Follow-up refinement snapshots require parent_session_id.")
            if self.follow_up_question is None:
                raise ValueError("Follow-up refinement snapshots require follow_up_question.")
            if self.analysis is not None:
                raise ValueError("Follow-up refinement snapshots must not include analysis.")
            if self.refinement_result is None:
                raise ValueError("Follow-up refinement snapshots require refinement_result.")

        if self.session_kind == SessionKind.FULL_PLAN_COMPOSED:
            if self.parent_session_id is None:
                raise ValueError("Composed plan snapshots require parent_session_id.")
            if self.follow_up_question is None:
                raise ValueError("Composed plan snapshots require follow_up_question.")
            if self.analysis is None:
                raise ValueError("Composed plan snapshots require analysis.")
            if self.refinement_result is None:
                raise ValueError("Composed plan snapshots require refinement_result.")

        return self


class SessionSnapshotStore(Protocol):
    """Storage contract for structured session snapshots."""

    def save_session_snapshot(self, snapshot: SessionSnapshot) -> SessionSnapshot:
        """Create or update a structured session snapshot."""

    def get_session_snapshot(self, session_id: str) -> SessionSnapshot | None:
        """Fetch a structured session snapshot by session ID."""

    def list_session_snapshots(
        self,
        *,
        limit: int | None = None,
        root_session_id: str | None = None,
        session_kind: SessionKind | None = None,
    ) -> list[SessionSnapshot]:
        """List structured session snapshots for history and thread queries."""
