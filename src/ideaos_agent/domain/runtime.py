"""Safe runtime-mode values used by local configuration management."""

from dataclasses import dataclass


class RuntimeModeSelectionError(ValueError):
    """Raised when a runtime mode selection requires explicit acknowledgement."""


@dataclass(frozen=True)
class RuntimeModeSelection:
    """Non-secret LLM and archive mode choices requested by a local user."""

    use_fake_llm: bool
    use_fake_archive: bool
    acknowledge_fake_llm_real_archive: bool = False

    def validate(self) -> None:
        """Require a deliberate acknowledgement before real archive writes demo output."""

        if self.use_fake_llm and not self.use_fake_archive:
            if not self.acknowledge_fake_llm_real_archive:
                raise RuntimeModeSelectionError(
                    "Fake LLM with real archive requires explicit acknowledgement."
                )
