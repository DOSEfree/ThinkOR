from fastapi.testclient import TestClient

from ideaos_agent.main import app


def test_healthcheck_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_exposes_basic_metadata() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_idea_analysis_endpoint_returns_fake_response(monkeypatch) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_MAX_INPUT_CHARS", "4000")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={"content": "我想做一个帮助独立开发者验证产品想法的工具。"},
    )

    assert response.status_code == 200
    assert response.json()["summary"]
