"""Run input-path diagnosis cases and write results to debug_runs/."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ideaos_agent.config import get_settings
from ideaos_agent.domain.errors import IdeaOsError
from ideaos_agent.infrastructure.llm.client import HttpLlmClient
from ideaos_agent.infrastructure.llm.parsing import parse_idea_analysis_response
from ideaos_agent.models import IdeaInput
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder

OUTPUT_DIR = Path("debug_runs")


@dataclass(frozen=True)
class DiagnosisCase:
    """Single diagnosis input case with an expected clarification mode."""

    name: str
    content: str
    expected_needs_clarification: bool


DEFAULT_CASES = [
    DiagnosisCase(
        name="short_product_idea",
        content="我想做一个帮助独立开发者快速验证产品想法的工具。",
        expected_needs_clarification=True,
    ),
    DiagnosisCase(
        name="more_specific_saas_idea",
        content=(
            "我想做一个 SaaS 工具，帮助独立开发者上传产品想法后，"
            "自动生成可行性分析、MVP 路线图和竞品方向判断。"
        ),
        expected_needs_clarification=False,
    ),
    DiagnosisCase(
        name="explicit_analysis_request",
        content=(
            "请分析这个具体创业想法：做一个面向独立开发者的 Web 工具，"
            "输入产品点子后输出市场分析、知识缺口、资源缺口和 MVP 步骤。"
        ),
        expected_needs_clarification=False,
    ),
    DiagnosisCase(
        name="near_blank_idea",
        content="我想创业。",
        expected_needs_clarification=True,
    ),
    DiagnosisCase(
        name="very_detailed_idea",
        content=(
            "我想做一个面向独立开发者的 Web SaaS，用户输入产品想法、目标用户和自己的技术背景后，"
            "系统用一次分析生成市场判断、知识缺口、资源缺口、MVP 步骤和后续路线图。"
            "首版只支持文本输入与报告导出，不做外部数据抓取，先按月订阅收费。"
        ),
        expected_needs_clarification=False,
    ),
]


def main() -> None:
    """Execute diagnosis cases and persist the artifact."""

    settings = get_settings()
    prompt_builder = IdeaAnalysisPromptBuilder()
    client = HttpLlmClient(
        provider=settings.llm_provider,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )

    results: list[dict[str, Any]] = []
    timestamp = datetime.now().astimezone().isoformat()

    for case in DEFAULT_CASES:
        idea_state = IdeaInput(content=case.content, clarifications=[])
        user_prompt = prompt_builder.build_user_prompt(
            idea_state.content,
            idea_state.clarifications,
        )
        record: dict[str, Any] = {
            "case": asdict(case),
            "input_length": len(case.content),
            "system_prompt_preview": prompt_builder.system_prompt[:800],
            "user_prompt_preview": user_prompt[:600],
            "request_summary": {
                "provider": settings.llm_provider,
                "base_url": settings.llm_base_url,
                "model": settings.llm_model,
                "timeout_seconds": settings.llm_timeout_seconds,
            },
        }

        try:
            raw_response = client.generate_text(
                system_prompt=prompt_builder.system_prompt,
                user_prompt=user_prompt,
            )
            parsed = parse_idea_analysis_response(raw_response)
            parsed_payload = parsed.model_dump()
            notes = infer_notes(
                case=case,
                raw_response=raw_response,
                parsed_response=parsed_payload,
            )
            record.update(
                {
                    "status": "success",
                    "raw_response": raw_response,
                    "parsed_response": parsed_payload,
                    "notes": notes,
                }
            )
        except IdeaOsError as exc:
            record.update(
                {
                    "status": "error",
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                    "notes": ["主链路返回项目级错误，请先看 error_message。"],
                }
            )
        except Exception as exc:  # pragma: no cover - defensive diagnosis guard
            record.update(
                {
                    "status": "error",
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                    "notes": ["出现未预期异常，需要人工进一步排查。"],
                }
            )

        results.append(record)

    payload = {
        "generated_at": timestamp,
        "purpose": "Phase 2 calibration diagnosis",
        "settings_summary": {
            "provider": settings.llm_provider,
            "base_url": settings.llm_base_url,
            "model": settings.llm_model,
            "timeout_seconds": settings.llm_timeout_seconds,
            "api_key_present": bool(settings.llm_api_key),
        },
        "results": results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-phase2-calibration-diagnosis.json"
    output_path = OUTPUT_DIR / filename
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Diagnosis artifact written to: {output_path}")


def infer_notes(
    *,
    case: DiagnosisCase,
    raw_response: str,
    parsed_response: dict[str, Any],
) -> list[str]:
    """Annotate the real model behavior for easier comparison."""

    notes: list[str] = []
    raw_lower = raw_response.lower()
    input_echo = str(parsed_response.get("input_echo", ""))
    needs_clarification = bool(parsed_response.get("needs_clarification"))
    analysis = parsed_response.get("analysis")

    if "占位符" in raw_response or "无效字符" in raw_response:
        notes.append("模型疑似将真实输入误判为占位符或无效字符。")

    if "placeholder" in raw_lower or "invalid" in raw_lower:
        notes.append("英文层面也出现了疑似占位或无效输入判断。")

    if input_echo != case.content:
        notes.append("input_echo 未忠实复述原始想法，存在改写或扩写。")
    else:
        notes.append("input_echo 与原始想法一致。")

    if needs_clarification != case.expected_needs_clarification:
        notes.append(
            "needs_clarification 与本轮校准目标不一致："
            f"期望 {case.expected_needs_clarification}，实际 {needs_clarification}。"
        )
    else:
        notes.append("needs_clarification 与本轮校准目标一致。")

    if needs_clarification and analysis is None:
        notes.append("模型进入澄清模式且未返回 analysis，契约一致。")
    elif not needs_clarification and isinstance(analysis, dict):
        notes.append("模型进入分析模式并返回了完整 analysis。")
    else:
        notes.append("模型返回模式与 analysis 结构存在异常，需人工复核。")

    return notes


if __name__ == "__main__":
    main()
