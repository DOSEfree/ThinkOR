import pytest
from fastapi.testclient import TestClient

from ideaos_agent.domain.archive import ArchiveStatus
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


def test_app_page_renders_html_interface() -> None:
    client = TestClient(app)

    response = client.get("/app")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="idea-form"' in response.text
    assert 'id="idea-content"' in response.text
    assert "/static/swiss.css" in response.text
    assert "/static/app.js" in response.text
    assert "归档状态" in response.text
    assert "follow-up 局部完善结果，以及当前会话的归档状态。" in response.text


def test_app_styles_allow_result_placeholder_copy_to_stay_on_one_line_more_easily() -> None:
    client = TestClient(app)

    response = client.get("/static/swiss.css")

    assert response.status_code == 200
    assert "max-width: 72rem;" in response.text


def test_app_serves_archive_aware_frontend_script() -> None:
    client = TestClient(app)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "renderArchivePanel" in response.text
    assert "SESSION ARCHIVE / 归档状态" in response.text
    assert "OPEN FEISHU DOC" in response.text
    assert "if (!resultContent.innerHTML.trim())" in response.text
    assert "SUMMARY / 摘要" in response.text
    assert "NEXT ACTIONS / 后续动作" in response.text
    assert "function formatSectionKeyLabel(sectionKey)" in response.text
    assert "SECTION_DISPLAY_LABELS" in response.text
    assert "data-follow-up-composer" in response.text
    assert "let isSubmitting = false" in response.text
    assert "function setActionButtonsDisabled(isDisabled)" in response.text


def test_idea_analysis_endpoint_returns_fake_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    monkeypatch.setenv("IDEAOS_MAX_INPUT_CHARS", "4000")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={"content": "我想做一个帮助独立开发者验证产品想法的工具。"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"].startswith("sess_")
    assert body["archive_status"] == ArchiveStatus.NOT_TRIGGERED
    assert body["archive_url"] is None
    assert body["archive_title"] == "独立开发者产品验证工具"
    assert body["input_echo"] == "我想做一个帮助独立开发者验证产品想法的工具。"
    assert body["needs_clarification"] is True
    assert body["analysis"] is None
