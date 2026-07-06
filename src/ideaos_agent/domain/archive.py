"""Archive-related domain models for v0.2 session tracking."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator, model_validator


class ArchiveStatus(StrEnum):
    """Archive lifecycle states for a single idea analysis session."""

    NOT_TRIGGERED = "not_triggered"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SessionRecord(BaseModel):
    """Minimal local session index model for archive tracking."""

    session_id: str = Field(min_length=1, description="完整会话的稳定 ID。")
    original_content: str = Field(min_length=1, description="用户首次提交的原始想法。")
    input_echo: str = Field(min_length=1, description="LLM 对原始想法的忠实复述。")
    clarification_count: int = Field(
        ge=0,
        description="当前请求中携带的澄清回答数量，用于最小索引与状态追踪。",
    )
    archive_status: ArchiveStatus = Field(description="当前会话的归档状态。")
    archive_url: str | None = Field(
        default=None,
        description="飞书归档链接。仅归档成功后应有值。",
    )
    archive_error: str | None = Field(
        default=None,
        description="归档失败时记录的最小错误信息。",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="会话记录创建时间。",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="会话进入最终完成态的时间；若仍为澄清态则为空。",
    )
    archived_at: datetime | None = Field(
        default=None,
        description="归档动作完成时间；成功或失败后均可记录。",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="会话记录最后更新时间。",
    )

    @field_validator("session_id", "original_content", "input_echo", "archive_error")
    @classmethod
    def validate_not_blank_when_present(cls, value: str | None) -> str | None:
        """Reject blank-only strings while allowing null optional fields."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("会话记录字段不能为空白字符串。")
        return normalized

    @field_validator("archive_url")
    @classmethod
    def validate_archive_url_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only archive URLs while allowing null."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("archive_url 不能为空白字符串。")
        return normalized

    @model_validator(mode="after")
    def validate_archive_consistency(self) -> "SessionRecord":
        """Keep persisted archive state internally consistent."""

        if self.archive_status == ArchiveStatus.NOT_TRIGGERED:
            if self.completed_at is not None:
                raise ValueError("未触发归档的会话不应包含 completed_at。")
            if self.archived_at is not None:
                raise ValueError("未触发归档的会话不应包含 archived_at。")
            if self.archive_url is not None:
                raise ValueError("未触发归档的会话不应包含 archive_url。")

        if self.archive_status == ArchiveStatus.PENDING:
            if self.completed_at is None:
                raise ValueError("待归档会话必须记录 completed_at。")
            if self.archived_at is not None:
                raise ValueError("待归档会话不应提前写入 archived_at。")
            if self.archive_url is not None:
                raise ValueError("待归档会话不应包含 archive_url。")

        if self.archive_status == ArchiveStatus.SUCCEEDED:
            if self.completed_at is None:
                raise ValueError("归档成功会话必须记录 completed_at。")
            if self.archived_at is None:
                raise ValueError("归档成功会话必须记录 archived_at。")
            if self.archive_url is None:
                raise ValueError("归档成功会话必须包含 archive_url。")

        if self.archive_status == ArchiveStatus.FAILED:
            if self.completed_at is None:
                raise ValueError("归档失败会话必须记录 completed_at。")
            if self.archived_at is None:
                raise ValueError("归档失败会话必须记录 archived_at。")
            if self.archive_url is not None:
                raise ValueError("归档失败会话不应包含 archive_url。")

        return self


class SessionClarificationRecord(BaseModel):
    """Serializable clarification item used in archive payloads."""

    question: str = Field(min_length=1, description="澄清问题。")
    answer: str = Field(min_length=1, description="用户回答。")

    @field_validator("question", "answer")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        """Reject blank-only clarification content."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("归档澄清内容不能为空白。")
        return normalized


class SessionArchivePayload(BaseModel):
    """Complete archive payload passed from application layer to an archiver."""

    session_id: str = Field(min_length=1, description="完整会话 ID。")
    archive_title: str = Field(min_length=1, description="归档文档标题中的语义标题部分。")
    original_content: str = Field(min_length=1, description="用户原始想法。")
    input_echo: str = Field(min_length=1, description="LLM 对原始想法的忠实复述。")
    clarifications: list[SessionClarificationRecord] = Field(
        default_factory=list,
        description="本次会话携带的澄清记录。",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="系统假设列表。",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="后续可继续打磨的问题。",
    )
    summary: str = Field(description="分析摘要。")
    feasibility: str = Field(description="可行性分析。")
    market: str = Field(description="市场分析。")
    knowledge_gaps: list[str] = Field(default_factory=list, description="知识缺口列表。")
    resource_gaps: list[str] = Field(default_factory=list, description="资源缺口列表。")
    team_requirements: list[str] = Field(default_factory=list, description="团队需求列表。")
    similar_projects: list[str] = Field(default_factory=list, description="相似项目列表。")
    mvp_roadmap: list[str] = Field(default_factory=list, description="MVP 路线图。")
    long_term_roadmap: list[str] = Field(default_factory=list, description="长期路线图。")
    created_at: datetime = Field(description="会话首次创建时间。")
    completed_at: datetime = Field(description="会话完成分析时间。")

    @field_validator(
        "session_id",
        "archive_title",
        "original_content",
        "input_echo",
        "summary",
        "feasibility",
        "market",
    )
    @classmethod
    def validate_required_text_not_blank(cls, value: str) -> str:
        """Reject blank-only required archive text fields."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("归档载荷中的必填文本字段不能为空白。")
        return normalized


class ArchiveResult(BaseModel):
    """Result returned by an archive adapter after one archive attempt."""

    archive_status: ArchiveStatus = Field(description="归档尝试后的最终状态。")
    archive_url: str | None = Field(default=None, description="归档成功后的飞书文档链接。")
    archive_error: str | None = Field(default=None, description="归档失败时记录的最小错误信息。")
    archived_at: datetime = Field(description="本次归档尝试结束时间。")

    @field_validator("archive_url", "archive_error")
    @classmethod
    def validate_optional_text_not_blank(cls, value: str | None) -> str | None:
        """Reject blank-only optional text values."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("归档结果文本字段不能为空白字符串。")
        return normalized

    @model_validator(mode="after")
    def validate_result_consistency(self) -> "ArchiveResult":
        """Keep archive attempt results internally consistent."""

        if self.archive_status == ArchiveStatus.SUCCEEDED:
            if self.archive_url is None:
                raise ValueError("归档成功结果必须包含 archive_url。")
            if self.archive_error is not None:
                raise ValueError("归档成功结果不应包含 archive_error。")
        elif self.archive_status == ArchiveStatus.FAILED:
            if self.archive_url is not None:
                raise ValueError("归档失败结果不应包含 archive_url。")
        else:
            raise ValueError("ArchiveResult 仅接受 succeeded 或 failed 两种状态。")

        return self


class SessionArchiveStore(Protocol):
    """Storage contract for the minimal session archive index."""

    def save_session_record(self, record: SessionRecord) -> SessionRecord:
        """Create or update the minimal session archive index record."""

    def get_session_record(self, session_id: str) -> SessionRecord | None:
        """Fetch a session archive record by its stable session ID."""


class SessionArchiver(Protocol):
    """Archive adapter contract for external session archive targets."""

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        """Archive one completed session and return the final attempt result."""
