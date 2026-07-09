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
    assert 'id="sidebar"' in response.text
    assert 'id="history-search-toggle"' in response.text
    assert 'id="sidebar-toggle"' in response.text
    assert 'id="sidebar-search-panel"' in response.text
    assert 'id="history-session-list"' in response.text
    assert 'id="history-thread-content"' in response.text
    assert 'id="thread-context-panel"' in response.text
    assert 'id="history-refresh"' in response.text
    assert 'id="result-shell"' in response.text
    assert 'aria-busy="false"' in response.text
    assert 'id="workspace-busy"' in response.text
    assert "follow-up" in response.text


def test_app_page_renders_v0_4_shell_and_brand_assets() -> None:
    client = TestClient(app)

    response = client.get("/app")

    assert response.status_code == 200
    assert 'class="topbar"' in response.text
    assert 'id="sidebar"' in response.text
    assert "/static/assets/logo/IdeaOS_logo.png" in response.text
    assert "/static/assets/logo/user.png" in response.text
    assert "/static/assets/logo/refresh.png" in response.text
    assert "历史记录" in response.text
    assert "/ HISTORY" in response.text
    assert "username" in response.text
    assert "CURRENT THREAD /" in response.text
    assert "Single Analysis /" in response.text
    assert "One Clarification /" in response.text
    assert "Feishu Archive /" in response.text
    assert "从给 IdeaOS 输入一句想法开始" in response.text


def test_app_styles_include_thread_context_and_sidebar_history_tokens() -> None:
    client = TestClient(app)

    response = client.get("/static/swiss.css")

    assert response.status_code == 200
    assert "max-width: 72rem;" in response.text
    assert ".thread-context-panel" in response.text
    assert ".sidebar-history-panel" in response.text
    assert ".workspace-busy" in response.text
    assert ".result-placeholder-card" in response.text
    assert "scrollbar-gutter: stable both-edges;" in response.text
    assert "overscroll-behavior: contain;" in response.text
    assert "overflow-x: hidden;" in response.text
    assert ".page-sidebar-collapsed .app-shell" in response.text
    assert ".history-bucket-label" in response.text
    assert ".history-folder" in response.text
    assert ".history-version-item" in response.text
    assert ".history-thread-action[data-action=\"delete-history-thread\"]" in response.text
    assert ".sidebar-title-main" in response.text
    assert "white-space: nowrap;" in response.text
    assert ".sidebar-refresh-icon" in response.text
    assert "width: 18px;" in response.text


def test_app_serves_v0_4_logo_asset() -> None:
    client = TestClient(app)

    response = client.get("/static/assets/logo/IdeaOS_logo.png")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_app_serves_archive_aware_frontend_script() -> None:
    client = TestClient(app)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "renderArchivePanel" in response.text
    assert "SESSION ARCHIVE /" in response.text
    assert "OPEN FEISHU DOC" in response.text
    assert "if (!resultContent.innerHTML.trim())" in response.text
    assert "SUMMARY /" in response.text
    assert "NEXT ACTIONS /" in response.text
    assert "function formatSectionKeyLabel(sectionKey)" in response.text
    assert "SECTION_DISPLAY_LABELS" in response.text
    assert "data-follow-up-composer" in response.text
    assert "let isSubmitting = false" in response.text
    history_search_hook = (
        'const historySearchToggleButton = document.getElementById("history-search-toggle")'
    )
    sidebar_toggle_hook = 'const sidebarToggleButton = document.getElementById("sidebar-toggle")'
    assert history_search_hook in response.text
    assert sidebar_toggle_hook in response.text
    assert 'setWorkspaceMode("empty")' in response.text
    assert "function setWorkspaceMode(mode)" in response.text
    workspace_busy_hook = (
        "function setWorkspaceBusy(isBusy, message = DEFAULT_WORKSPACE_BUSY_MESSAGE)"
    )
    assert workspace_busy_hook in response.text
    assert "function setSidebarCollapsed(isCollapsed)" in response.text
    assert "function setSearchPanelVisible(isVisible)" in response.text
    assert "function formatWorkspaceBusyMessage(label)" in response.text
    thread_panel_hook = 'const threadContextPanel = document.getElementById("thread-context-panel")'
    assert thread_panel_hook in response.text
    assert "attachSessionActionContainer(threadContextPanel)" in response.text
    assert "function setThreadContextVisible(isVisible)" in response.text
    assert "function setActionButtonsDisabled(isDisabled)" in response.text
    assert 'activeLoadingButton.setAttribute("aria-busy", "true")' in response.text
    assert "async function loadRecentSessions()" in response.text
    assert 'fetch("/api/v1/threads?limit=24")' in response.text
    assert "async function openHistorySession(sessionId, options = {})" in response.text
    assert "async function toggleHistoryThread(rootSessionId)" in response.text
    assert "async function handleDeleteHistoryThread(rootSessionId, triggerButton)" in response.text
    assert "async function syncRemoteArchiveDeletions()" in response.text
    assert "function groupThreadsByRecency(items)" in response.text
    assert "data-action='toggle-history-thread'" in response.text
    assert "data-action='continue-history-follow-up'" in response.text
    assert "data-action='delete-history-thread'" in response.text
    assert 'method: "DELETE"' in response.text
    assert 'fetch("/api/v1/threads/sync-remote-archives", {' in response.text
    assert 'if (archiveStatus === "succeeded") {' in response.text
    assert 'return "";' in response.text
    assert "删除这条想法线程" in response.text
    assert "1 个版本 / VERSION" in response.text
    assert "ROOT ANALYSIS / 根分析" in response.text
    assert "Open latest version" in response.text
    assert "OPEN DETAIL" in response.text
    assert "CONTINUE FOLLOW-UP" in response.text
    assert "CONTINUE HERE" in response.text


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
    assert body["needs_clarification"] is True
    assert body["analysis"] is None
