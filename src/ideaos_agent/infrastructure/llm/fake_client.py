"""Fake LLM client used for tests and local demonstrations."""

import json

from ideaos_agent.infrastructure.llm.client import LlmClient


class FakeLlmClient(LlmClient):
    """Return a deterministic full response without calling any external API."""

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt
        del user_prompt

        return json.dumps(
            {
                "summary": "这是一个帮助用户把模糊想法转成执行计划的工具。",
                "feasibility": "技术上可行，关键挑战在于输出稳定性与用户信任建立。",
                "market": "目标用户是独立开发者与早期产品负责人，需求真实但竞争认知需要验证。",
                "knowledge_gaps": ["Prompt 设计", "产品验证方法", "基础后端开发"],
                "resource_gaps": ["模型额度", "真实用户反馈", "清晰的评估标准"],
                "team_requirements": ["产品负责人", "Python 工程师", "AI 应用工程师"],
                "similar_projects": ["创业点子分析助手", "MVP 规划助手", "产品验证顾问工具"],
                "mvp_roadmap": ["接收原始想法输入", "输出 9 个模块", "收集第一批反馈"],
                "long_term_roadmap": ["提升各模块质量", "加入可编辑结果页面", "准备对外发布"],
            },
            ensure_ascii=False,
        )
