"""Application settings for the local development baseline."""

import os
from dataclasses import dataclass


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


def get_settings() -> AppSettings:
    """Load runtime settings from the current process environment."""

    return AppSettings(
        app_name=os.getenv("IDEAOS_APP_NAME", "IdeaOS-Agent"),
        environment=os.getenv("IDEAOS_ENV", "development"),
        debug=_parse_bool(os.getenv("IDEAOS_DEBUG"), default=False),
    )
