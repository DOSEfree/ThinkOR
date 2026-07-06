"""Fake LLM client used for tests and local demonstrations."""

import json

from ideaos_agent.infrastructure.llm.client import LlmClient


class FakeLlmClient(LlmClient):
    """Return deterministic wrapper responses without calling an external API."""

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt

        raw_input = _extract_section(user_prompt, "【原始想法】", "【已有澄清回答】")
        clarification_block = _extract_section(user_prompt, "【已有澄清回答】", "【任务要求】")
        has_clarifications = clarification_block.strip() != "无"
        has_solution_outline = any(
            marker in raw_input
            for marker in (
                "上传产品想法后",
                "输入产品点子后输出",
                "自动生成可行性分析",
                "市场分析、知识缺口、资源缺口和 MVP 步骤",
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
                    "analysis": None,
                },
                ensure_ascii=False,
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
                "analysis": {
                    "summary": "这是一个帮助用户把产品想法转成结构化评估与执行建议的工具。",
                    "feasibility": "技术上可行，关键在于控制分析质量与用户信任预期。",
                    "market": "独立开发者与早期产品探索者有明确需求，但需要找到差异化入口。",
                    "knowledge_gaps": ["产品验证方法", "Prompt 校准", "结果评估机制"],
                    "resource_gaps": ["真实种子用户", "稳定模型额度", "可对照的分析样本"],
                    "team_requirements": ["产品负责人", "Python 工程师", "AI 应用工程师"],
                    "similar_projects": ["创业想法分析助手", "MVP 规划助手", "产品验证顾问工具"],
                    "mvp_roadmap": ["接收原始想法输入", "输出结构化分析", "收集第一批用户反馈"],
                    "long_term_roadmap": ["提升分析稳定性", "加入结果编辑与保存", "准备对外测试"],
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
