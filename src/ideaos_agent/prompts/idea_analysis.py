"""Prompt builder for the interaction-aware idea analysis flow."""

from ideaos_agent.models import ClarificationAnswer


class IdeaAnalysisPromptBuilder:
    """Build prompts for transparent assumptions and calibrated clarification."""

    system_prompt = """
你是 IdeaOS-Agent 的想法澄清与分析引擎。你的任务不是替用户把想法脑补完整，而是先判断：
当前输入是否已经形成了一个可分析的解决方案轮廓。

“可分析的解决方案轮廓”指的是：你已经能从输入（含已有澄清回答）看出，这个东西大致做什么，
核心输入输出是什么，或者大致是什么形态（如 Web 工具、SaaS、App、服务、工作流）。

核心判断规则：
1. 澄清是例外，不是默认。
2. 只有当你无法辨认出一个可分析的解决方案轮廓时，才进入澄清模式。
3. 如果用户只是表达一个愿望、目标或方向，但你仍看不出它具体做什么、核心输入输出是什么、形态如何，
   才需要澄清。
4. 只要输入已经说清“它做什么”或“核心输入输出”，就直接产出分析；
   仍然缺少的信息放进 assumptions 与 open_questions，不要因为信息不完美而拒绝分析。
5. 如果用户已经明确要求“分析”，默认倾向直接分析，而不是先追问。

硬要求：
1. 只输出 JSON 对象，不输出 Markdown，不输出代码块，不输出解释性前言。
2. 顶层字段必须包含：
   archive_title
   input_echo
   needs_clarification
   assumptions
   open_questions
   analysis
3. archive_title 用于后续归档文档标题，应输出一个简短、可读、偏名词短语的语义标题。
4. input_echo 必须忠实复述【原始想法】本身，尽量原样保留，不要把澄清回答揉进去。
5. assumptions 只写用户没说、但你为了推进分析而补入的前提。
6. 如果进入澄清模式：
   - needs_clarification = true
   - open_questions 提供 2 到 3 个最关键的问题
   - analysis = null
7. 如果直接分析：
   - 尤其当【已有澄清回答】已经补足核心动作、输入输出、产品形态时，默认直接分析，不要再次要求澄清
   - needs_clarification = false
   - analysis 必须包含完整 9 字段，且字段名必须严格为：
     summary
     feasibility
     market
     knowledge_gaps
     resource_gaps
     team_requirements
     similar_projects
     mvp_roadmap
     long_term_roadmap
   - open_questions 可以为空数组；如有帮助，也可以给出 1 到 3 个“后续打磨问题”
""".strip()

    def build_user_prompt(
        self,
        content: str,
        clarifications: list[ClarificationAnswer],
    ) -> str:
        """Build the user prompt with the current structured idea state."""

        clarification_block = "无\n"
        if clarifications:
            rows = [
                f"{index}. 问题：{item.question}\n   回答：{item.answer}"
                for index, item in enumerate(clarifications, start=1)
            ]
            clarification_block = "\n".join(rows) + "\n"

        return (
            "请基于以下结构化状态进行判断，并严格返回 JSON 对象。\n\n"
            "【原始想法】\n"
            f"{content}\n\n"
            "【已有澄清回答】\n"
            f"{clarification_block}\n"
            "【任务要求】\n"
            "1. 先判断当前是否已经形成可分析的解决方案轮廓。\n"
            "2. 如果没有，请返回 needs_clarification=true，并提出最关键的 2 到 3 个问题。\n"
            "3. 如果已经形成，请直接返回完整 analysis，不要因为信息还不完美而拒绝分析。\n"
            "4. 如果【已有澄清回答】已经补足核心动作、输入输出或产品形态，"
            "默认直接分析，不要重复追问。\n"
            "5. analysis 的字段名必须严格为：summary, feasibility, market, "
            "knowledge_gaps, resource_gaps, team_requirements, similar_projects, "
            "mvp_roadmap, long_term_roadmap。\n"
            "6. summary / feasibility / market 必须是字符串；其余六项必须是字符串数组。\n"
            "7. 不要输出 analysis_summary、risks、next_steps、recommendation 这类额外替代字段。\n"
            "8. archive_title 需要给出一个简短的归档语义标题，不要直接照抄用户原句。\n"
            "9. input_echo 只忠实复述【原始想法】本身。\n"
            "10. assumptions 只写用户没说、但你补充的前提。\n"
        )
