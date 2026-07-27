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
    assert "<title>ThinkOR / App</title>" in response.text
    assert 'aria-label="ThinkOR"' in response.text
    assert 'id="idea-form"' in response.text
    assert 'id="idea-content"' in response.text
    assert "/static/swiss.css" in response.text
    assert "/static/app.js" in response.text
    assert 'id="sidebar"' in response.text
    assert 'id="history-search-toggle"' in response.text
    assert 'id="sidebar-toggle"' in response.text
    assert 'id="sidebar-search-panel"' in response.text
    assert 'id="sidebar-search-input"' in response.text
    assert 'id="history-session-list"' in response.text
    assert 'id="history-thread-content"' in response.text
    assert 'id="thread-context-panel"' in response.text
    assert 'id="history-refresh"' in response.text
    assert 'id="result-shell"' in response.text
    assert 'aria-busy="false"' in response.text
    assert 'id="workspace-busy"' in response.text
    assert 'id="loading-dialog"' in response.text
    assert 'id="loading-dialog-elapsed"' in response.text
    assert 'id="archive-retry-dialog"' in response.text
    assert 'id="request-retry-dialog"' in response.text
    assert 'id="delete-confirm-dialog"' in response.text
    assert 'class="loading-slot-window"' in response.text
    assert 'class="loading-slot-gear"' in response.text
    assert 'class="loading-slot-spark loading-slot-spark-six"' in response.text
    assert 'id="app-tooltip"' in response.text
    assert 'data-tooltip="刷新历史记录 / Refresh history"' in response.text
    assert "follow-up" in response.text


def test_app_page_renders_v0_4_shell_and_brand_assets() -> None:
    client = TestClient(app)

    response = client.get("/app")

    assert response.status_code == 200
    assert 'class="topbar"' in response.text
    assert 'id="sidebar"' in response.text
    assert "/static/assets/logo/ThinkOR_logo.png" in response.text
    assert "/static/assets/logo/user.png" in response.text
    assert "/static/assets/logo/refresh.png" in response.text
    assert "历史记录" in response.text
    assert "/ HISTORY" in response.text
    assert 'class="topbar-user-value"' in response.text
    assert "当前链路 / CURRENT THREAD" in response.text
    slogan = (
        "Your AI agent for exploring ideas, shaping thoughts, and creating possibilities."
    )
    assert slogan in response.text
    assert 'class="workspace-title-accent"' in response.text
    assert "单次分析 / Single Analysis" not in response.text
    assert "输入一句想法以开始" in response.text


def test_app_styles_expose_thinkor_theme_and_interaction_hooks() -> None:
    client = TestClient(app)

    response = client.get("/static/swiss.css")

    assert response.status_code == 200
    assert "--brand: #d7ff00;" in response.text
    assert "--page-bg: #090a0b;" in response.text
    assert "background: #000000;" in response.text
    assert ".page-workspace-empty .workspace::before" in response.text
    assert "-webkit-mask-image: radial-gradient(ellipse at center" in response.text
    grid_transform = "transform: translateX(-50%) perspective(780px) rotateX(59deg) scale(1.18);"
    assert grid_transform in response.text
    assert ".page-workspace-history-detail .workspace-stage" in response.text
    assert ".topbar-logo-link" in response.text
    assert "width: 220px;" in response.text
    assert ".workspace" in response.text
    assert ".thread-context-panel" in response.text
    assert ".sidebar-history-panel" in response.text
    assert ".sidebar-search.hidden + .history-shell" in response.text
    assert ".history-shell::after" in response.text
    assert ".workspace-busy" in response.text
    assert ".loading-dialog" in response.text
    assert ".archive-retry-dialog" in response.text
    assert ".request-retry-dialog" in response.text
    assert ".delete-confirm-dialog" in response.text
    assert ".loading-slot-machine" in response.text
    assert ".loading-slot-window" in response.text
    assert "cubic-bezier(0.72, 0, 0.28, 1)" in response.text
    assert ".loading-slot-gear" in response.text
    assert "@keyframes loading-slot-spark-six" in response.text
    assert ".completion-notice" in response.text
    assert ".app-tooltip" in response.text
    assert ".sidebar-history-panel .history-panel-body::-webkit-scrollbar-thumb" in response.text
    history_scroll_gutter_hook = (
        ".sidebar-history-panel .history-panel-body {\n"
        "  padding: 4px 14px 12px 0;"
    )
    assert history_scroll_gutter_hook in response.text
    assert ".workspace::-webkit-scrollbar-thumb" in response.text
    active_history_card_hook = (
        ".history-item.is-active,\n"
        ".thread-item.is-active {"
    )
    assert active_history_card_hook in response.text
    folder_active_card_hook = (
        ".history-folder.is-active {\n"
        "  border-color: rgba(215, 255, 0, 0.64);\n"
        "  background: #1b1f20;\n"
        "  box-shadow: none;\n"
        "}"
    )
    assert folder_active_card_hook in response.text
    version_active_card_hook = (
        ".history-version-item.is-active {\n"
        "  border-color: rgba(215, 255, 0, 0.64);\n"
        "  background: #1d2118;\n"
        "  box-shadow: none;\n"
        "}"
    )
    assert version_active_card_hook in response.text
    assert ".page-workspace-active .workspace-stage" in response.text
    assert ".result-placeholder-card" in response.text
    assert ".history-folder" in response.text
    assert ".history-version-item" in response.text
    assert ".history-thread-action[data-action=\"delete-history-thread\"]" in response.text
    assert ".analysis-heading" in response.text
    assert "@media (prefers-reduced-motion: reduce)" in response.text


def test_app_serves_thinkor_logo_asset() -> None:
    client = TestClient(app)

    response = client.get("/static/assets/logo/ThinkOR_logo.png")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_app_serves_archive_aware_frontend_script() -> None:
    client = TestClient(app)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "renderArchivePanel" in response.text
    assert "归档状态" in response.text
    assert "打开飞书文档" in response.text
    assert "archive-status-list" in response.text
    assert "function resolveArchiveSummary(payload, archiveStatus, sessionKind)" in response.text
    assert "if (!resultContent.innerHTML.trim())" in response.text
    assert "摘要 / SUMMARY" in response.text
    assert "后续动作 / NEXT ACTIONS" in response.text
    assert "function formatSectionKeyLabel(sectionKey)" in response.text
    assert "SECTION_DISPLAY_LABELS" in response.text
    assert "let isViewingHistoryDetail = false" in response.text
    assert 'setWorkspaceMode("history-detail")' in response.text
    assert "返回主页" in response.text
    assert "renderFollowUpActions" in response.text
    assert "thread-node-button" in response.text
    assert "data-follow-up-composer" in response.text
    assert "let isSubmitting = false" in response.text
    history_search_hook = (
        'const historySearchToggleButton = document.getElementById("history-search-toggle")'
    )
    history_search_input_hook = (
        'const sidebarSearchInput = document.getElementById("sidebar-search-input")'
    )
    sidebar_toggle_hook = 'const sidebarToggleButton = document.getElementById("sidebar-toggle")'
    assert history_search_hook in response.text
    assert history_search_input_hook in response.text
    assert sidebar_toggle_hook in response.text
    assert 'setWorkspaceMode("empty")' in response.text
    assert "function setWorkspaceMode(mode)" in response.text
    workspace_busy_hook = (
        "function setWorkspaceBusy(isBusy, message = DEFAULT_WORKSPACE_BUSY_MESSAGE)"
    )
    assert workspace_busy_hook in response.text
    loading_dialog_hook = (
        "function setLoadingDialog(isLoading, "
        "message = DEFAULT_WORKSPACE_BUSY_MESSAGE)"
    )
    assert loading_dialog_hook in response.text
    assert "function updateLoadingElapsedTime()" in response.text
    assert "function scrollWorkspaceToTop()" in response.text
    assert "function showDeleteConfirmation(message, deleteAction)" in response.text
    assert "async function retryFailedArchive()" in response.text
    assert "function renderRetryableApiError(data, fallbackMessage, retryAction)" in response.text
    assert "function initializeHistoryScrollIndicator()" in response.text
    assert 'historySessionList.classList.add("is-scrolling")' in response.text
    assert "function setSidebarCollapsed(isCollapsed)" in response.text
    assert "function setSearchPanelVisible(isVisible)" in response.text
    assert "function scheduleHistorySearch(query)" in response.text
    build_history_path_hook = (
        "function buildHistoryThreadsRequestPath(limit = 24, query = currentHistorySearchQuery)"
    )
    assert build_history_path_hook in response.text
    assert "function formatWorkspaceBusyMessage(label)" in response.text
    thread_panel_hook = 'const threadContextPanel = document.getElementById("thread-context-panel")'
    assert thread_panel_hook in response.text
    assert "attachSessionActionContainer(threadContextPanel)" in response.text
    assert "function setThreadContextVisible(isVisible)" in response.text
    assert "function setActionButtonsDisabled(isDisabled)" in response.text
    assert 'activeLoadingButton.setAttribute("aria-busy", "true")' in response.text
    assert "async function loadRecentSessions()" in response.text
    request_path_hook = "const requestPath = buildHistoryThreadsRequestPath(24, normalizedQuery);"
    assert request_path_hook in response.text
    assert "const response = await fetch(requestPath);" in response.text
    assert "async function openHistorySession(sessionId, options = {})" in response.text
    assert "async function toggleHistoryThread(rootSessionId)" in response.text
    assert "async function handleDeleteHistoryThread(rootSessionId, triggerButton)" in response.text
    assert "async function handleDeleteHistorySession(sessionId, triggerButton)" in response.text
    assert "async function syncRemoteArchiveDeletions()" in response.text
    assert "function groupThreadsByRecency(items)" in response.text
    assert "function truncateHistoryCardTitle(title, maxLength = 10)" in response.text
    assert "function extractSessionContext(payload)" in response.text
    assert "function formatFormalVersionLabel(item, fallbackNumber = null)" in response.text
    assert "function buildThreadContextMeta(items, rootSessionId)" in response.text
    assert 'class="analysis-heading"' in response.text
    assert "data-action='toggle-history-thread'" in response.text
    assert "data-action='continue-history-follow-up'" in response.text
    assert "data-action='delete-history-session'" in response.text
    assert "data-action='delete-history-thread'" in response.text
    assert 'method: "DELETE"' in response.text
    assert 'fetch("/api/v1/threads/sync-remote-archives", {' in response.text
    assert 'if (archiveStatus === "succeeded") {' in response.text
    assert 'return "";' in response.text
    assert "删除这条想法线程" in response.text
    assert "1 个版本 / VERSION" in response.text
    assert 'historySessionList.classList.remove("is-scrolling")' in response.text
    assert "Open latest version" in response.text
    assert "OPEN DETAIL" in response.text
    assert "CONTINUE FOLLOW-UP" in response.text
    assert "CONTINUE HERE" not in response.text
    assert "CURRENT CHAIN" in response.text
    assert "ROOT VERSION" in response.text
    assert "thread-node-parent" in response.text
    assert "function renderStatusBar()" in response.text
    assert "function initializeAppTooltips()" in response.text
    assert "function showAppTooltip(target)" in response.text
    follow_up_placeholder = "请优先打磨这个方案的核心路径、验证方式或落地边界。"
    assert follow_up_placeholder in response.text
    assert "function renderHistoryVersionDeleteAction(item)" in response.text
    assert "data-action=\"open-archive-retry\"" in response.text
    assert "/retry-archive" in response.text
    assert 'target.closest("[data-action]")' in response.text
    assert "scrollIntoView({behavior: \"smooth\", block: \"center\"})" in response.text
    assert "scrollWorkspaceToTop();" in response.text
    delete_leaf_tooltip = "删除这个版本 / Delete version"
    assert delete_leaf_tooltip in response.text


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
