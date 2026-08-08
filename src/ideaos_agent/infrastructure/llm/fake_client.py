"""Fake LLM client used for tests and local demonstrations."""

import json

from ideaos_agent.infrastructure.llm.client import LlmClient


class FakeLlmClient(LlmClient):
    """Return deterministic wrapper responses without external API calls."""

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt

        if _looks_like_follow_up_prompt(user_prompt):
            return self._generate_follow_up_response(user_prompt)

        return self._generate_analysis_response(user_prompt)

    def _generate_analysis_response(self, user_prompt: str) -> str:
        raw_input = _extract_section(user_prompt, "【原始想法】", "【已有澄清回答】")
        clarification_block = _extract_section(user_prompt, "【已有澄清回答】", "【想法意图】")
        has_clarifications = clarification_block.strip() not in {"无", ""}
        has_solution_outline = any(
            marker in raw_input
            for marker in (
                "上传产品想法后",
                "输入产品点子后输出",
                "自动生成可行性分析",
                "市场分析、知识缺口、资源缺口和 MVP 步骤",
                "Web 工具",
                "SaaS 工具",
            )
        )

        if not has_clarifications and not has_solution_outline:
            return json.dumps(
                {
                    "archive_title": "独立开发者产品验证工具",
                    "input_echo": raw_input,
                    "needs_clarification": True,
                    "assumptions": [
                        "假设该工具面向独立开发者。",
                        "假设用户希望先判断想法是否值得继续推进。",
                    ],
                    "open_questions": [
                        "这个工具最核心要帮用户完成的验证动作是什么？",
                        "用户输入什么，系统要返回什么结果？",
                    ],
                    "clarification_rationale": (
                        "当前输入还看不出这个想法具体做什么，缺少核心动作与输入输出，"
                        "因此需要先澄清。"
                    ),
                    "analysis": None,
                },
                ensure_ascii=False,
            )

        intent = _extract_intent(user_prompt)
        market_copy = (
            "个人自用场景下，价值在于用最低成本判断一个想法值不值得继续投入，"
            "不需要考虑商业化路径。"
            if "自己用" in intent or "个人自用" in intent
            else "独立开发者与早期产品探索者有明确需求，但需要找到差异化入口。"
        )

        return json.dumps(
            {
                "archive_title": "独立开发者产品验证工具",
                "input_echo": raw_input,
                "needs_clarification": False,
                "assumptions": [
                    "假设用户愿意先接受文本报告形式的分析结果。",
                ],
                "open_questions": [
                    "后续是否需要把分析结果沉淀为可编辑的项目卡片？",
                ],
                "clarification_rationale": (
                    "输入已经形成可分析的解决方案轮廓，缺失的信息不会改变方向性结论，"
                    "因此直接分析。"
                ),
                "analysis": {
                    "summary": "这是一个帮助用户把产品想法转成结构化评估与执行建议的工具。",
                    "feasibility": "技术上可行，关键在于控制分析质量与用户信任预期。",
                    "market": market_copy,
                    "knowledge_gaps": ["产品验证方法", "Prompt 标准", "结果评估机制"],
                    "resource_gaps": ["真实种子用户", "稳定模型额度", "可对照的分析样本"],
                    "team_requirements": ["产品负责人", "Python 工程师", "AI 应用工程师"],
                    "similar_projects": ["创业想法分析助手", "MVP 规划助手", "产品验证顾问工具"],
                    "mvp_roadmap": ["接收原始想法输入", "输出结构化分析", "收集第一批用户反馈"],
                    "long_term_roadmap": ["提升分析稳定性", "加入结果编辑与保存", "准备对外测试"],
                },
            },
            ensure_ascii=False,
        )

    def _generate_follow_up_response(self, user_prompt: str) -> str:
        question = _extract_follow_up_question(user_prompt)
        clarification_block = _extract_follow_up_clarifications(user_prompt)
        has_clarifications = clarification_block.strip() not in {"none", "无", ""}
        needs_clarification = not has_clarifications and len(question) < 8

        if needs_clarification:
            return json.dumps(
                {
                    "archive_title": "独立开发者产品验证工具优化",
                    "input_echo": question,
                    "needs_clarification": True,
                    "assumptions": [
                        "假设你是希望进一步完善已有方案，而不是完全重做方向。"
                    ],
                    "open_questions": [
                        "你最想优先改进的是目标用户、核心功能，还是商业化路径？",
                        "你希望这次修改更偏向产品策略还是执行落地？",
                    ],
                    "clarification_rationale": (
                        "这次 follow-up 请求还不足以判断要修改哪个板块，因此先澄清。"
                    ),
                    "refinement_result": None,
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "archive_title": "独立开发者产品验证工具优化",
                "input_echo": question,
                "needs_clarification": False,
                "assumptions": [
                    "假设这次 follow-up 仍然围绕独立开发者产品验证场景，不更换主方向。"
                ],
                "open_questions": [
                    "下一轮可以继续打磨报告模板与结果沉淀方式。"
                ],
                "clarification_rationale": (
                    "本次 follow-up 已经能判断要收窄的目标用户板块，因此直接局部完善。"
                ),
                "refinement_result": {
                    "question_summary": question or "进一步完善当前方案",
                    "refinement_answer": (
                        "建议把产品定位进一步收窄到独立开发者在项目早期的"
                        "想法筛选与 MVP 决策支持。"
                    ),
                    "affected_sections": ["summary", "market", "mvp_roadmap"],
                    "proposed_section_updates": [
                        {
                            "section_key": "summary",
                            "change_summary": "收窄产品定位，强调想法筛选与 MVP 决策支持。",
                            "updated_text": (
                                "这是一个帮助独立开发者在项目早期完成想法筛选、"
                                "可行性判断与 MVP 决策支持的分析工具。"
                            ),
                            "updated_items": [],
                        },
                        {
                            "section_key": "market",
                            "change_summary": "更明确聚焦独立开发者早期决策场景。",
                            "updated_text": (
                                "目标用户聚焦为缺少产品研究资源的独立开发者，"
                                "他们在项目早期尤其需要低成本完成方向判断与 "
                                "MVP 优先级决策。"
                            ),
                            "updated_items": [],
                        },
                        {
                            "section_key": "mvp_roadmap",
                            "change_summary": "更聚焦首版 MVP 的核心动作。",
                            "updated_text": None,
                            "updated_items": [
                                "接收原始想法并提取核心目标用户与问题定义",
                                "输出结构化可行性分析与 MVP 建议",
                                "支持一轮 follow-up 精修并生成新版完整方案",
                            ],
                        },
                    ],
                    "next_actions": [
                        "确认是否保留当前目标用户聚焦。",
                        "确认后生成新版完整方案。",
                    ],
                },
            },
            ensure_ascii=False,
        )


def _extract_section(text: str, start_marker: str, end_marker: str) -> str:
    """Extract a labeled section from the prompt for deterministic fake responses."""

    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        return ""
    section = text[start + len(start_marker) : end]
    return section.strip()


def _extract_line_value(text: str, prefix: str) -> str:
    """Extract one prefixed line value from the prompt."""

    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def _extract_intent(text: str) -> str:
    """Extract the declared intent label from the analysis prompt."""

    return _extract_section(text, "【想法意图】", "【任务要求】").strip()


def _looks_like_follow_up_prompt(text: str) -> bool:
    """Detect the current follow-up prompt shape using stable markers."""

    return (
        "session_kind:" in text
        and "refinement_result" in text
        and "follow-up" in text
    )


def _extract_follow_up_question(text: str) -> str:
    """Extract the current follow-up question from the latest prompt shape."""

    question = _extract_line_value(text, "Follow-up question:")
    if question:
        return question

    return _extract_section(
        text,
        "【当前这次 follow-up 问题】",
        "【当前这次 follow-up 已有澄清回答】",
    )


def _extract_follow_up_clarifications(text: str) -> str:
    """Extract follow-up clarification answers from old or new prompt shapes."""

    clarification_block = _extract_section(
        text,
        "Existing clarification answers:",
        "Requirements:",
    )
    if clarification_block:
        return clarification_block

    return _extract_section(
        text,
        "【当前这次 follow-up 已有澄清回答】",
        "【任务要求】",
    )
