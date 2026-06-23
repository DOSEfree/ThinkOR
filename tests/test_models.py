from ideaos_agent.models import IdeaInput


def test_idea_input_accepts_content() -> None:
    payload = IdeaInput(content="我想做一个帮助孩子学习的应用。")

    assert payload.content.startswith("我想做")
