"""Domain-level error types for the thin vertical slice."""


class IdeaOsError(Exception):
    """Base error for project-specific failures."""


class IdeaInputTooLongError(IdeaOsError):
    """Raised when the input idea exceeds the configured maximum length."""


class LlmNotConfiguredError(IdeaOsError):
    """Raised when no usable LLM configuration is available."""


class LlmTimeoutError(IdeaOsError):
    """Raised when the LLM call times out."""


class LlmRequestError(IdeaOsError):
    """Raised when the upstream LLM provider request fails."""


class LlmResponseFormatError(IdeaOsError):
    """Raised when the LLM output cannot be parsed into IdeaAnalysis."""

    def __init__(self, message: str, *, raw_output: str | None = None) -> None:
        super().__init__(message)
        self.raw_output = raw_output


class SessionNotFoundError(IdeaOsError):
    """Raised when a requested session or snapshot cannot be found locally."""


class SessionStateError(IdeaOsError):
    """Raised when a session exists but its state/kind is invalid for an operation."""
