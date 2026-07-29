"""Dependency wiring for API routes."""

import os

from ideaos_agent.application.follow_up_session_service import FollowUpSessionService
from ideaos_agent.application.idea_analysis_service import IdeaAnalysisService
from ideaos_agent.application.idea_analysis_session_service import IdeaAnalysisSessionService
from ideaos_agent.application.lark_setup_service import LarkSetupService
from ideaos_agent.application.local_config_service import LocalConfigService
from ideaos_agent.application.runtime_capability_service import RuntimeCapabilityService
from ideaos_agent.application.session_history_service import SessionHistoryService
from ideaos_agent.config import ENV_FILE_PATH, PROJECT_ROOT, AppSettings, get_settings
from ideaos_agent.domain.archive import SessionArchiver, SessionArchiveStore
from ideaos_agent.domain.session import SessionSnapshotStore
from ideaos_agent.infrastructure.archive.fake_archiver import FakeSessionArchiver
from ideaos_agent.infrastructure.archive.lark_cli_archiver import LarkCliSessionArchiver
from ideaos_agent.infrastructure.archive.lark_cli_status import LarkCliStatusAdapter
from ideaos_agent.infrastructure.archive.sqlite_store import SqliteSessionArchiveStore
from ideaos_agent.infrastructure.config.dotenv_store import DotenvModeStore
from ideaos_agent.infrastructure.llm.client import HttpLlmClient, LlmClient
from ideaos_agent.infrastructure.llm.fake_client import FakeLlmClient
from ideaos_agent.prompts.follow_up import FollowUpPromptBuilder
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder

_LARK_SETUP_SERVICE: LarkSetupService | None = None


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
    """Create the core idea analysis service that only talks to the LLM."""

    settings = get_app_settings()
    return IdeaAnalysisService(
        settings=settings,
        llm_client=get_llm_client(settings),
        prompt_builder=IdeaAnalysisPromptBuilder(),
    )


def get_session_archive_store(settings: AppSettings) -> SessionArchiveStore:
    """Create the local archive index store selected by configuration."""

    return SqliteSessionArchiveStore(settings.archive_db_path)


def get_session_snapshot_store(settings: AppSettings) -> SessionSnapshotStore:
    """Create the local structured snapshot store selected by configuration."""

    return SqliteSessionArchiveStore(settings.archive_db_path)


def get_session_archiver(settings: AppSettings) -> SessionArchiver:
    """Create the archive adapter selected by configuration."""

    if settings.use_fake_archive:
        return FakeSessionArchiver()

    return LarkCliSessionArchiver(
        command=settings.feishu_cli_command,
        archive_as=settings.feishu_archive_as,
        parent_token=settings.feishu_archive_parent_token,
        timeout_seconds=settings.feishu_archive_timeout_seconds,
    )


def get_idea_analysis_session_service() -> IdeaAnalysisSessionService:
    """Create the session-aware root analysis service."""

    settings = get_app_settings()
    return IdeaAnalysisSessionService(
        analysis_service=get_idea_analysis_service(),
        session_archive_store=get_session_archive_store(settings),
        session_snapshot_store=get_session_snapshot_store(settings),
        session_archiver=get_session_archiver(settings),
    )


def get_follow_up_session_service() -> FollowUpSessionService:
    """Create the v0.2.5 follow-up session service."""

    settings = get_app_settings()
    return FollowUpSessionService(
        settings=settings,
        llm_client=get_llm_client(settings),
        prompt_builder=FollowUpPromptBuilder(),
        session_archive_store=get_session_archive_store(settings),
        session_snapshot_store=get_session_snapshot_store(settings),
        session_archiver=get_session_archiver(settings),
    )


def get_session_history_service() -> SessionHistoryService:
    """Create the history service for thread queries and deletions."""

    settings = get_app_settings()
    return SessionHistoryService(
        follow_up_draft_retention_days=settings.follow_up_draft_retention_days,
        session_archive_store=get_session_archive_store(settings),
        session_snapshot_store=get_session_snapshot_store(settings),
        session_archiver=get_session_archiver(settings),
    )


def get_lark_cli_status_adapter(settings: AppSettings) -> LarkCliStatusAdapter:
    """Build the standalone local CLI status adapter."""

    return LarkCliStatusAdapter(
        command=settings.feishu_cli_command,
        archive_as=settings.feishu_archive_as,
        timeout_seconds=settings.feishu_archive_timeout_seconds,
    )


def get_runtime_capability_service() -> RuntimeCapabilityService:
    """Return safe effective mode and readiness details."""

    settings = get_app_settings()
    return RuntimeCapabilityService(
        settings=settings,
        lark_adapter=get_lark_cli_status_adapter(settings),
    )


def get_local_config_service() -> LocalConfigService:
    """Return the service allowed to patch two non-secret mode flags."""

    return LocalConfigService(
        dotenv_store=DotenvModeStore(
            dotenv_path=ENV_FILE_PATH,
            template_path=PROJECT_ROOT / ".env.example",
        ),
        settings_loader=get_settings,
        process_environment=dict(os.environ),
    )


def get_lark_setup_service() -> LarkSetupService:
    """Return the one in-process, short-lived user authorization flow manager."""

    global _LARK_SETUP_SERVICE
    if _LARK_SETUP_SERVICE is None:
        settings = get_app_settings()
        _LARK_SETUP_SERVICE = LarkSetupService(
            adapter=get_lark_cli_status_adapter(settings),
            project_root=PROJECT_ROOT,
        )
    return _LARK_SETUP_SERVICE
