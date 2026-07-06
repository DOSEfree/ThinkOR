import json

from ideaos_agent.application.idea_analysis_service import IdeaAnalysisService
from ideaos_agent.config import AppSettings
from ideaos_agent.infrastructure.llm.client import LlmClient
from ideaos_agent.models import ClarificationAnswer, IdeaInput
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder


class MockLlmClient(LlmClient):
    """Configurable mock client that records prompts and returns queued responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls: list[dict[str, str]] = []

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self._responses.pop(0)


def build_service(responses: list[dict[str, object]]) -> tuple[IdeaAnalysisService, MockLlmClient]:
    client = MockLlmClient([json.dumps(item, ensure_ascii=False) for item in responses])
    service = IdeaAnalysisService(
        settings=AppSettings(
            llm_api_key="fake-key",
            use_fake_llm=False,
            max_input_chars=4000,
        ),
        llm_client=client,
        prompt_builder=IdeaAnalysisPromptBuilder(),
    )
    return service, client


def test_thin_input_triggers_clarification_and_preserves_input_echo() -> None:
    raw_input = "我想做一个帮助独立开发者快速验证产品想法的工具。"
    service, _client = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": raw_input,
                "needs_clarification": True,
                "assumptions": [
                    "假设该工具面向独立开发者。",
                    "假设用户想先判断想法值不值得继续推进。",
                ],
                "open_questions": [
                    "这个工具最核心要帮用户完成的验证动作是什么？",
                    "用户输入什么，系统要返回什么结果？",
                ],
                "analysis": None,
            }
        ]
    )

    result = service.analyze(IdeaInput(content=raw_input))

    assert result.input_echo == raw_input
    assert result.needs_clarification is True
    assert result.analysis is None
    assert len(result.open_questions) == 2
    assert result.assumptions


def test_two_step_flow_uses_stateless_clarifications() -> None:
    raw_input = "我想做一个帮助独立开发者验证产品想法的工具。"
    service, client = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": raw_input,
                "needs_clarification": False,
                "assumptions": ["假设该工具先以 Web 形式提供。"],
                "open_questions": [],
                "analysis": {
                    "summary": "这是一个帮助独立开发者验证产品想法的 Web 工具。",
                    "feasibility": "技术可行。",
                    "market": "目标用户较明确。",
                    "knowledge_gaps": ["产品验证方法"],
                    "resource_gaps": ["种子用户"],
                    "team_requirements": ["产品负责人"],
                    "similar_projects": ["创业想法分析工具"],
                    "mvp_roadmap": ["定义最小输入输出"],
                    "long_term_roadmap": ["迭代交互体验"],
                },
            }
        ]
    )

    result = service.analyze(
        IdeaInput(
            content=raw_input,
            clarifications=[
                ClarificationAnswer(
                    question="你最想帮用户验证什么？",
                    answer="先判断这个想法值不值得继续做。",
                ),
                ClarificationAnswer(
                    question="你希望输出更偏建议还是更偏执行步骤？",
                    answer="先给建议，再给轻量执行步骤。",
                ),
            ],
        )
    )

    assert result.input_echo == raw_input
    assert result.needs_clarification is False
    assert result.analysis is not None
    user_prompt = client.calls[0]["user_prompt"]
    assert "【已有澄清回答】" in user_prompt
    assert "先判断这个想法值不值得继续做。" in user_prompt


def test_input_echo_faithfully_restates_input_in_analysis_mode() -> None:
    raw_input = "我想做一个帮助独立开发者快速验证产品想法的工具。"
    service, _client = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": raw_input,
                "needs_clarification": False,
                "assumptions": ["假设它以 Web 形式提供。"],
                "open_questions": [],
                "analysis": {
                    "summary": "这是一个帮助独立开发者快速验证产品想法的工具。",
                    "feasibility": "技术上可做，但需要进一步明确范围。",
                    "market": "目标用户是独立开发者。",
                    "knowledge_gaps": ["产品验证框架"],
                    "resource_gaps": ["种子用户"],
                    "team_requirements": ["产品负责人"],
                    "similar_projects": ["创业想法分析工具"],
                    "mvp_roadmap": ["先收集用户输入"],
                    "long_term_roadmap": ["逐步提升交互模型"],
                },
            }
        ]
    )

    result = service.analyze(IdeaInput(content=raw_input))

    assert result.input_echo == raw_input
    assert result.analysis is not None


def test_assumptions_are_kept_outside_analysis_fields() -> None:
    service, _client = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": "我想做一个帮助独立开发者验证产品想法的工具。",
                "needs_clarification": False,
                "assumptions": ["假设该工具最终会采用订阅制。"],
                "open_questions": [],
                "analysis": {
                    "summary": "这是一个帮助独立开发者验证产品想法的工具。",
                    "feasibility": "技术上可行，但商业模式仍需验证。",
                    "market": "市场存在需求。",
                    "knowledge_gaps": ["定价策略"],
                    "resource_gaps": ["真实反馈"],
                    "team_requirements": ["产品负责人"],
                    "similar_projects": ["创业想法分析工具"],
                    "mvp_roadmap": ["定义最小输入输出"],
                    "long_term_roadmap": ["逐步迭代商业模式"],
                },
            }
        ]
    )

    result = service.analyze(IdeaInput(content="我想做一个帮助独立开发者验证产品想法的工具。"))

    assert result.assumptions == ["假设该工具最终会采用订阅制。"]
    assert result.analysis is not None
    assert "订阅制" not in result.analysis.summary


def test_specific_input_can_stay_in_analysis_mode_without_clarification() -> None:
    raw_input = (
        "我想做一个 SaaS 工具，帮助独立开发者上传产品想法后，"
        "自动生成可行性分析、MVP 路线图和竞品方向判断。"
    )
    service, _client = build_service(
        [
            {
                "archive_title": "独立开发者 SaaS 分析工具",
                "input_echo": raw_input,
                "needs_clarification": False,
                "assumptions": ["假设首版只支持文本输入。"],
                "open_questions": ["是否需要在首版支持报告保存与分享？"],
                "analysis": {
                    "summary": "这是一个面向独立开发者的 SaaS 分析工具。",
                    "feasibility": "技术路径清楚，首版可行。",
                    "market": "目标用户与价值主张都较明确。",
                    "knowledge_gaps": ["结果质量评估"],
                    "resource_gaps": ["种子用户样本"],
                    "team_requirements": ["产品负责人", "AI 应用工程师"],
                    "similar_projects": ["创业想法分析工具", "MVP 规划助手"],
                    "mvp_roadmap": ["定义输入输出结构", "接入模型并返回结构化报告"],
                    "long_term_roadmap": ["提升分析稳定性", "扩展协作能力"],
                },
            }
        ]
    )

    result = service.analyze(IdeaInput(content=raw_input))

    assert result.input_echo == raw_input
    assert result.needs_clarification is False
    assert result.analysis is not None
    assert result.open_questions == ["是否需要在首版支持报告保存与分享？"]


def test_stateless_request_contains_entire_idea_state() -> None:
    service, client = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": "我想做一个帮助独立开发者验证产品想法的工具。",
                "needs_clarification": True,
                "assumptions": ["假设目标用户是独立开发者。"],
                "open_questions": [
                    "你最想验证什么？",
                    "希望输出建议还是执行计划？",
                ],
                "analysis": None,
            }
        ]
    )

    service.analyze(
        IdeaInput(
            content="我想做一个帮助独立开发者验证产品想法的工具。",
            clarifications=[
                ClarificationAnswer(
                    question="你最想验证什么？",
                    answer="先验证这个想法值不值得继续推进。",
                )
            ],
        )
    )

    prompt = client.calls[0]["user_prompt"]
    assert "【原始想法】" in prompt
    assert "【已有澄清回答】" in prompt
    assert "先验证这个想法值不值得继续推进。" in prompt


def test_prompt_explicitly_lists_required_analysis_fields() -> None:
    service, client = build_service(
        [
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": "我想做一个帮助独立开发者验证产品想法的工具。",
                "needs_clarification": True,
                "assumptions": [],
                "open_questions": ["你最想验证什么？", "用户输入什么，系统输出什么？"],
                "analysis": None,
            }
        ]
    )

    service.analyze(IdeaInput(content="我想做一个帮助独立开发者验证产品想法的工具。"))

    prompt = client.calls[0]["user_prompt"]
    assert "analysis 的字段名必须严格为" in prompt
    assert "summary, feasibility, market" in prompt
