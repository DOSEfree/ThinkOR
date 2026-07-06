"""Prompt builder for bounded follow-up refinement requests."""

import json

from ideaos_agent.domain.session import SessionClarificationRecord, SessionSnapshot


class FollowUpPromptBuilder:
    """Build prompts for v0.2.5 follow-up refinement requests."""

    system_prompt = """
你是 IdeaOS-Agent 的 follow-up 局部完善引擎。你的任务不是重写整份方案，
而是基于上一版完整分析，只回答用户这一次继续追问或想修改的局部方向。

核心判断规则：
1. 澄清是例外，不是默认。
2. 只有当用户这次 follow-up 请求仍然过于含糊，你无法判断要改哪一部分时，才进入澄清模式。
3. 如果你已经能判断用户想收窄、补强或调整哪一块，就直接返回 refinement_result。
4. 你只修改真正受影响的 section，不要重写无关 section。

硬要求：
1. 只输出 JSON 对象，不输出 Markdown，不输出代码块，不输出解释性前言。
2. 顶层字段必须包含：
   archive_title
   input_echo
   needs_clarification
   assumptions
   open_questions
   refinement_result
3. input_echo 只忠实复述【当前这次 follow-up 问题】本身，不要混入原始想法或旧分析。
4. archive_title 仍应输出一个简短、可读、偏名词短语的语义标题。
5. 如果进入澄清模式：
   - needs_clarification = true
   - open_questions 提供 2 到 3 个最关键的问题
   - refinement_result = null
6. 如果直接完善：
   - needs_clarification = false
   - refinement_result 必须包含且只包含以下字段：
     question_summary
     refinement_answer
     affected_sections
     proposed_section_updates
     next_actions
7. affected_sections 必须是字符串数组。
8. proposed_section_updates 必须是 JSON 数组，即使只有 1 条也必须返回数组，不能返回单个对象。
9. proposed_section_updates 的每一项必须包含：
   section_key
   change_summary
   updated_text
   updated_items
10. 当 section_key 属于 summary / feasibility / market 时：
   - updated_text 必须为字符串
   - updated_items 必须为空数组
11. 当 section_key 属于 knowledge_gaps / resource_gaps / team_requirements /
    similar_projects / mvp_roadmap / long_term_roadmap 时：
   - updated_items 必须为字符串数组
   - updated_text 必须为 null
12. next_actions 必须是字符串数组，可以为空数组。
13. 不要输出 section_updates、updated_section、final_plan、analysis 这类替代字段。
""".strip()

    def build_refinement_prompt(
        self,
        *,
        parent_snapshot: SessionSnapshot,
        question: str,
        clarifications: list[SessionClarificationRecord],
    ) -> str:
        """Build the follow-up refinement prompt from the parent snapshot."""

        clarification_lines = ["none"]
        if clarifications:
            clarification_lines = [
                f"{index}. question: {item.question}\n   answer: {item.answer}"
                for index, item in enumerate(clarifications, start=1)
            ]

        parent_analysis = parent_snapshot.analysis
        if parent_analysis is None:
            raise ValueError("Follow-up prompts require a parent snapshot with analysis.")

        analysis_json = json.dumps(parent_analysis.model_dump(), ensure_ascii=False)
        return (
            "请基于以下结构化状态进行 follow-up 局部完善，并严格返回 JSON 对象。\n\n"
            "【父会话信息】\n"
            f"session_id: {parent_snapshot.session_id}\n"
            f"session_kind: {parent_snapshot.session_kind.value}\n"
            f"archive_title: {parent_snapshot.archive_title}\n\n"
            "【原始想法】\n"
            f"{parent_snapshot.original_content}\n\n"
            "【上一版完整分析】\n"
            f"{analysis_json}\n\n"
            "【当前这次 follow-up 问题】\n"
            f"{question}\n\n"
            "【当前这次 follow-up 已有澄清回答】\n"
            f"{chr(10).join(clarification_lines)}\n\n"
            "【任务要求】\n"
            "1. 先判断当前这次 follow-up 是否已经足够明确，可以直接局部完善。\n"
            "2. 如果可以，请直接返回 refinement_result，不要因为信息还不完美就再次追问。\n"
            "3. 如果不可以，请返回 needs_clarification=true，并提出 2 到 3 个最关键的问题。\n"
            "4. refinement_result 只修改真正受影响的 section，不要重写整份 analysis。\n"
            "5. affected_sections 必须是字符串数组。\n"
            "6. proposed_section_updates 必须严格是数组；即使只有一条更新，也要写成 [ {...} ]。\n"
            "7. 每条 proposed_section_updates 都必须同时给出 section_key、change_summary、"
            "updated_text、updated_items 这四个字段。\n"
            "8. 文本 section 使用 updated_text；列表 section 使用 updated_items。\n"
            "9. next_actions 必须是字符串数组，可以为空数组。\n"
            "10. input_echo 只忠实复述【当前这次 follow-up 问题】本身。\n"
        )
