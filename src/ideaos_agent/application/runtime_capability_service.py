"""Read the effective non-secret runtime capability state."""

from dataclasses import dataclass

from ideaos_agent.config import AppSettings
from ideaos_agent.infrastructure.archive.lark_cli_status import LarkCliStatus, LarkCliStatusAdapter


@dataclass(frozen=True)
class RuntimeCapabilities:
    use_fake_llm: bool
    use_fake_archive: bool
    llm_state: str
    llm_missing_items: tuple[str, ...]
    archive_state: str
    lark: LarkCliStatus | None


class RuntimeCapabilityService:
    """Map settings into UI-facing readiness without accessing any secret value."""

    def __init__(self, *, settings: AppSettings, lark_adapter: LarkCliStatusAdapter) -> None:
        self._settings = settings
        self._lark_adapter = lark_adapter

    def get_capabilities(self) -> RuntimeCapabilities:
        missing_items = tuple(
            name
            for name, value in (
                ("api_key", self._settings.llm_api_key),
                ("model", self._settings.llm_model),
            )
            if not value.strip()
        )
        if self._settings.use_fake_llm:
            llm_state = "fake"
        elif missing_items:
            llm_state = "not_configured"
        else:
            llm_state = "configured_unverified"

        if self._settings.use_fake_archive:
            return RuntimeCapabilities(
                use_fake_llm=self._settings.use_fake_llm,
                use_fake_archive=True,
                llm_state=llm_state,
                llm_missing_items=missing_items,
                archive_state="fake",
                lark=None,
            )
        lark = self._lark_adapter.inspect()
        return RuntimeCapabilities(
            use_fake_llm=self._settings.use_fake_llm,
            use_fake_archive=False,
            llm_state=llm_state,
            llm_missing_items=missing_items,
            archive_state=lark.availability,
            lark=lark,
        )
