"""Typed API-facing models for IdeaOS-Agent requests and responses."""

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
    session_kind: SessionKind = Field(description="Session kind for the current response.")
    parent_session_id: str | None = Field(
        default=None,
        description="Parent session ID. Root analyses do not have one.",
    )
    archive_status: ArchiveStatus = Field(description="Current archive status.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL after a successful archive attempt.",
    )

    @field_validator("session_id", "parent_session_id", "archive_url")
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
    parent_session_id: str = Field(min_length=1, description="Parent session ID.")
    session_kind: SessionKind = Field(
        default=SessionKind.FOLLOW_UP_REFINEMENT,
        description="Session kind for this follow-up response.",
    )
    archive_status: ArchiveStatus = Field(description="Current archive status.")
    archive_url: str | None = Field(
        default=None,
        description="Archive URL after a successful archive attempt.",
    )

    @field_validator("session_id", "parent_session_id", "archive_url")
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
