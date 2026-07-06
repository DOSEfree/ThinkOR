from ideaos_agent.domain.errors import LlmResponseFormatError
from ideaos_agent.infrastructure.llm.parsing import (
    parse_follow_up_response,
    parse_idea_analysis_response,
)


def test_parse_idea_analysis_response_surfaces_field_level_summary() -> None:
    raw = """
    {
      "archive_title": "测试标题",
      "input_echo": "原始输入",
      "needs_clarification": false,
      "assumptions": [],
      "open_questions": [],
      "analysis": {
        "summary": ["摘要"],
        "feasibility": "可行",
        "market": "市场",
        "knowledge_gaps": ["gap"]
      }
    }
    """

    try:
        parse_idea_analysis_response(raw)
    except LlmResponseFormatError as exc:
        assert "analysis.summary" in str(exc)
    else:
        raise AssertionError("Expected LlmResponseFormatError to be raised.")


def test_parse_follow_up_response_coerces_single_update_object_to_list() -> None:
    raw = """
    {
      "archive_title": "目标用户收窄",
      "input_echo": "我想把目标用户进一步收窄。",
      "needs_clarification": false,
      "assumptions": [],
      "open_questions": [],
      "refinement_result": {
        "question_summary": "收窄目标用户",
        "refinement_answer": "建议聚焦缺少产品背景的独立开发者。",
        "affected_sections": "market",
        "proposed_section_updates": {
          "section_key": "market",
          "change_summary": "改写目标用户定位。",
          "updated_text": "目标用户聚焦为缺少产品背景的独立开发者。",
          "updated_items": []
        },
        "next_actions": "确认后生成新版完整方案。"
      }
    }
    """

    result = parse_follow_up_response(raw)

    assert result.refinement_result is not None
    assert result.refinement_result.affected_sections[0].value == "market"
    assert len(result.refinement_result.proposed_section_updates) == 1
    assert result.refinement_result.proposed_section_updates[0].section_key.value == "market"
    assert result.refinement_result.next_actions == ["确认后生成新版完整方案。"]


def test_parse_follow_up_response_coerces_null_list_fields() -> None:
    raw = """
    {
      "archive_title": "目标用户收窄",
      "input_echo": "我想把目标用户进一步收窄。",
      "needs_clarification": false,
      "assumptions": null,
      "open_questions": null,
      "refinement_result": {
        "question_summary": "收窄目标用户",
        "refinement_answer": "建议聚焦缺少产品背景的独立开发者。",
        "affected_sections": null,
        "proposed_section_updates": {
          "section_key": "market",
          "change_summary": "改写目标用户定位。",
          "updated_text": "目标用户聚焦为缺少产品背景的独立开发者。",
          "updated_items": null
        },
        "next_actions": null
      }
    }
    """

    result = parse_follow_up_response(raw)

    assert result.assumptions == []
    assert result.open_questions == []
    assert result.refinement_result is not None
    assert result.refinement_result.affected_sections[0].value == "market"
    assert result.refinement_result.proposed_section_updates[0].updated_items == []
    assert result.refinement_result.next_actions == []
