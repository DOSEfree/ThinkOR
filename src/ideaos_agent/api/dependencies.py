"""Dependency wiring for API routes."""

from ideaos_agent.application.idea_analysis_service import IdeaAnalysisService
from ideaos_agent.config import AppSettings, get_settings
from ideaos_agent.infrastructure.llm.client import (
    HttpLlmClient,
    LlmClient,
)
from ideaos_agent.infrastructure.llm.fake_client import FakeLlmClient
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder


def get_app_settings() -> AppSettings:
    """Return application settings for FastAPI dependencies."""

    return get_settings()


def get_llm_client(settings: AppSettings) -> LlmClient:
    """Create the LLM client selected by configuration."""

    if settings.use_fake_llm:
        return FakeLlmClient()

    return HttpLlmClient(
        provider=settings.llm_provider,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def get_idea_analysis_service() -> IdeaAnalysisService:
    """Create the Phase 1 idea analysis service."""

    settings = get_app_settings()
    return IdeaAnalysisService(
        settings=settings,
        llm_client=get_llm_client(settings),
        prompt_builder=IdeaAnalysisPromptBuilder(),
    )
