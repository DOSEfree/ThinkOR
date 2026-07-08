from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ideaos_agent.domain.archive import ArchiveStatus
from ideaos_agent.infrastructure.archive.sqlite_store import SqliteSessionArchiveStore
from ideaos_agent.main import app


def test_idea_analysis_rejects_empty_input() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/idea-analysis", json={"content": ""})

    assert response.status_code == 422


def test_idea_analysis_rejects_blank_only_input() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/idea-analysis", json={"content": "   "})

    assert response.status_code == 422


def test_idea_analysis_rejects_input_that_is_too_long(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    monkeypatch.setenv("IDEAOS_MAX_INPUT_CHARS", "10")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={"content": "这是一个明显超过长度限制的想法描述。"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "idea_input_too_long"


def test_idea_analysis_requires_key_when_not_using_fake_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "false")
    monkeypatch.delenv("IDEAOS_LLM_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post("/api/v1/idea-analysis", json={"content": "我想做一个想法分析工具。"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "llm_not_configured"


def test_idea_analysis_accepts_clarifications_with_fake_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
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
    assert body["session_id"].startswith("sess_")
    assert body["archive_status"] == ArchiveStatus.SUCCEEDED
    assert body["archive_url"] == f"https://feishu.example.com/docx/{body['session_id']}"
    assert body["archive_title"] == "独立开发者产品验证工具"
    assert body["input_echo"] == "我想做一个帮助独立开发者验证产品想法的工具。"
    assert body["needs_clarification"] is False
    assert body["analysis"]["summary"]


def test_idea_analysis_reuses_session_id_when_client_resubmits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={
            "session_id": "sess_existing",
            "content": "我想做一个帮助独立开发者验证产品想法的工具。",
            "clarifications": [
                {
                    "question": "你最想帮用户验证什么？",
                    "answer": "我最想先帮助他们判断想法值不值得继续做。",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "sess_existing"


def test_idea_analysis_persists_session_record_to_sqlite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    monkeypatch.setenv("IDEAOS_ARCHIVE_DB_PATH", str(tmp_path / "ideaos_agent.db"))
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={
            "content": "我想做一个帮助独立开发者验证产品想法的工具。",
            "clarifications": [
                {
                    "question": "你最想帮用户验证什么？",
                    "answer": "我最想先帮助他们判断想法值不值得继续做。",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    archive_store = SqliteSessionArchiveStore(tmp_path / "ideaos_agent.db")
    persisted_record = archive_store.get_session_record(body["session_id"])

    assert persisted_record is not None
    assert persisted_record.archive_status == ArchiveStatus.SUCCEEDED
    assert persisted_record.root_session_id == body["session_id"]
    assert persisted_record.archive_url == f"https://feishu.example.com/docx/{body['session_id']}"
    assert persisted_record.clarification_count == 1
    assert persisted_record.completed_at is not None
    assert persisted_record.archived_at is not None


def test_session_history_endpoints_return_thread_views(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    monkeypatch.setenv("IDEAOS_ARCHIVE_DB_PATH", str(tmp_path / "ideaos_agent.db"))
    client = TestClient(app)

    analysis_response = client.post(
        "/api/v1/idea-analysis",
        json={
            "content": "我想做一个帮助独立开发者验证产品想法的工具。",
            "clarifications": [
                {
                    "question": "你最想帮用户验证什么？",
                    "answer": "我最想先帮助他们判断想法值不值得继续做。",
                }
            ],
        },
    )
    assert analysis_response.status_code == 200
    analysis_body = analysis_response.json()

    refine_response = client.post(
        "/api/v1/follow-up/refine",
        json={
            "parent_session_id": analysis_body["session_id"],
            "question": "我想进一步收窄目标用户。",
            "clarifications": [],
        },
    )
    assert refine_response.status_code == 200
    refine_body = refine_response.json()

    composed_response = client.post(
        "/api/v1/follow-up/compose-full-plan",
        json={"parent_session_id": refine_body["session_id"]},
    )
    assert composed_response.status_code == 200
    composed_body = composed_response.json()

    sessions_response = client.get("/api/v1/sessions")
    assert sessions_response.status_code == 200
    sessions_body = sessions_response.json()
    assert len(sessions_body["items"]) >= 3
    assert sessions_body["items"][0]["root_session_id"] == analysis_body["session_id"]

    detail_response = client.get(f"/api/v1/sessions/{analysis_body['session_id']}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["session_id"] == analysis_body["session_id"]
    assert detail_body["can_continue_follow_up"] is True
    assert refine_body["session_id"] in detail_body["child_session_ids"]

    threads_response = client.get("/api/v1/threads")
    assert threads_response.status_code == 200
    threads_body = threads_response.json()
    assert len(threads_body["items"]) >= 1
    assert threads_body["items"][0]["root_session_id"] == analysis_body["session_id"]

    thread_response = client.get(f"/api/v1/threads/{analysis_body['session_id']}")
    assert thread_response.status_code == 200
    thread_body = thread_response.json()
    assert thread_body["root_session_id"] == analysis_body["session_id"]
    assert [item["session_id"] for item in thread_body["items"]] == [
        analysis_body["session_id"],
        refine_body["session_id"],
        composed_body["session_id"],
    ]
