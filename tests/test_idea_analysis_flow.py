from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ideaos_agent import config
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
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "false")
    monkeypatch.delenv("IDEAOS_LLM_API_KEY", raising=False)
    monkeypatch.setattr(config, "ENV_FILE_PATH", tmp_path / ".env")
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
    assert body["archive_status"] == ArchiveStatus.SIMULATED
    assert body["archive_url"] is None
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
    assert persisted_record.archive_status == ArchiveStatus.SIMULATED
    assert persisted_record.root_session_id == body["session_id"]
    assert persisted_record.archive_url is None
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
    assert analysis_body["formal_version_number"] == 1
    assert analysis_body["parent_formal_version_number"] is None

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
    assert refine_body["formal_version_number"] is None
    assert refine_body["parent_formal_version_number"] == 1

    composed_response = client.post(
        "/api/v1/follow-up/compose-full-plan",
        json={"parent_session_id": refine_body["session_id"]},
    )
    assert composed_response.status_code == 200
    composed_body = composed_response.json()
    assert composed_body["formal_version_number"] == 2
    assert composed_body["parent_formal_version_number"] == 1

    sessions_response = client.get("/api/v1/sessions")
    assert sessions_response.status_code == 200
    sessions_body = sessions_response.json()
    assert len(sessions_body["items"]) >= 2
    assert sessions_body["items"][0]["root_session_id"] == analysis_body["session_id"]

    detail_response = client.get(f"/api/v1/sessions/{analysis_body['session_id']}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["session_id"] == analysis_body["session_id"]
    assert detail_body["formal_version_number"] == 1
    assert detail_body["parent_formal_version_number"] is None
    assert detail_body["can_continue_follow_up"] is True
    assert composed_body["session_id"] in detail_body["child_session_ids"]
    assert detail_body["active_follow_up_draft_id"] is None

    threads_response = client.get("/api/v1/threads")
    assert threads_response.status_code == 200
    threads_body = threads_response.json()
    assert len(threads_body["items"]) >= 1
    assert threads_body["items"][0]["root_session_id"] == analysis_body["session_id"]
    assert threads_body["items"][0]["latest_formal_version_number"] == 2

    thread_response = client.get(f"/api/v1/threads/{analysis_body['session_id']}")
    assert thread_response.status_code == 200
    thread_body = thread_response.json()
    assert thread_body["root_session_id"] == analysis_body["session_id"]
    assert [item["session_id"] for item in thread_body["items"]] == [
        analysis_body["session_id"],
        composed_body["session_id"],
    ]
    assert [item["formal_version_number"] for item in thread_body["items"]] == [1, 2]
    assert [item["parent_formal_version_number"] for item in thread_body["items"]] == [
        None,
        1,
    ]


def test_branch_follow_up_via_api_keeps_global_version_numbers_and_root_parent_binding(
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
                    "question": "你最想先验证什么？",
                    "answer": "先判断一个想法值不值得继续做。",
                }
            ],
        },
    )
    assert analysis_response.status_code == 200
    analysis_body = analysis_response.json()

    first_refine_response = client.post(
        "/api/v1/follow-up/refine",
        json={
            "parent_session_id": analysis_body["session_id"],
            "question": "我想先收窄目标用户。",
            "clarifications": [],
        },
    )
    assert first_refine_response.status_code == 200
    first_refine_body = first_refine_response.json()
    first_composed_response = client.post(
        "/api/v1/follow-up/compose-full-plan",
        json={"parent_session_id": first_refine_body["session_id"]},
    )
    assert first_composed_response.status_code == 200
    first_composed_body = first_composed_response.json()

    second_refine_response = client.post(
        "/api/v1/follow-up/refine",
        json={
            "parent_session_id": analysis_body["session_id"],
            "question": "我想从 ROOT 版本重新追问渠道与分发。",
            "clarifications": [],
        },
    )
    assert second_refine_response.status_code == 200
    second_refine_body = second_refine_response.json()
    second_composed_response = client.post(
        "/api/v1/follow-up/compose-full-plan",
        json={"parent_session_id": second_refine_body["session_id"]},
    )
    assert second_composed_response.status_code == 200
    second_composed_body = second_composed_response.json()

    assert first_composed_body["formal_version_number"] == 2
    assert first_composed_body["parent_formal_version_number"] == 1
    assert second_refine_body["formal_version_number"] is None
    assert second_refine_body["parent_formal_version_number"] == 1
    assert second_composed_body["formal_version_number"] == 3
    assert second_composed_body["parent_formal_version_number"] == 1

    thread_response = client.get(f"/api/v1/threads/{analysis_body['session_id']}")
    assert thread_response.status_code == 200
    thread_body = thread_response.json()
    assert [item["session_id"] for item in thread_body["items"]] == [
        analysis_body["session_id"],
        first_composed_body["session_id"],
        second_composed_body["session_id"],
    ]
    assert [item["formal_version_number"] for item in thread_body["items"]] == [1, 2, 3]
    assert [item["parent_formal_version_number"] for item in thread_body["items"]] == [
        None,
        1,
        1,
    ]


def test_delete_leaf_session_endpoint_allows_non_latest_branch_leaf_and_keeps_version_ids(
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
            "content": "I want to build a tool that helps indie developers validate product ideas.",
            "clarifications": [
                {
                    "question": "What is the first thing you want to validate for them?",
                    "answer": "I want to help them decide whether an idea is worth pursuing.",
                }
            ],
        },
    )
    assert analysis_response.status_code == 200
    analysis_body = analysis_response.json()

    first_refine_response = client.post(
        "/api/v1/follow-up/refine",
        json={
            "parent_session_id": analysis_body["session_id"],
            "question": "I want to narrow the target user further.",
            "clarifications": [],
        },
    )
    assert first_refine_response.status_code == 200
    first_refine_body = first_refine_response.json()
    first_composed_response = client.post(
        "/api/v1/follow-up/compose-full-plan",
        json={"parent_session_id": first_refine_body["session_id"]},
    )
    assert first_composed_response.status_code == 200
    first_composed_body = first_composed_response.json()

    second_refine_response = client.post(
        "/api/v1/follow-up/refine",
        json={
            "parent_session_id": analysis_body["session_id"],
            "question": "I want to go back to ROOT and explore distribution instead.",
            "clarifications": [],
        },
    )
    assert second_refine_response.status_code == 200
    second_refine_body = second_refine_response.json()
    second_composed_response = client.post(
        "/api/v1/follow-up/compose-full-plan",
        json={"parent_session_id": second_refine_body["session_id"]},
    )
    assert second_composed_response.status_code == 200
    second_composed_body = second_composed_response.json()

    delete_response = client.delete(f"/api/v1/sessions/{first_composed_body['session_id']}")
    assert delete_response.status_code == 200
    delete_body = delete_response.json()
    assert delete_body["session_id"] == first_composed_body["session_id"]
    assert delete_body["root_session_id"] == analysis_body["session_id"]
    assert delete_body["parent_session_id"] == analysis_body["session_id"]
    assert delete_body["deleted_session_count"] == 1
    assert delete_body["deleted_draft_count"] == 0
    assert delete_body["deleted_session_ids"] == [first_composed_body["session_id"]]
    assert delete_body["archive_delete_failures"] == []

    deleted_detail_response = client.get(f"/api/v1/sessions/{first_composed_body['session_id']}")
    assert deleted_detail_response.status_code == 404

    thread_response = client.get(f"/api/v1/threads/{analysis_body['session_id']}")
    assert thread_response.status_code == 200
    thread_body = thread_response.json()
    assert [item["session_id"] for item in thread_body["items"]] == [
        analysis_body["session_id"],
        second_composed_body["session_id"],
    ]
    assert [item["formal_version_number"] for item in thread_body["items"]] == [1, 3]
    assert [item["parent_formal_version_number"] for item in thread_body["items"]] == [
        None,
        1,
    ]


def test_delete_leaf_session_endpoint_blocks_root_single_delete(
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
            "content": "I want to build a tool that helps indie developers validate product ideas.",
            "clarifications": [
                {
                    "question": "What is the first thing you want to validate for them?",
                    "answer": "I want to help them decide whether an idea is worth pursuing.",
                }
            ],
        },
    )
    assert analysis_response.status_code == 200
    analysis_body = analysis_response.json()

    delete_response = client.delete(f"/api/v1/sessions/{analysis_body['session_id']}")

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"]["code"] == "session_state_invalid"


def test_delete_thread_endpoint_removes_local_history_without_remote_fake_archive(
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
            "content": "I want to build a tool that helps indie developers validate product ideas.",
            "clarifications": [
                {
                    "question": "What is the first thing you want to validate for them?",
                    "answer": "I want to help them decide whether an idea is worth pursuing.",
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
            "question": "I want to narrow the target user further.",
            "clarifications": [],
        },
    )
    assert refine_response.status_code == 200

    delete_response = client.delete(f"/api/v1/threads/{analysis_body['session_id']}")
    assert delete_response.status_code == 200
    delete_body = delete_response.json()
    assert delete_body["root_session_id"] == analysis_body["session_id"]
    assert delete_body["deleted_session_count"] >= 2
    assert delete_body["deleted_archive_count"] == 0
    assert delete_body["archive_delete_failures"] == []

    thread_response = client.get(f"/api/v1/threads/{analysis_body['session_id']}")
    assert thread_response.status_code == 404

    sessions_response = client.get("/api/v1/sessions")
    assert sessions_response.status_code == 200
    assert sessions_response.json()["items"] == []


def test_sync_remote_archives_endpoint_skips_simulated_archives(
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
            "content": "I want to build a tool that helps indie developers validate product ideas.",
            "clarifications": [
                {
                    "question": "What is the first thing you want to validate for them?",
                    "answer": "I want to help them decide whether an idea is worth pursuing.",
                }
            ],
        },
    )
    assert analysis_response.status_code == 200

    sync_response = client.post("/api/v1/threads/sync-remote-archives")

    assert sync_response.status_code == 200
    sync_body = sync_response.json()
    assert sync_body["checked_archive_count"] == 0
    assert sync_body["removed_session_count"] == 0
    assert sync_body["removed_session_ids"] == []
    assert sync_body["probe_failures"] == []


def test_retry_failed_archive_endpoint_reuses_persisted_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    database_path = tmp_path / "ideaos_agent.db"
    monkeypatch.setenv("IDEAOS_ARCHIVE_DB_PATH", str(database_path))
    client = TestClient(app)

    analysis_response = client.post(
        "/api/v1/idea-analysis",
        json={
            "content": "我想做一个帮助独立开发者验证产品想法的工具。",
            "clarifications": [
                {
                    "question": "你最想先验证什么？",
                    "answer": "先判断一个想法值不值得继续做。",
                }
            ],
        },
    )
    assert analysis_response.status_code == 200
    session_id = analysis_response.json()["session_id"]
    archive_store = SqliteSessionArchiveStore(database_path)
    record = archive_store.get_session_record(session_id)
    assert record is not None
    failed_at = datetime.now(UTC)
    archive_store.save_session_record(
        record.model_copy(
            update={
                "archive_status": ArchiveStatus.FAILED,
                "archive_url": None,
                "archive_error": "need_user_authorization",
                "archived_at": failed_at,
                "updated_at": failed_at,
            }
        )
    )

    retry_response = client.post(f"/api/v1/sessions/{session_id}/retry-archive")

    assert retry_response.status_code == 200
    retry_body = retry_response.json()
    assert retry_body["session_id"] == session_id
    assert retry_body["archive_status"] == ArchiveStatus.SIMULATED
    assert retry_body["archive_url"] is None
    assert retry_body["archive_error"] is None

    duplicate_retry_response = client.post(f"/api/v1/sessions/{session_id}/retry-archive")

    assert duplicate_retry_response.status_code == 409
    assert duplicate_retry_response.json()["detail"]["code"] == "archive_retry_not_allowed"


def test_idea_analysis_echoes_declared_intent_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={
            "content": "我想做一个帮助独立开发者验证产品想法的工具。",
            "intent": "product",
        },
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "product"


def test_idea_analysis_rejects_removed_decided_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-analysis",
        json={
            "content": "我想做一个帮助独立开发者验证产品想法的工具。",
            "intent": "decided",
        },
    )

    assert response.status_code == 422

