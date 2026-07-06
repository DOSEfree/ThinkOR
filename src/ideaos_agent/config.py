"""Application settings for the local development baseline."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    """Parse a boolean-like environment variable value."""

    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppSettings:
    """Typed runtime settings loaded from environment variables."""

    app_name: str = "IdeaOS-Agent"
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
    feishu_cli_command: str = "lark-cli"
    feishu_archive_as: str = "user"
    feishu_archive_parent_token: str = ""
    feishu_archive_timeout_seconds: float = 30.0


def get_settings() -> AppSettings:
    """Load runtime settings from the current process environment."""

    return AppSettings(
        app_name=os.getenv("IDEAOS_APP_NAME", "IdeaOS-Agent"),
        environment=os.getenv("IDEAOS_ENV", "development"),
        debug=_parse_bool(os.getenv("IDEAOS_DEBUG"), default=False),
        llm_provider=os.getenv("IDEAOS_LLM_PROVIDER", "alibaba_compatible"),
        llm_base_url=os.getenv("IDEAOS_LLM_BASE_URL", ""),
        llm_api_key=os.getenv("IDEAOS_LLM_API_KEY", ""),
        llm_model=os.getenv("IDEAOS_LLM_MODEL", ""),
        llm_timeout_seconds=float(os.getenv("IDEAOS_LLM_TIMEOUT_SECONDS", "30")),
        max_input_chars=int(os.getenv("IDEAOS_MAX_INPUT_CHARS", "4000")),
        use_fake_llm=_parse_bool(os.getenv("IDEAOS_USE_FAKE_LLM"), default=False),
        use_fake_archive=_parse_bool(os.getenv("IDEAOS_USE_FAKE_ARCHIVE"), default=False),
        archive_db_path=os.getenv("IDEAOS_ARCHIVE_DB_PATH", "data/ideaos_agent.db"),
        feishu_cli_command=os.getenv("IDEAOS_FEISHU_CLI_COMMAND", "lark-cli"),
        feishu_archive_as=os.getenv("IDEAOS_FEISHU_ARCHIVE_AS", "user"),
        feishu_archive_parent_token=os.getenv("IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN", ""),
        feishu_archive_timeout_seconds=float(
            os.getenv("IDEAOS_FEISHU_ARCHIVE_TIMEOUT_SECONDS", "30")
        ),
    )
