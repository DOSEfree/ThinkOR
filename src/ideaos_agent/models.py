"""Typed API-facing models for ThinkOR requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from ideaos_agent.domain.analysis import IdeaAnalysis, RefinementResult
from ideaos_agent.domain.archive import ArchiveStatus
from ideaos_agent.domain.session import SessionKind


class ClarificationAnswer(BaseModel):
    """One user-provided clarification answer."""

    question: str = Field(min_length=1, description="Clarification question.")
    answer: str = Field(min_length=1, description="Clarification answer.")

    @field_validator("question", "answer")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        """Reject blank-only clarification content."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Clarification fields must not be blank.")
        return normalized


class IdeaInput(BaseModel):
    """Root analysis input."""

    session_id: str | None = Field(
        default=None,
        description="Stable session ID for one clarification-bound analysis flow.",
    )
    content: str = Field(min_length=1, description="Raw idea input.")
    clarifications: list[ClarificationAnswer] = Field(
        default_factory=list,
        description="Optional one-round clarification answers.",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        """Reject blank-only content."""

        if not value.strip():
            raise ValueError("Idea content must not be blank.")
        return value

    @field_validator("session_id")
    @classmethod
    def validate_session_id_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only session identifiers while allowing null."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("session_id must not be blank.")
        return normalized


class IdeaAnalysisLlmOutput(BaseModel):
    """LLM wrapper output before session/archive metadata is attached."""

    archive_title: str = Field(
        min_length=1,
        description="Short semantic title for archive naming.",
    )
    input_echo: str = Field(
        min_length=1,
        description="Faithful restatement of the raw idea only.",
    )
    needs_clarification: bool = Field(
        description="Whether the current input still needs clarification.",
    )
    assumptions: list[str] = Field(default_factory=list, description="System assumptions.")
    open_questions: list[str] = Field(default_factory=list, description="Open questions.")
    analysis: IdeaAnalysis | None = Field(
        default=None,
        description="Full analysis when clarification is no longer needed.",
    )

    @field_validator("archive_title", "input_echo")
    @classmethod
    def validate_required_text_not_blank(cls, value: str) -> str:
        """Reject blank-only required text fields."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("archive_title and input_echo must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_consistency(self) -> "IdeaAnalysisLlmOutput":
        """Keep the wrapper shape internally consistent."""

        if len(self.open_questions) > 3:
            raise ValueError("open_questions must contain at most 3 items.")

        if self.needs_clarification:
            if self.analysis is not None:
                raise ValueError("analysis must be null when clarification is needed.")
            if not 2 <= len(self.open_questions) <= 3:
                raise ValueError(
                    "open_questions must contain 2 to 3 items when clarification is needed."
                )
        else:
            if self.analysis is None:
                raise ValueError("analysis must exist when clarification is not needed.")

        return self


class BaseAnalysisResponse(IdeaAnalysisLlmOutput):
    """Shared response fields for full-analysis-shaped API responses."""

    session_id: str = Field(min_length=1, description="Stable session ID.")
    root_session_id: str = Field(
        min_length=1,
        description="Stable root session ID for the whole idea thread.",
    )
    session_kind: SessionKind = Field(description="Session kind for the current response.")
    parent_session_id: str | None = Field(
        default=None,
        description="Parent session ID. Root analyses do not have one.",
    )
    formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description="Stable formal version number inside the root thread.",
    )
    parent_formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description="Stable formal version number of the direct parent session, if any.",
    )
    archive_status: ArchiveStatus = Field(description="Current archive status.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL after a successful archive attempt.",
    )
    archive_error: str | None = Field(
        default=None,
        description="Safe, user-actionable error detail after a failed archive attempt.",
    )

    @field_validator("session_id", "root_session_id", "parent_session_id", "archive_url")
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Response text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_archive_metadata(self) -> "BaseAnalysisResponse":
        """Keep archive metadata internally consistent."""

        if self.parent_session_id is None and self.parent_formal_version_number is not None:
            raise ValueError(
                "parent_formal_version_number is only allowed when parent_session_id exists."
            )
        if self.archive_status == ArchiveStatus.SUCCEEDED:
            if self.archive_url is None:
                raise ValueError("archive_url is required when archive succeeds.")
        elif self.archive_url is not None:
            raise ValueError("archive_url is only allowed when archive succeeds.")

        return self


class IdeaAnalysisResponse(BaseAnalysisResponse):
    """API response for the root analysis flow."""

    session_kind: SessionKind = Field(
        default=SessionKind.ANALYSIS,
        description="Session kind for the current response.",
    )

    @model_validator(mode="after")
    def validate_root_shape(self) -> "IdeaAnalysisResponse":
        """Restrict the root analysis response to the analysis session kind."""

        if self.session_kind != SessionKind.ANALYSIS:
            raise ValueError("IdeaAnalysisResponse must use session_kind=analysis.")
        if self.root_session_id != self.session_id:
            raise ValueError("Root analysis responses must use session_id as root_session_id.")
        if self.parent_session_id is not None:
            raise ValueError("Root analysis responses must not include parent_session_id.")
        return self


class FollowUpInput(BaseModel):
    """Follow-up refinement input tied to one archived/completed parent session."""

    session_id: str | None = Field(
        default=None,
        description="Stable session ID for one follow-up clarification-bound flow.",
    )
    parent_session_id: str = Field(min_length=1, description="Parent session to continue from.")
    question: str = Field(min_length=1, description="Follow-up question or refinement request.")
    clarifications: list[ClarificationAnswer] = Field(
        default_factory=list,
        description="Optional one-round clarification answers for the follow-up.",
    )

    @field_validator("session_id", "parent_session_id", "question")
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Follow-up text fields must not be blank.")
        return normalized


class FollowUpLlmOutput(BaseModel):
    """LLM wrapper output for follow-up refinement."""

    archive_title: str = Field(
        min_length=1,
        description="Short semantic title for follow-up archive naming.",
    )
    input_echo: str = Field(
        min_length=1,
        description="Faithful restatement of the current follow-up question only.",
    )
    needs_clarification: bool = Field(
        description="Whether the follow-up question still needs clarification.",
    )
    assumptions: list[str] = Field(default_factory=list, description="System assumptions.")
    open_questions: list[str] = Field(default_factory=list, description="Open questions.")
    refinement_result: RefinementResult | None = Field(
        default=None,
        description="Structured refinement result when clarification is no longer needed.",
    )

    @field_validator("archive_title", "input_echo")
    @classmethod
    def validate_required_text_not_blank(cls, value: str) -> str:
        """Reject blank-only required text fields."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("archive_title and input_echo must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_consistency(self) -> "FollowUpLlmOutput":
        """Keep the wrapper shape internally consistent."""

        if len(self.open_questions) > 3:
            raise ValueError("open_questions must contain at most 3 items.")

        if self.needs_clarification:
            if self.refinement_result is not None:
                raise ValueError(
                    "refinement_result must be null when clarification is needed."
                )
            if not 2 <= len(self.open_questions) <= 3:
                raise ValueError(
                    "open_questions must contain 2 to 3 items when clarification is needed."
                )
        else:
            if self.refinement_result is None:
                raise ValueError(
                    "refinement_result must exist when clarification is not needed."
                )

        return self


class FollowUpResponse(FollowUpLlmOutput):
    """API response for one follow-up refinement session."""

    session_id: str = Field(min_length=1, description="Current follow-up session ID.")
    root_session_id: str = Field(
        min_length=1,
        description="Stable root session ID inherited from the idea thread.",
    )
    parent_session_id: str = Field(min_length=1, description="Parent session ID.")
    formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Formal version number. Follow-up refinement stays draft-only, "
            "so this is null."
        ),
    )
    parent_formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description="Stable formal version number of the direct parent session.",
    )
    session_kind: SessionKind = Field(
        default=SessionKind.FOLLOW_UP_REFINEMENT,
        description="Session kind for this follow-up response.",
    )
    archive_status: ArchiveStatus = Field(description="Current archive status.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL after a successful archive attempt.",
    )

    @field_validator("session_id", "root_session_id", "parent_session_id", "archive_url")
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Follow-up response text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_archive_metadata(self) -> "FollowUpResponse":
        """Keep archive metadata internally consistent."""

        if self.session_kind != SessionKind.FOLLOW_UP_REFINEMENT:
            raise ValueError("FollowUpResponse must use follow_up_refinement session kind.")
        if self.formal_version_number is not None:
            raise ValueError("FollowUpResponse must not include formal_version_number.")

        if self.archive_status == ArchiveStatus.SUCCEEDED:
            if self.archive_url is None:
                raise ValueError("archive_url is required when archive succeeds.")
        elif self.archive_url is not None:
            raise ValueError("archive_url is only allowed when archive succeeds.")

        return self


class ComposeFullPlanInput(BaseModel):
    """Input for confirming one refinement and generating a composed full plan."""

    parent_session_id: str = Field(
        min_length=1,
        description="Refinement session ID that should be composed into a new full plan.",
    )

    @field_validator("parent_session_id")
    @classmethod
    def validate_parent_not_blank(cls, value: str) -> str:
        """Reject blank-only parent IDs."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("parent_session_id must not be blank.")
        return normalized


class ComposedPlanResponse(BaseAnalysisResponse):
    """API response for a composed full-plan session."""

    parent_session_id: str = Field(min_length=1, description="Parent refinement session ID.")
    session_kind: SessionKind = Field(
        default=SessionKind.FULL_PLAN_COMPOSED,
        description="Session kind for the composed plan response.",
    )
    refinement_result: RefinementResult = Field(
        description="Refinement context used to compose the new full plan.",
    )

    @model_validator(mode="after")
    def validate_composed_shape(self) -> "ComposedPlanResponse":
        """Keep composed-plan metadata aligned."""

        if self.session_kind != SessionKind.FULL_PLAN_COMPOSED:
            raise ValueError("ComposedPlanResponse must use full_plan_composed session kind.")
        if self.analysis is None:
            raise ValueError("ComposedPlanResponse must include analysis.")
        return self


class SessionHistoryItem(BaseModel):
    """Compact history item used in session and thread list responses."""

    session_id: str = Field(min_length=1, description="Current session ID.")
    root_session_id: str = Field(min_length=1, description="Root session ID for the thread.")
    parent_session_id: str | None = Field(
        default=None,
        description="Immediate parent session ID, if any.",
    )
    formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description="Stable formal version number inside the root thread.",
    )
    parent_formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description="Stable formal version number of the direct parent session, if any.",
    )
    can_delete_leaf: bool = Field(
        description="Whether this node can be deleted as a non-root formal leaf.",
    )
    delete_block_reason: str | None = Field(
        default=None,
        description="Why leaf deletion is blocked for this node, if applicable.",
    )
    session_kind: SessionKind = Field(description="Kind of session.")
    archive_title: str = Field(min_length=1, description="Semantic archive title.")
    archive_status: ArchiveStatus = Field(description="Current archive status.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL after a successful archive attempt.",
    )
    created_at: datetime = Field(description="Creation time of the session.")
    updated_at: datetime = Field(description="Latest update time of the session.")
    can_continue_follow_up: bool = Field(
        description="Whether this node can be explicitly used as a follow-up parent.",
    )

    @field_validator(
        "session_id",
        "root_session_id",
        "parent_session_id",
        "archive_title",
        "archive_url",
        "delete_block_reason",
    )
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session history text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_delete_capability(self) -> "SessionHistoryItem":
        """Keep leaf-delete metadata internally consistent."""

        if self.can_delete_leaf and self.delete_block_reason is not None:
            raise ValueError(
                "delete_block_reason is only allowed when can_delete_leaf is false."
            )
        if not self.can_delete_leaf and self.delete_block_reason is None:
            raise ValueError(
                "delete_block_reason is required when can_delete_leaf is false."
            )
        return self


class SessionListResponse(BaseModel):
    """Response for session history list queries."""

    items: list[SessionHistoryItem] = Field(default_factory=list, description="History items.")


class SessionThreadSummary(BaseModel):
    """Compact summary for one idea thread."""

    root_session_id: str = Field(min_length=1, description="Root session ID for the thread.")
    root_archive_title: str = Field(min_length=1, description="Semantic title of the root idea.")
    latest_session_id: str = Field(min_length=1, description="Latest session ID in the thread.")
    latest_formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description="Stable formal version number of the latest formal session in the thread.",
    )
    latest_session_kind: SessionKind = Field(description="Latest session kind in the thread.")
    latest_archive_status: ArchiveStatus = Field(description="Latest archive status in the thread.")
    latest_updated_at: datetime = Field(description="Latest update time in the thread.")
    session_count: int = Field(ge=1, description="Number of sessions currently in the thread.")

    @field_validator("root_session_id", "root_archive_title", "latest_session_id")
    @classmethod
    def validate_required_text_not_blank(cls, value: str) -> str:
        """Reject blank-only required text fields."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Session thread summary text fields must not be blank.")
        return normalized


class ThreadListResponse(BaseModel):
    """Response for thread summary list queries."""

    items: list[SessionThreadSummary] = Field(
        default_factory=list,
        description="Thread summaries.",
    )


class ArchiveDeleteFailure(BaseModel):
    """One remote archive that could not be deleted cleanly."""

    archive_url: str = Field(min_length=1, description="Archive URL that failed to delete.")
    error: str = Field(min_length=1, description="Human-readable delete error.")

    @field_validator("archive_url", "error")
    @classmethod
    def validate_required_text_not_blank(cls, value: str) -> str:
        """Reject blank-only required text values."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Archive delete failure fields must not be blank.")
        return normalized


class ArchiveProbeFailure(BaseModel):
    """One remote archive whose presence could not be determined cleanly."""

    archive_url: str = Field(min_length=1, description="Archive URL that failed to probe.")
    error: str = Field(min_length=1, description="Human-readable probe error.")

    @field_validator("archive_url", "error")
    @classmethod
    def validate_required_text_not_blank(cls, value: str) -> str:
        """Reject blank-only required text values."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Archive probe failure fields must not be blank.")
        return normalized


class ArchiveSyncResponse(BaseModel):
    """Response returned after syncing local history with remote archive absence."""

    checked_archive_count: int = Field(
        ge=0,
        description="Number of archived sessions whose remote archive state was checked.",
    )
    removed_session_count: int = Field(
        ge=0,
        description="Number of local sessions removed because their remote archive was missing.",
    )
    removed_session_ids: list[str] = Field(
        default_factory=list,
        description="Session IDs removed from local history during this sync.",
    )
    probe_failures: list[ArchiveProbeFailure] = Field(
        default_factory=list,
        description="Remote archive probes that failed and therefore did not mutate local history.",
    )

    @field_validator("removed_session_ids")
    @classmethod
    def validate_removed_session_ids(cls, value: list[str]) -> list[str]:
        """Reject blank-only removed session identifiers."""

        normalized_ids: list[str] = []
        for item in value:
            normalized = item.strip()
            if not normalized:
                raise ValueError("removed_session_ids must not contain blank values.")
            normalized_ids.append(normalized)
        return normalized_ids


class ArchiveRetryResponse(BaseModel):
    """Response returned after retrying one previously failed Feishu archive."""

    session_id: str = Field(min_length=1, description="Session whose archive was retried.")
    archive_status: ArchiveStatus = Field(description="Final status of the retry attempt.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL when the retry succeeds.",
    )
    archive_error: str | None = Field(
        default=None,
        description="Safe, user-actionable error detail when the retry still fails.",
    )
    archived_at: datetime = Field(description="Time when the retry attempt completed.")

    @field_validator("session_id", "archive_url", "archive_error")
    @classmethod
    def validate_retry_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank retry response text."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Archive retry response text must not be blank.")
        return normalized


class ThreadDeleteResponse(BaseModel):
    """Response returned after deleting one local thread and its linked archives."""

    root_session_id: str = Field(min_length=1, description="Deleted root session ID.")
    deleted_session_count: int = Field(
        ge=1,
        description="Number of local sessions removed from this thread.",
    )
    deleted_archive_count: int = Field(
        ge=0,
        description="Number of Feishu archives deleted successfully.",
    )
    archive_delete_failures: list[ArchiveDeleteFailure] = Field(
        default_factory=list,
        description="Remote archive deletions that failed but did not block local cleanup.",
    )

    @field_validator("root_session_id")
    @classmethod
    def validate_root_not_blank(cls, value: str) -> str:
        """Reject blank-only root session identifiers."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("root_session_id must not be blank.")
        return normalized


class SessionLeafDeleteResponse(BaseModel):
    """Response returned after deleting one non-root formal leaf and attached drafts."""

    session_id: str = Field(min_length=1, description="Deleted formal leaf session ID.")
    root_session_id: str = Field(min_length=1, description="Root session ID for the thread.")
    parent_session_id: str = Field(
        min_length=1,
        description="Direct parent formal session used as the safe fallback after deletion.",
    )
    deleted_session_count: int = Field(
        ge=1,
        description="Total number of local sessions removed, including attached draft cache.",
    )
    deleted_draft_count: int = Field(
        ge=0,
        description="Number of attached follow-up draft sessions removed together with the leaf.",
    )
    deleted_archive_count: int = Field(
        ge=0,
        description="Number of Feishu archives deleted successfully.",
    )
    deleted_session_ids: list[str] = Field(
        default_factory=list,
        description="All local session IDs removed during this leaf delete.",
    )
    archive_delete_failures: list[ArchiveDeleteFailure] = Field(
        default_factory=list,
        description="Remote archive deletions that failed but did not block local cleanup.",
    )

    @field_validator("session_id", "root_session_id", "parent_session_id")
    @classmethod
    def validate_leaf_delete_text_not_blank(cls, value: str) -> str:
        """Reject blank-only text values in leaf delete responses."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Leaf delete response text fields must not be blank.")
        return normalized

    @field_validator("deleted_session_ids")
    @classmethod
    def validate_deleted_session_ids(cls, value: list[str]) -> list[str]:
        """Reject blank-only deleted session identifiers."""

        normalized_ids: list[str] = []
        for item in value:
            normalized = item.strip()
            if not normalized:
                raise ValueError("deleted_session_ids must not contain blank values.")
            normalized_ids.append(normalized)
        return normalized_ids


class SessionDetailResponse(BaseModel):
    """Detailed history response for one session."""

    session_id: str = Field(min_length=1, description="Current session ID.")
    root_session_id: str = Field(min_length=1, description="Root session ID for the thread.")
    parent_session_id: str | None = Field(
        default=None,
        description="Immediate parent session ID, if any.",
    )
    formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Stable formal version number inside the root thread "
            "when the current session is formal."
        ),
    )
    parent_formal_version_number: int | None = Field(
        default=None,
        ge=1,
        description="Stable formal version number of the direct parent session, if any.",
    )
    session_kind: SessionKind = Field(description="Kind of session.")
    archive_status: ArchiveStatus = Field(description="Current archive status.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL after a successful archive attempt.",
    )
    archive_error: str | None = Field(
        default=None,
        description="Safe, user-actionable error detail after a failed archive attempt.",
    )
    archive_title: str = Field(min_length=1, description="Semantic archive title.")
    original_content: str = Field(min_length=1, description="Root/original idea content.")
    input_echo: str = Field(min_length=1, description="Faithful current input echo.")
    clarifications: list[ClarificationAnswer] = Field(
        default_factory=list,
        description="Clarifications used in the session.",
    )
    assumptions: list[str] = Field(default_factory=list, description="System assumptions.")
    open_questions: list[str] = Field(default_factory=list, description="Open questions.")
    follow_up_question: str | None = Field(
        default=None,
        description="Follow-up question when this is not a root analysis.",
    )
    analysis: IdeaAnalysis | None = Field(
        default=None,
        description="Full analysis when available.",
    )
    refinement_result: RefinementResult | None = Field(
        default=None,
        description="Refinement result when available.",
    )
    created_at: datetime = Field(description="Creation time of the session.")
    completed_at: datetime = Field(description="Completion time of the session.")
    updated_at: datetime = Field(description="Latest update time of the session.")
    archived_at: datetime | None = Field(
        default=None,
        description="Archive attempt completion time, if any.",
    )
    can_continue_follow_up: bool = Field(
        description="Whether this node can be explicitly used as a follow-up parent.",
    )
    child_session_ids: list[str] = Field(
        default_factory=list,
        description="Immediate children that continue from this session.",
    )
    active_follow_up_draft_id: str | None = Field(
        default=None,
        description="Latest recoverable follow-up draft ID under this formal session.",
    )
    active_follow_up_draft_question: str | None = Field(
        default=None,
        description="Latest recoverable follow-up draft question, if one exists.",
    )
    active_follow_up_draft_updated_at: datetime | None = Field(
        default=None,
        description="Latest update time for the recoverable follow-up draft, if any.",
    )

    @field_validator(
        "session_id",
        "root_session_id",
        "parent_session_id",
        "archive_url",
        "archive_error",
        "archive_title",
        "original_content",
        "input_echo",
        "follow_up_question",
        "active_follow_up_draft_id",
        "active_follow_up_draft_question",
    )
    @classmethod
    def validate_detail_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session detail text fields must not be blank.")
        return normalized


class SessionThreadResponse(BaseModel):
    """Detailed response for one idea thread."""

    root_session_id: str = Field(min_length=1, description="Root session ID for the thread.")
    items: list[SessionHistoryItem] = Field(
        default_factory=list,
        description="Ordered sessions in the thread.",
    )

    @field_validator("root_session_id")
    @classmethod
    def validate_root_not_blank(cls, value: str) -> str:
        """Reject blank-only root session identifiers."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("root_session_id must not be blank.")
        return normalized
