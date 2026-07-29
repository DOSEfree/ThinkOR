"""Application settings for the local development baseline."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


def resolve_project_root(working_directory: Path | None = None) -> Path:
    """Resolve the local project directory before falling back to the installed package path."""

    candidate = (working_directory or Path.cwd()).resolve()
    if (candidate / "pyproject.toml").is_file() or (candidate / ".env.example").is_file():
        return candidate
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = resolve_project_root()
ENV_FILE_PATH = PROJECT_ROOT / ".env"


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    """Parse a boolean-like environment variable value."""

    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_app_name(value: str | None) -> str:
    """Keep the legacy display-name setting compatible with the ThinkOR brand."""

    normalized = value.strip() if value is not None else ""
    if not normalized or normalized == "IdeaOS-Agent":
        return "ThinkOR"
    return normalized


def _get_setting_value(name: str, dotenv_values_map: dict[str, str | None]) -> str | None:
    """Prefer explicit process variables over the local dotenv file."""

    process_value = os.getenv(name)
    if process_value is not None:
        return process_value
    return dotenv_values_map.get(name)


@dataclass(frozen=True)
class AppSettings:
    """Typed runtime settings loaded from environment variables."""

    app_name: str = "ThinkOR"
    environment: str = "development"
    debug: bool = False
    llm_provider: str = "alibaba_compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 30.0
    max_input_chars: int = 4000
    use_fake_llm: bool = False
    use_fake_archive: bool = False
    archive_db_path: str = "data/ideaos_agent.db"
    follow_up_draft_retention_days: int = 7
    feishu_cli_command: str = "lark-cli"
    feishu_archive_as: str = "user"
    feishu_archive_parent_token: str = ""
    feishu_archive_timeout_seconds: float = 30.0


def get_settings() -> AppSettings:
    """Load settings from the local dotenv file and explicit process variables."""

    dotenv_values_map = dict(dotenv_values(ENV_FILE_PATH)) if ENV_FILE_PATH.is_file() else {}

    return AppSettings(
        app_name=_resolve_app_name(_get_setting_value("IDEAOS_APP_NAME", dotenv_values_map)),
        environment=_get_setting_value("IDEAOS_ENV", dotenv_values_map) or "development",
        debug=_parse_bool(_get_setting_value("IDEAOS_DEBUG", dotenv_values_map), default=False),
        llm_provider=(
            _get_setting_value("IDEAOS_LLM_PROVIDER", dotenv_values_map)
            or "alibaba_compatible"
        ),
        llm_base_url=_get_setting_value("IDEAOS_LLM_BASE_URL", dotenv_values_map) or "",
        llm_api_key=_get_setting_value("IDEAOS_LLM_API_KEY", dotenv_values_map) or "",
        llm_model=_get_setting_value("IDEAOS_LLM_MODEL", dotenv_values_map) or "",
        llm_timeout_seconds=float(
            _get_setting_value("IDEAOS_LLM_TIMEOUT_SECONDS", dotenv_values_map) or "30"
        ),
        max_input_chars=int(
            _get_setting_value("IDEAOS_MAX_INPUT_CHARS", dotenv_values_map) or "4000"
        ),
        use_fake_llm=_parse_bool(
            _get_setting_value("IDEAOS_USE_FAKE_LLM", dotenv_values_map),
            default=True,
        ),
        use_fake_archive=_parse_bool(
            _get_setting_value("IDEAOS_USE_FAKE_ARCHIVE", dotenv_values_map),
            default=True,
        ),
        archive_db_path=(
            _get_setting_value("IDEAOS_ARCHIVE_DB_PATH", dotenv_values_map)
            or "data/ideaos_agent.db"
        ),
        follow_up_draft_retention_days=int(
            _get_setting_value("IDEAOS_FOLLOW_UP_DRAFT_RETENTION_DAYS", dotenv_values_map)
            or "7"
        ),
        feishu_cli_command=(
            _get_setting_value("IDEAOS_FEISHU_CLI_COMMAND", dotenv_values_map) or "lark-cli"
        ),
        feishu_archive_as=(
            _get_setting_value("IDEAOS_FEISHU_ARCHIVE_AS", dotenv_values_map) or "user"
        ),
        feishu_archive_parent_token=(
            _get_setting_value("IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN", dotenv_values_map)
            or ""
        ),
        feishu_archive_timeout_seconds=float(
            _get_setting_value("IDEAOS_FEISHU_ARCHIVE_TIMEOUT_SECONDS", dotenv_values_map)
            or "30"
        ),
    )
