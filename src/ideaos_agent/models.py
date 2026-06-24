"""Core data structures for IdeaOS-Agent v0.1."""

from pydantic import BaseModel, Field, field_validator


class IdeaInput(BaseModel):
    """User-provided raw idea text."""

    content: str = Field(min_length=1, description="用户输入的原始想法文本。")

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        """Reject blank-only content while preserving the original text."""

        if not value.strip():
            raise ValueError("想法输入不能为空白。")
        return value


class IdeaAnalysis(BaseModel):
    """单次想法分析的完整输出契约。

    这是 Phase 1「端到端薄纵切」的核心承诺：一次 LLM 调用一次性产出全部
    9 个模块。字段刻意保持简单（文本 / 字符串列表），允许内容粗糙但必须完整。
    更丰富的结构（如可行性 1–10 评分、知识缺口领域清单等）属于 Phase 2 的
    逐段提质范围，届时再在不破坏端到端链路的前提下细化对应字段。
    """

    summary: str = Field(description="想法摘要：用一两句话讲清这个想法是什么。")
    feasibility: str = Field(description="可行性分析：技术 / 市场 / 资源层面的初步判断。")
    market: str = Field(description="市场分析：面向谁、需求是否真实、大致竞争格局。")
    knowledge_gaps: list[str] = Field(
        default_factory=list, description="知识缺口：推进该想法所需补齐的知识领域。"
    )
    resource_gaps: list[str] = Field(
        default_factory=list, description="资源缺口：容易被忽略的资源约束清单。"
    )
    team_requirements: list[str] = Field(
        default_factory=list, description="团队需求：推荐的团队角色配置。"
    )
    similar_projects: list[str] = Field(
        default_factory=list,
        description="相似项目参考：v0.1 仅依据模型已有知识给出，不接外部数据源。",
    )
    mvp_roadmap: list[str] = Field(
        default_factory=list, description="MVP 路线图：从想法到最小可用版本的关键步骤。"
    )
    long_term_roadmap: list[str] = Field(
        default_factory=list, description="长期发展路线图：MVP 之后的阶段性方向。"
    )
