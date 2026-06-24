"""LLM client abstractions and HTTP implementation."""

from abc import ABC, abstractmethod

import httpx

from ideaos_agent.domain.errors import (
    LlmNotConfiguredError,
    LlmRequestError,
    LlmTimeoutError,
)


class LlmClient(ABC):
    """Abstract LLM client boundary used by the application layer."""

    @abstractmethod
    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Generate a single text response for the provided prompts."""


class HttpLlmClient(LlmClient):
    """Minimal HTTP-based LLM client using an OpenAI-compatible payload."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self._provider = provider
        self._base_url = base_url.strip()
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._timeout_seconds = timeout_seconds

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Call the configured provider exactly once and return plain text."""

        if not self._base_url or not self._model or not self._api_key:
            raise LlmNotConfiguredError("LLM base URL、model 或 API key 未完整配置。")

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-IdeaOS-Provider": self._provider,
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(self._base_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LlmTimeoutError("LLM 调用超时，请稍后重试。") from exc
        except httpx.HTTPError as exc:
            raise LlmRequestError(f"LLM 调用失败：{exc}") from exc

        return self._extract_content(response.json())

    @staticmethod
    def _extract_content(payload: object) -> str:
        """Extract assistant text from a compatible response payload."""

        if not isinstance(payload, dict):
            raise LlmRequestError("LLM 响应格式异常：顶层不是对象。")

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmRequestError("LLM 响应格式异常：缺少 choices。")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LlmRequestError("LLM 响应格式异常：choice 结构错误。")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LlmRequestError("LLM 响应格式异常：缺少 message。")

        content = message.get("content")
        if not isinstance(content, str):
            raise LlmRequestError("LLM 响应格式异常：message.content 不是字符串。")

        return content
