"""Core data structures for IdeaOS-Agent v0.1."""

from pydantic import BaseModel, Field, field_validator, model_validator


class IdeaInput(BaseModel):
    """User-provided raw idea text plus optional clarification answers."""

    content: str = Field(min_length=1, description="用户输入的原始想法文本。")
    clarifications: list["ClarificationAnswer"] = Field(
        default_factory=list,
        description="用户对上一轮关键问题的补充回答。服务端不持久化，只随请求显式携带。",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        """Reject blank-only content while preserving the original text."""

        if not value.strip():
            raise ValueError("想法输入不能为空白。")
        return value


class ClarificationAnswer(BaseModel):
    """Single user-provided clarification answer."""

    question: str = Field(min_length=1, description="系统提出的澄清问题。")
    answer: str = Field(min_length=1, description="用户对该问题的回答。")

    @field_validator("question", "answer")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        """Reject blank-only clarification content."""

        if not value.strip():
            raise ValueError("澄清问题与回答不能为空白。")
        return value


class IdeaAnalysis(BaseModel):
    """Full nine-field analysis contract for the implementation slice."""

    summary: str = Field(description="想法摘要：用一两句话讲清这个想法是什么。")
    feasibility: str = Field(description="可行性分析：技术 / 市场 / 资源层面的初步判断。")
    market: str = Field(description="市场分析：面向谁、需求是否真实、大致竞争格局。")
    knowledge_gaps: list[str] = Field(
        default_factory=list,
        description="知识缺口：推进该想法所需补齐的知识领域。",
    )
    resource_gaps: list[str] = Field(
        default_factory=list,
        description="资源缺口：容易被忽略的资源约束清单。",
    )
    team_requirements: list[str] = Field(
        default_factory=list,
        description="团队需求：推荐的团队角色配置。",
    )
    similar_projects: list[str] = Field(
        default_factory=list,
        description="相似项目参考：v0.1 仅依据模型已有知识给出，不接外部数据源。",
    )
    mvp_roadmap: list[str] = Field(
        default_factory=list,
        description="MVP 路线图：从想法到最小可用版本的关键步骤。",
    )
    long_term_roadmap: list[str] = Field(
        default_factory=list,
        description="长期发展路线图：MVP 之后的阶段性方向。",
    )


class IdeaAnalysisResponse(BaseModel):
    """Outer response wrapper for analysis mode and clarification mode."""

    input_echo: str = Field(
        min_length=1,
        description="对用户【原始想法】的忠实复述，建议尽量原样保留，不做扩写。",
    )
    needs_clarification: bool = Field(description="当前信息是否不足以直接产出正式分析。")
    assumptions: list[str] = Field(
        default_factory=list,
        description="用户未明确给出、由模型补入的假设前提。",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="澄清问题或后续打磨问题。澄清模式需给 2 到 3 个，分析模式可为空。",
    )
    analysis: IdeaAnalysis | None = Field(
        default=None,
        description="当 needs_clarification=false 时返回完整分析，否则必须为 null。",
    )

    @field_validator("input_echo")
    @classmethod
    def validate_input_echo_not_blank(cls, value: str) -> str:
        """Reject blank-only input echoes."""

        if not value.strip():
            raise ValueError("input_echo 不能为空白。")
        return value

    @model_validator(mode="after")
    def validate_consistency(self) -> "IdeaAnalysisResponse":
        """Ensure the wrapper is self-consistent and safe."""

        if len(self.open_questions) > 3:
            raise ValueError("open_questions 最多提供 3 个问题。")

        if self.needs_clarification:
            if self.analysis is not None:
                raise ValueError("需要澄清时 analysis 必须为 null。")
            if not 2 <= len(self.open_questions) <= 3:
                raise ValueError("需要澄清时 open_questions 必须提供 2 到 3 个问题。")
        else:
            if self.analysis is None:
                raise ValueError("无需澄清时必须返回 analysis。")

        return self
