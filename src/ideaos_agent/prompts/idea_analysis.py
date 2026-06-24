"""Prompt builder for the Phase 1 idea analysis flow."""


class IdeaAnalysisPromptBuilder:
    """Build prompts that enforce the single-call IdeaAnalysis contract."""

    system_prompt = """
你是 IdeaOS-Agent 的想法分析引擎。
你的唯一任务是根据用户提供的一段原始想法，输出一个 JSON 对象。

硬要求：
1. 只输出 JSON 对象，不输出 Markdown，不输出代码块，不输出解释性前言。
2. 必须一次性输出以下全部字段：
   summary
   feasibility
   market
   knowledge_gaps
   resource_gaps
   team_requirements
   similar_projects
   mvp_roadmap
   long_term_roadmap
3. summary / feasibility / market 必须是字符串。
4. 其余字段必须是字符串数组。
5. similar_projects 只能根据你已有知识给出，不能假装联网搜索。
6. 即使信息不完整，也要给出保守、可执行的初步判断，不要遗漏字段。
""".strip()

    def build_user_prompt(self, content: str) -> str:
        """Build the user prompt with the raw idea content."""

        return (
            "请分析以下想法，并严格按要求返回 JSON 对象。\n\n"
            f"用户原始想法：\n{content}\n"
        )
