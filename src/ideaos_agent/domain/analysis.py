"""Core analysis-domain models shared by API, storage, and archive layers."""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisSectionKey(StrEnum):
    """Canonical section keys for the nine-field analysis contract."""

    SUMMARY = "summary"
    FEASIBILITY = "feasibility"
    MARKET = "market"
    KNOWLEDGE_GAPS = "knowledge_gaps"
    RESOURCE_GAPS = "resource_gaps"
    TEAM_REQUIREMENTS = "team_requirements"
    SIMILAR_PROJECTS = "similar_projects"
    MVP_ROADMAP = "mvp_roadmap"
    LONG_TERM_ROADMAP = "long_term_roadmap"


TEXT_SECTION_KEYS = {
    AnalysisSectionKey.SUMMARY,
    AnalysisSectionKey.FEASIBILITY,
    AnalysisSectionKey.MARKET,
}

LIST_SECTION_KEYS = {
    AnalysisSectionKey.KNOWLEDGE_GAPS,
    AnalysisSectionKey.RESOURCE_GAPS,
    AnalysisSectionKey.TEAM_REQUIREMENTS,
    AnalysisSectionKey.SIMILAR_PROJECTS,
    AnalysisSectionKey.MVP_ROADMAP,
    AnalysisSectionKey.LONG_TERM_ROADMAP,
}


class IdeaAnalysis(BaseModel):
    """Structured analysis output shared across analysis and compose flows."""

    summary: str = Field(description="High-level summary of the idea.")
    feasibility: str = Field(description="Feasibility assessment.")
    market: str = Field(description="Market assessment.")
    knowledge_gaps: list[str] = Field(default_factory=list, description="Knowledge gaps.")
    resource_gaps: list[str] = Field(default_factory=list, description="Resource gaps.")
    team_requirements: list[str] = Field(default_factory=list, description="Suggested roles.")
    similar_projects: list[str] = Field(default_factory=list, description="Similar projects.")
    mvp_roadmap: list[str] = Field(default_factory=list, description="MVP roadmap.")
    long_term_roadmap: list[str] = Field(
        default_factory=list,
        description="Long-term roadmap.",
    )

    @field_validator("summary", "feasibility", "market")
    @classmethod
    def validate_required_copy_not_blank(cls, value: str) -> str:
        """Reject blank-only text sections."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Analysis text fields must not be blank.")
        return normalized


class SectionUpdate(BaseModel):
    """One proposed update to one analysis section."""

    section_key: AnalysisSectionKey = Field(description="Which analysis section is updated.")
    change_summary: str = Field(description="Short explanation of the proposed change.")
    updated_text: str | None = Field(
        default=None,
        description="Replacement value for text sections.",
    )
    updated_items: list[str] = Field(
        default_factory=list,
        description="Replacement items for list sections.",
    )

    @field_validator("change_summary", "updated_text")
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Section update text must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_value_shape(self) -> "SectionUpdate":
        """Require the right replacement payload shape for each section type."""

        if self.section_key in TEXT_SECTION_KEYS:
            if self.updated_text is None:
                raise ValueError("Text sections require updated_text.")
            if self.updated_items:
                raise ValueError("Text sections must not provide updated_items.")
        else:
            if not self.updated_items:
                raise ValueError("List sections require updated_items.")
            if self.updated_text is not None:
                raise ValueError("List sections must not provide updated_text.")

        return self


class RefinementResult(BaseModel):
    """Structured follow-up refinement result used before full-plan composition."""

    question_summary: str = Field(description="Short restatement of the follow-up request.")
    refinement_answer: str = Field(description="Direct answer to the follow-up request.")
    affected_sections: list[AnalysisSectionKey] = Field(
        default_factory=list,
        description="Which sections are affected by the refinement.",
    )
    proposed_section_updates: list[SectionUpdate] = Field(
        default_factory=list,
        description="Concrete section-level updates proposed by the refinement.",
    )
    next_actions: list[str] = Field(
        default_factory=list,
        description="Optional next actions after the refinement.",
    )

    @field_validator("question_summary", "refinement_answer")
    @classmethod
    def validate_required_text_not_blank(cls, value: str) -> str:
        """Reject blank-only required text values."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("Refinement text fields must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_consistency(self) -> "RefinementResult":
        """Keep section references and updates aligned."""

        if not self.proposed_section_updates:
            raise ValueError("Refinement results must include proposed_section_updates.")

        update_keys = [item.section_key for item in self.proposed_section_updates]
        if not self.affected_sections:
            object.__setattr__(self, "affected_sections", list(dict.fromkeys(update_keys)))
        else:
            missing_keys = [key for key in update_keys if key not in self.affected_sections]
            if missing_keys:
                raise ValueError("affected_sections must include every updated section.")

        return self


def apply_section_updates(
    base_analysis: IdeaAnalysis,
    updates: list[SectionUpdate],
) -> IdeaAnalysis:
    """Create a new analysis by applying proposed section updates in order."""

    composed = base_analysis.model_dump()
    for update in updates:
        key = update.section_key.value
        if update.section_key in TEXT_SECTION_KEYS:
            composed[key] = update.updated_text
        else:
            composed[key] = list(update.updated_items)
    return IdeaAnalysis.model_validate(composed)
