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
