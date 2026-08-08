"""Application service for the Phase 1 idea analysis flow."""

from ideaos_agent.config import AppSettings
from ideaos_agent.domain.errors import IdeaInputTooLongError, LlmNotConfiguredError
from ideaos_agent.infrastructure.llm.client import LlmClient
from ideaos_agent.infrastructure.llm.parsing import parse_idea_analysis_response
from ideaos_agent.models import IdeaAnalysisLlmOutput, IdeaInput
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder


class IdeaAnalysisService:
    """Coordinate the single-call LLM idea analysis flow."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        llm_client: LlmClient,
        prompt_builder: IdeaAnalysisPromptBuilder,
    ) -> None:
        self._settings = settings
        self._llm_client = llm_client
        self._prompt_builder = prompt_builder

    def analyze(self, payload: IdeaInput) -> IdeaAnalysisLlmOutput:
        """Analyze a user's idea through one LLM request."""

        content = payload.content.strip()
        clarification_size = sum(
            len(item.question.strip()) + len(item.answer.strip()) for item in payload.clarifications
        )
        if len(content) + clarification_size > self._settings.max_input_chars:
            raise IdeaInputTooLongError(
                f"想法输入过长，当前上限为 {self._settings.max_input_chars} 个字符。"
            )

        if not self._settings.use_fake_llm and not self._settings.llm_api_key:
            raise LlmNotConfiguredError("尚未配置 LLM API key，请在项目级 .env 中填写。")

        prompt = self._prompt_builder.build_user_prompt(
            content,
            payload.clarifications,
            intent=payload.intent,
        )
        response_text = self._llm_client.generate_text(
            system_prompt=self._prompt_builder.system_prompt,
            user_prompt=prompt,
        )
        return parse_idea_analysis_response(response_text)
