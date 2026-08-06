"""Contract tests for the v0.8.0 clarification protocol.

These tests run in CI without a real LLM: they pin the prompt structure, the
parser behavior, the fake-client demo output, and the eval-case schema. Real
judgment quality is measured separately with evals/run_eval.py.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ideaos_agent.infrastructure.llm.fake_client import FakeLlmClient
from ideaos_agent.infrastructure.llm.parsing import parse_idea_analysis_response
from ideaos_agent.models import IdeaInput
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder

EVAL_CASES_PATH = Path(__file__).resolve().parents[1] / "evals" / "clarification_cases.json"
VALID_CATEGORIES = {"vague", "clear", "personal", "commercial", "explicit_analysis", "edge"}


def test_prompt_contains_judgment_protocol_and_rationale_requirement() -> None:
    builder = IdeaAnalysisPromptBuilder()

    assert "改变分析结论" in builder.system_prompt
    assert "clarification_rationale" in builder.system_prompt
    assert "个人自用" in builder.system_prompt

    prompt = builder.build_user_prompt("我想做一个工具。", [])
    assert "【想法意图】" in prompt
    assert "clarification_rationale 必须输出一句简短理由" in prompt


def test_prompt_includes_intent_label() -> None:
    builder = IdeaAnalysisPromptBuilder()

    personal_prompt = builder.build_user_prompt("我想做一个工具。", [], intent="personal")
    assert "个人自用" in personal_prompt
    assert "不打算做成商业化产品" in personal_prompt

    default_prompt = builder.build_user_prompt("我想做一个工具。", [])
    assert "未指定（由你判断）" in default_prompt

    product_prompt = builder.build_user_prompt("我想做一个工具。", [], intent="product")
    assert "想做成产品" in product_prompt


def test_idea_input_validates_intent() -> None:
    assert IdeaInput(content="做一个工具", intent="personal").intent == "personal"
    assert IdeaInput(content="做一个工具", intent=None).intent is None

    with pytest.raises(ValidationError):
        IdeaInput(content="做一个工具", intent="unknown")


def test_parser_accepts_and_normalizes_rationale() -> None:
    raw_with = """
    {
      "archive_title": "工具分析",
      "input_echo": "我想做一个工具。",
      "needs_clarification": true,
      "assumptions": [],
      "open_questions": ["做什么？", "给谁用？"],
      "clarification_rationale": "还看不出这个想法具体做什么。",
      "analysis": null
    }
    """
    parsed = parse_idea_analysis_response(raw_with)
    assert parsed.clarification_rationale == "还看不出这个想法具体做什么。"

    raw_without = """
    {
      "archive_title": "工具分析",
      "input_echo": "我想做一个工具。",
      "needs_clarification": true,
      "assumptions": [],
      "open_questions": ["做什么？", "给谁用？"],
      "analysis": null
    }
    """
    assert parse_idea_analysis_response(raw_without).clarification_rationale is None

    raw_blank = raw_with.replace(
        '"clarification_rationale": "还看不出这个想法具体做什么。"',
        '"clarification_rationale": "   "',
    )
    assert parse_idea_analysis_response(raw_blank).clarification_rationale is None


def test_fake_client_emits_rationale_and_intent_aware_market() -> None:
    builder = IdeaAnalysisPromptBuilder()
    client = FakeLlmClient()
    content = (
        "我想做一个 SaaS 工具，帮助独立开发者上传产品想法后，"
        "自动生成可行性分析、MVP 路线图和竞品方向判断。"
    )

    personal_prompt = builder.build_user_prompt(content, [], intent="personal")
    personal = parse_idea_analysis_response(
        client.generate_text(
            system_prompt=builder.system_prompt,
            user_prompt=personal_prompt,
        )
    )
    assert personal.needs_clarification is False
    assert personal.clarification_rationale
    assert personal.analysis is not None
    assert "个人自用" in personal.analysis.market

    default_prompt = builder.build_user_prompt(content, [])
    default = parse_idea_analysis_response(
        client.generate_text(
            system_prompt=builder.system_prompt,
            user_prompt=default_prompt,
        )
    )
    assert default.needs_clarification is False
    assert default.clarification_rationale
    assert default.analysis is not None
    assert "差异化" in default.analysis.market


def test_eval_cases_schema_valid() -> None:
    payload = json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert isinstance(cases, list) and len(cases) >= 10

    seen_ids: set[str] = set()
    for case in cases:
        case_id = str(case["id"])
        assert case_id not in seen_ids, f"duplicate case id: {case_id}"
        seen_ids.add(case_id)
        assert case["category"] in VALID_CATEGORIES, f"unknown category: {case['category']}"
        assert isinstance(case["expected"]["needs_clarification"], bool)
        assert str(case["input"]).strip()