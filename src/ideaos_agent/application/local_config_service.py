"""Application service for non-secret local runtime mode changes."""

from collections.abc import Callable
from dataclasses import dataclass

from ideaos_agent.config import AppSettings
from ideaos_agent.domain.runtime import RuntimeModeSelection
from ideaos_agent.infrastructure.config.dotenv_store import DotenvModeStore


@dataclass(frozen=True)
class LocalConfigApplyResult:
    """Safe outcome of a local mode update and immediate settings reload."""

    created_from_template: bool
    effective_use_fake_llm: bool
    effective_use_fake_archive: bool
    process_environment_overrides: tuple[str, ...]


class LocalConfigService:
    """Apply a mode selection and report the settings effective for the next request."""

    def __init__(
        self,
        *,
        dotenv_store: DotenvModeStore,
        settings_loader: Callable[[], AppSettings],
        process_environment: dict[str, str],
    ) -> None:
        self._dotenv_store = dotenv_store
        self._settings_loader = settings_loader
        self._process_environment = process_environment

    def apply_runtime_modes(self, selection: RuntimeModeSelection) -> LocalConfigApplyResult:
        """Persist mode flags and return the settings used by the next dependency build."""

        # Reject unrelated invalid local settings before modifying either runtime flag.
        self._settings_loader()
        update = self._dotenv_store.update_modes(selection)
        settings = self._settings_loader()
        overrides = tuple(
            key
            for key in ("IDEAOS_USE_FAKE_LLM", "IDEAOS_USE_FAKE_ARCHIVE")
            if key in self._process_environment
        )
        return LocalConfigApplyResult(
            created_from_template=update.created_from_template,
            effective_use_fake_llm=settings.use_fake_llm,
            effective_use_fake_archive=settings.use_fake_archive,
            process_environment_overrides=overrides,
        )
