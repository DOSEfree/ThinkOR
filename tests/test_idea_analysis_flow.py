from fastapi.testclient import TestClient

from ideaos_agent.main import app


def test_idea_analysis_rejects_empty_input() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/idea-analysis", json={"content": ""})

    assert response.status_code == 422


def test_idea_analysis_rejects_blank_only_input() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/idea-analysis", json={"content": "   "})

    assert response.status_code == 422


def test_idea_analysis_rejects_input_that_is_too_long(monkeypatch) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_MAX_INPUT_CHARS", "10")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={"content": "这是一个明显超过长度限制的想法描述。"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "idea_input_too_long"


def test_idea_analysis_requires_key_when_not_using_fake_llm(monkeypatch) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "false")
    monkeypatch.delenv("IDEAOS_LLM_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post("/api/v1/idea-analysis", json={"content": "我想做一个想法分析工具。"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "llm_not_configured"


def test_idea_analysis_accepts_clarifications_with_fake_llm(monkeypatch) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={
            "content": "我想做一个帮助独立开发者验证产品想法的工具。",
            "clarifications": [
                {
                    "question": "你最想帮用户验证什么？",
                    "answer": "我最想先帮助他们判断想法值不值得继续做。",
                },
                {
                    "question": "你希望输出偏建议还是偏执行计划？",
                    "answer": "先给建议，再给一个轻量计划。",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["input_echo"] == "我想做一个帮助独立开发者验证产品想法的工具。"
    assert body["needs_clarification"] is False
    assert body["analysis"]["summary"]
