"""Core data structures for IdeaOS-Agent v0.1."""

from pydantic import BaseModel, Field


class IdeaInput(BaseModel):
    """User-provided raw idea text."""

    content: str = Field(min_length=1, description="用户输入的原始想法文本。")
