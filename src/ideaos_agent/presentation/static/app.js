"use strict";

const form = document.getElementById("idea-form");
const textarea = document.getElementById("idea-content");
const submitButton = document.getElementById("idea-submit");
const resetButton = document.getElementById("idea-reset");
const sidebar = document.getElementById("sidebar");
const sidebarToggleButton = document.getElementById("sidebar-toggle");
const historySearchToggleButton = document.getElementById("history-search-toggle");
const sidebarSearchPanel = document.getElementById("sidebar-search-panel");
const sidebarSearchInput = document.getElementById("sidebar-search-input");
const historyShell = document.getElementById("history-shell");
const historyRefreshButton = document.getElementById("history-refresh");
const historySessionList = document.getElementById("history-session-list");
const threadContextPanel = document.getElementById("thread-context-panel");
const historyThreadContent = document.getElementById("history-thread-content");
const resultShell = document.getElementById("result-shell");
const workspaceBusy = document.getElementById("workspace-busy");
const workspaceBusyText = document.getElementById("workspace-busy-text");
const resultPlaceholder = document.getElementById("result-placeholder");
const resultError = document.getElementById("result-error");
const resultContent = document.getElementById("result-content");

let currentSessionId = null;
let currentView = null;
let selectedHistorySessionId = null;
let selectedThreadRootSessionId = null;
let isSubmitting = false;
let activeLoadingButton = null;
let historyThreadSummaries = [];

const expandedHistoryRootIds = new Set();
const historyThreadCache = new Map();
const historyThreadLoadErrors = new Map();
const loadingHistoryRootIds = new Set();

const DEFAULT_WORKSPACE_BUSY_MESSAGE = "Analysis is running. Please keep this workspace open.";

const ANALYSIS_FIELDS = [
  ["01", "SUMMARY / 摘要", "summary", "copy", "analysis-span-12"],
  ["02", "FEASIBILITY / 可行性", "feasibility", "copy", "analysis-span-12"],
  ["03", "MARKET / 市场判断", "market", "copy", "analysis-span-12"],
  ["04", "KNOWLEDGE GAPS / 认知缺口", "knowledge_gaps", "list", "analysis-span-12"],
  ["05", "RESOURCE GAPS / 资源缺口", "resource_gaps", "list", "analysis-span-12"],
  ["06", "TEAM REQUIREMENTS / 团队需求", "team_requirements", "list", "analysis-span-12"],
  ["07", "SIMILAR PROJECTS / 相似项目", "similar_projects", "list", "analysis-span-12"],
  ["08", "MVP ROADMAP / MVP 路线图", "mvp_roadmap", "list", "analysis-span-12"],
  ["09", "LONG-TERM ROADMAP / 长期路线图", "long_term_roadmap", "list", "analysis-span-12"],
];

const SECTION_DISPLAY_LABELS = Object.fromEntries(
  ANALYSIS_FIELDS.map(([, title, key]) => [key, title]),
);

const SESSION_KIND_LABELS = {
  analysis: "ANALYSIS",
  follow_up_refinement: "FOLLOW-UP REFINEMENT",
  full_plan_composed: "FULL PLAN COMPOSED",
};

const ARCHIVE_STATUS_META = {
  not_triggered: {
    badge: "NOT TRIGGERED",
    label: "WAITING FOR FINAL RESULT",
    note: "Archive will be created only after this session reaches a completed result.",
  },
  pending: {
    badge: "PENDING",
    label: "ARCHIVE IN PROGRESS",
    note: "The result is ready and the archive job has been triggered for this session.",
  },
  succeeded: {
    badge: "SUCCEEDED",
    label: "ARCHIVED TO FEISHU",
    note: "This completed session has been archived successfully. You can open the Feishu doc below.",
  },
  failed: {
    badge: "FAILED",
    label: "ARCHIVE FAILED",
    note: "The result is ready, but the Feishu archive step failed. The result below is still valid.",
  },
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSubmitting) {
    return;
  }
  const content = textarea.value.trim();
  if (!content) {
    renderError("请输入一段原始想法后再提交。");
    return;
  }

  currentSessionId = null;
  currentView = null;
  await submitIdea(
    { content, clarifications: [], session_id: null },
    "分析 / ANALYZE",
    submitButton,
  );
});

resetButton.addEventListener("click", () => {
  form.reset();
  clearResult();
  textarea.focus();
});

initializeUi();
void initializeHistory();

function initializeUi() {
  setSidebarCollapsed(false);
  setSearchPanelVisible(false);
  setWorkspaceMode("empty");

  if (historySearchToggleButton instanceof HTMLButtonElement) {
    historySearchToggleButton.addEventListener("click", () => {
      if (document.body.classList.contains("page-sidebar-collapsed")) {
        setSidebarCollapsed(false);
      }

      const shouldOpen = sidebarSearchPanel instanceof HTMLElement
        ? sidebarSearchPanel.classList.contains("hidden")
        : false;
      setSearchPanelVisible(shouldOpen);
    });
  }

  if (sidebarToggleButton instanceof HTMLButtonElement) {
    sidebarToggleButton.addEventListener("click", () => {
      const shouldCollapse = !document.body.classList.contains("page-sidebar-collapsed");
      if (shouldCollapse) {
        setSearchPanelVisible(false);
      }
      setSidebarCollapsed(shouldCollapse);
    });
  }
}

if (historyRefreshButton instanceof HTMLButtonElement) {
  historyRefreshButton.addEventListener("click", async () => {
    if (isSubmitting) {
      return;
    }
    historyRefreshButton.disabled = true;
    await syncRemoteArchiveDeletions();
    historyThreadCache.clear();
    historyThreadLoadErrors.clear();
    try {
      await loadRecentSessions();
      if (
        selectedThreadRootSessionId
        && historyThreadSummaries.some(
          (item) => item.root_session_id === selectedThreadRootSessionId,
        )
      ) {
        await loadThreadView(selectedThreadRootSessionId);
      } else if (selectedThreadRootSessionId) {
        clearResult();
      }
    } finally {
      historyRefreshButton.disabled = false;
    }
  });
}

attachSessionActionContainer(historyShell);
attachSessionActionContainer(threadContextPanel);

resultContent.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  if (isSubmitting) {
    return;
  }

  if (target.matches("[data-action='reset']")) {
    form.reset();
    clearResult();
    textarea.focus();
    return;
  }

  if (target.matches("[data-action='rerun-analysis']")) {
    await handleClarificationRerun(target);
    return;
  }

  if (target.matches("[data-action='start-follow-up']")) {
    renderFollowUpComposer();
    return;
  }

  if (target.matches("[data-action='restore-follow-up-draft']")) {
    const sessionId = target.getAttribute("data-session-id");
    if (sessionId) {
      await openHistorySession(sessionId);
    }
    return;
  }

  if (target.matches("[data-action='submit-follow-up']")) {
    await handleFollowUpRefine(target);
    return;
  }

  if (target.matches("[data-action='rerun-follow-up']")) {
    await handleFollowUpClarificationRerun(target);
    return;
  }

  if (target.matches("[data-action='compose-full-plan']")) {
    await handleComposeFullPlan(target);
  }
});

async function handleClarificationRerun(triggerButton) {
  const content = currentView && currentView.rawContent ? currentView.rawContent : textarea.value.trim();
  const questionCards = Array.from(resultContent.querySelectorAll("[data-question-card]"));
  const clarifications = [];

  for (const card of questionCards) {
    const question = card.getAttribute("data-question") || "";
    const input = card.querySelector("[data-question-input]");
    const answer = input instanceof HTMLTextAreaElement ? input.value.trim() : "";
    if (!answer) {
      renderError("请先回答全部澄清问题，再重新分析。");
      return;
    }
    clarifications.push({ question, answer });
  }

  if (!clarifications.length) {
    renderError("当前没有可提交的澄清回答。");
    return;
  }

  await submitIdea(
    { content, clarifications, session_id: currentSessionId },
    "补充并重新分析 / RE-RUN",
    triggerButton,
  );
}

async function handleFollowUpRefine(triggerButton) {
  if (!currentView || !currentView.sessionId) {
    renderError("当前没有可继续完善的结果。");
    return;
  }

  const input = resultContent.querySelector("[data-follow-up-input]");
  const question = input instanceof HTMLTextAreaElement ? input.value.trim() : "";
  if (!question) {
    renderError("请输入你想继续完善的问题。");
    return;
  }

  currentView.followUpQuestion = question;
  await submitFollowUpRefine(
    {
      session_id: null,
      parent_session_id: currentView.sessionId,
      question,
      clarifications: [],
    },
    "继续完善 / REFINE",
    triggerButton,
  );
}

async function handleFollowUpClarificationRerun(triggerButton) {
  if (!currentView || !currentView.parentSessionId || !currentView.followUpQuestion) {
    renderError("当前没有可继续补充的 follow-up 请求。");
    return;
  }

  const questionCards = Array.from(resultContent.querySelectorAll("[data-question-card]"));
  const clarifications = [];

  for (const card of questionCards) {
    const question = card.getAttribute("data-question") || "";
    const input = card.querySelector("[data-question-input]");
    const answer = input instanceof HTMLTextAreaElement ? input.value.trim() : "";
    if (!answer) {
      renderError("请先回答全部 follow-up 澄清问题。");
      return;
    }
    clarifications.push({ question, answer });
  }

  if (!clarifications.length) {
    renderError("当前没有可提交的 follow-up 澄清回答。");
    return;
  }

  await submitFollowUpRefine(
    {
      session_id: currentSessionId,
      parent_session_id: currentView.parentSessionId,
      question: currentView.followUpQuestion,
      clarifications,
    },
    "补充并继续完善 / RE-RUN",
    triggerButton,
  );
}

async function handleComposeFullPlan(triggerButton) {
  if (!currentView || !currentView.sessionId || currentView.kind !== "follow_up_refinement") {
    renderError("当前没有可合成新版完整方案的 refinement 结果。");
    return;
  }

  setLoadingState(true, "生成新版完整方案 / COMPOSE", triggerButton);
  clearFeedback();

  try {
    const response = await fetch("/api/v1/follow-up/compose-full-plan", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ parent_session_id: currentView.sessionId }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      renderApiError(data, "生成新版完整方案失败，请稍后重试。");
      return;
    }

    currentSessionId = typeof data.session_id === "string" ? data.session_id : null;
    currentView = {
      kind: "full_plan_composed",
      sessionId: data.session_id,
      rawContent: currentView.rawContent,
      clarifications: [],
    };
    renderComposedPlanView(data);
    await refreshHistoryAfterMutation(data);
  } catch (error) {
    renderError(error instanceof Error ? error.message : "网络异常，请稍后重试。");
  } finally {
    setLoadingState(false, "分析 / ANALYZE", triggerButton);
  }
}

async function submitIdea(payload, loadingLabel, triggerButton) {
  setLoadingState(true, loadingLabel, triggerButton);
  clearFeedback();

  try {
    const response = await fetch("/api/v1/idea-analysis", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      renderApiError(data, "请求失败，请稍后重试。");
      return;
    }

    currentSessionId = typeof data.session_id === "string" ? data.session_id : currentSessionId;

    if (data.needs_clarification === true) {
      currentView = {
        kind: "analysis_clarification",
        sessionId: data.session_id,
        rawContent: payload.content,
      };
      renderClarificationView(data, payload.content);
      await refreshHistoryAfterMutation(data);
      return;
    }

    if (data.needs_clarification === false) {
      currentView = {
        kind: "analysis",
        sessionId: data.session_id,
        rawContent: payload.content,
        clarifications: payload.clarifications || [],
      };
      renderAnalysisView(data, payload.content, payload.clarifications || []);
      await refreshHistoryAfterMutation(data);
      return;
    }

    renderError("返回结果不符合预期契约。");
  } catch (error) {
    renderError(error instanceof Error ? error.message : "网络异常，请稍后重试。");
  } finally {
    setLoadingState(false, "分析 / ANALYZE", triggerButton);
  }
}

async function submitFollowUpRefine(payload, loadingLabel, triggerButton) {
  setLoadingState(true, loadingLabel, triggerButton);
  clearFeedback();

  try {
    const response = await fetch("/api/v1/follow-up/refine", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      renderApiError(data, "继续完善失败，请稍后重试。");
      return;
    }

    currentSessionId = typeof data.session_id === "string" ? data.session_id : currentSessionId;

    if (data.needs_clarification === true) {
      currentView = {
        kind: "follow_up_clarification",
        sessionId: data.session_id,
        parentSessionId: payload.parent_session_id,
        rawContent: currentView && currentView.rawContent ? currentView.rawContent : textarea.value.trim(),
        followUpQuestion: payload.question,
      };
      renderFollowUpClarificationView(data, payload.question);
      await refreshHistoryAfterMutation(data);
      return;
    }

    currentView = {
      kind: "follow_up_refinement",
      sessionId: data.session_id,
      parentSessionId: payload.parent_session_id,
      rawContent: currentView && currentView.rawContent ? currentView.rawContent : textarea.value.trim(),
      followUpQuestion: payload.question,
    };
    renderRefinementView(data);
    await refreshHistoryAfterMutation(data);
  } catch (error) {
    renderError(error instanceof Error ? error.message : "网络异常，请稍后重试。");
  } finally {
    setLoadingState(false, "分析 / ANALYZE", triggerButton);
  }
}

async function initializeHistory() {
  await loadRecentSessions();
}

function attachSessionActionContainer(container) {
  if (!(container instanceof HTMLElement)) {
    return;
  }

  container.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || isSubmitting) {
      return;
    }

    if (target.matches("[data-action='open-history-session']")) {
      const sessionId = target.getAttribute("data-session-id");
      if (sessionId) {
        await openHistorySession(sessionId);
      }
      return;
    }

    if (target.matches("[data-action='continue-history-follow-up']")) {
      const sessionId = target.getAttribute("data-session-id");
      if (sessionId) {
        await openHistorySession(sessionId, { openComposer: true });
      }
      return;
    }

    if (target.matches("[data-action='toggle-history-thread']")) {
      const rootSessionId = target.getAttribute("data-root-session-id");
      if (rootSessionId) {
        await toggleHistoryThread(rootSessionId);
      }
      return;
    }

    if (target.matches("[data-action='delete-history-thread']")) {
      const rootSessionId = target.getAttribute("data-root-session-id");
      if (rootSessionId) {
        await handleDeleteHistoryThread(rootSessionId, target);
      }
    }
  });
}

async function refreshHistoryAfterMutation(payload) {
  await loadRecentSessions();

  const sessionId = typeof payload.session_id === "string" ? payload.session_id : null;
  const rootSessionId = typeof payload.root_session_id === "string" ? payload.root_session_id : null;

  if (sessionId) {
    selectedHistorySessionId = sessionId;
  }
  if (rootSessionId) {
    selectedThreadRootSessionId = rootSessionId;
    expandedHistoryRootIds.add(rootSessionId);
    historyThreadLoadErrors.delete(rootSessionId);
    historyThreadCache.delete(rootSessionId);
    loadingHistoryRootIds.add(rootSessionId);
    await loadThreadView(rootSessionId);
  }
}

async function loadRecentSessions() {
  if (!(historySessionList instanceof HTMLElement)) {
    return;
  }

  historySessionList.innerHTML = "<p class=\"history-empty\">Loading history...</p>";

  try {
    const response = await fetch("/api/v1/threads?limit=24");
    const data = await response.json().catch(() => ({ items: [] }));

    if (!response.ok) {
      historyThreadSummaries = [];
      historySessionList.innerHTML = "<p class=\"history-empty\">Failed to load history.</p>";
      return;
    }

    const items = Array.isArray(data.items) ? data.items : [];
    historyThreadSummaries = items;
    renderHistorySessionList(items);
  } catch (_error) {
    historyThreadSummaries = [];
    historySessionList.innerHTML = "<p class=\"history-empty\">Failed to load history.</p>";
  }
}

async function syncRemoteArchiveDeletions() {
  try {
    const response = await fetch("/api/v1/threads/sync-remote-archives", {
      method: "POST",
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      return;
    }

    const removedSessionIds = Array.isArray(data.removed_session_ids)
      ? data.removed_session_ids.filter((item) => typeof item === "string")
      : [];

    if (
      selectedHistorySessionId
      && removedSessionIds.includes(selectedHistorySessionId)
    ) {
      clearResult();
    }
  } catch (_error) {
    // Refresh should still continue to local history reload even if remote sync fails.
  }
}

async function loadThreadView(rootSessionId) {
  if (!(historyThreadContent instanceof HTMLElement) || !rootSessionId) {
    resetThreadContextPanel();
    return;
  }

  setThreadContextVisible(true);
  historyThreadContent.innerHTML = "<p class=\"history-empty\">Loading thread...</p>";

  try {
    const response = await fetch(`/api/v1/threads/${encodeURIComponent(rootSessionId)}`);
    const data = await response.json().catch(() => ({ items: [] }));

    if (!response.ok) {
      historyThreadLoadErrors.set(rootSessionId, "failed");
      loadingHistoryRootIds.delete(rootSessionId);
      if (expandedHistoryRootIds.has(rootSessionId)) {
        renderHistorySessionList(historyThreadSummaries);
      }
      historyThreadContent.innerHTML = "<p class=\"history-empty\">Failed to load thread.</p>";
      return;
    }

    selectedThreadRootSessionId = rootSessionId;
    historyThreadLoadErrors.delete(rootSessionId);
    historyThreadCache.set(rootSessionId, data);
    loadingHistoryRootIds.delete(rootSessionId);
    if (expandedHistoryRootIds.has(rootSessionId)) {
      renderHistorySessionList(historyThreadSummaries);
    }
    renderThreadView(data);
  } catch (_error) {
    historyThreadLoadErrors.set(rootSessionId, "failed");
    loadingHistoryRootIds.delete(rootSessionId);
    if (expandedHistoryRootIds.has(rootSessionId)) {
      renderHistorySessionList(historyThreadSummaries);
    }
    historyThreadContent.innerHTML = "<p class=\"history-empty\">Failed to load thread.</p>";
  }
}

async function openHistorySession(sessionId, options = {}) {
  const { openComposer = false } = options;

  clearFeedback();

  try {
    const response = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      renderApiError(data, "Failed to load session detail.");
      return;
    }

    selectedHistorySessionId = data.session_id;
    selectedThreadRootSessionId = data.root_session_id;
    currentSessionId = typeof data.session_id === "string" ? data.session_id : currentSessionId;
    expandedHistoryRootIds.add(data.root_session_id);
    historyThreadLoadErrors.delete(data.root_session_id);
    historyThreadCache.delete(data.root_session_id);
    loadingHistoryRootIds.add(data.root_session_id);
    populateInputFromDetail(data);
    renderHistoryDetail(data);
    await loadRecentSessions();
    await loadThreadView(data.root_session_id);

    if (openComposer && data.can_continue_follow_up) {
      renderFollowUpComposer();
    }
  } catch (_error) {
    renderError("Failed to load session detail.");
  }
}

function renderHistorySessionList(items) {
  if (!(historySessionList instanceof HTMLElement)) {
    return;
  }

  if (!Array.isArray(items) || !items.length) {
    historySessionList.innerHTML = "<p class=\"history-empty\">No completed local threads yet.</p>";
    return;
  }

  const buckets = groupThreadsByRecency(items);
  historySessionList.innerHTML = `
    <div class="history-list">
      ${buckets.map((bucket) => renderHistoryBucket(bucket)).join("")}
    </div>
  `;
}

function renderHistorySessionItem(item) {
  const isActive = item.session_id === selectedHistorySessionId;
  const archiveBadge = renderHistoryArchiveBadge(item.archive_status);
  const continueAction = item.can_continue_follow_up
    ? `
      <button
        class="history-open"
        type="button"
        data-action="continue-history-follow-up"
        data-session-id="${escapeHtml(item.session_id)}"
      >
        继续完善 / CONTINUE FOLLOW-UP
      </button>
    `
    : "";

  return `
    <article class="history-item ${isActive ? "is-active" : ""}">
      <div class="history-item-head">
        <div>
          <h3 class="history-item-title">${escapeHtml(item.archive_title || "Untitled Session")}</h3>
          <p class="history-item-copy">${escapeHtml(formatSessionKindLabel(item.session_kind))}</p>
        </div>
        ${archiveBadge}
      </div>
      <p class="history-item-copy">Session ${escapeHtml(item.session_id)}</p>
      <p class="history-item-copy">Updated ${escapeHtml(formatDateTime(item.updated_at))}</p>
      <div class="history-item-actions">
        <button
          class="history-open"
          type="button"
          data-action="open-history-session"
          data-session-id="${escapeHtml(item.session_id)}"
        >
          打开详情 / OPEN DETAIL
        </button>
        ${continueAction}
      </div>
    </article>
  `;
}

function renderHistoryBucket(bucket) {
  return `
    <section class="history-bucket">
      <div class="history-bucket-label">${escapeHtml(bucket.label)}</div>
      <div class="history-folder-list">
        ${bucket.items.map((item) => renderHistoryThreadSummary(item)).join("")}
      </div>
    </section>
  `;
}

function renderHistoryThreadSummary(item) {
  const isActive = item.root_session_id === selectedThreadRootSessionId;
  const isExpanded = expandedHistoryRootIds.has(item.root_session_id);
  const sessionCount = Number.isFinite(item.session_count) ? Number(item.session_count) : 0;
  const versionsLabel = sessionCount === 1 ? "1 个版本 / VERSION" : `${sessionCount} 个版本 / VERSIONS`;
  const children = renderHistoryThreadChildren(item.root_session_id);
  const archiveBadge = renderHistoryArchiveBadge(item.latest_archive_status);

  return `
    <article class="history-folder ${isActive ? "is-active" : ""}">
      <div class="history-folder-head">
        <button
          class="history-folder-toggle"
          type="button"
          data-action="toggle-history-thread"
          data-root-session-id="${escapeHtml(item.root_session_id)}"
          aria-label="${isExpanded ? "收起版本" : "展开版本"}"
          title="${isExpanded ? "收起版本 / Collapse versions" : "展开版本 / Expand versions"}"
        >
          ${isExpanded ? "▾" : "▸"}
        </button>
        <div class="history-folder-copy">
          <h3 class="history-item-title">${escapeHtml(item.root_archive_title || "Untitled Thread")}</h3>
          <div class="history-folder-summary">
            <span class="history-count-badge">${escapeHtml(versionsLabel)}</span>
            <p class="history-item-copy">Latest ${escapeHtml(formatDateTime(item.latest_updated_at))}</p>
          </div>
        </div>
        <div class="history-folder-actions">
          ${archiveBadge}
          <button
            class="history-icon-button"
            type="button"
            data-action="open-history-session"
            data-session-id="${escapeHtml(item.latest_session_id)}"
            aria-label="打开最新版本"
            title="打开最新版本 / Open latest version"
          >
            ↗
          </button>
          <button
            class="history-icon-button history-icon-button-danger"
            type="button"
            data-action="delete-history-thread"
            data-root-session-id="${escapeHtml(item.root_session_id)}"
            aria-label="删除这条想法线程"
            title="删除这条想法线程并尝试清理关联飞书归档 / Delete thread"
          >
            ×
          </button>
        </div>
      </div>
      ${children}
    </article>
  `;
}

function renderHistoryThreadChildren(rootSessionId) {
  if (!expandedHistoryRootIds.has(rootSessionId)) {
    return "";
  }

  if (loadingHistoryRootIds.has(rootSessionId)) {
    return `
      <div class="history-folder-children">
        <p class="history-item-copy history-placeholder-copy">正在加载版本… / Loading versions...</p>
      </div>
    `;
  }

  if (historyThreadLoadErrors.has(rootSessionId)) {
    return `
      <div class="history-folder-children">
        <p class="history-item-copy history-placeholder-copy">版本加载失败，请稍后重试。 / Failed to load versions.</p>
      </div>
    `;
  }

  const payload = historyThreadCache.get(rootSessionId);
  const items = payload && Array.isArray(payload.items) ? payload.items : [];
  if (!items.length) {
    return `
      <div class="history-folder-children">
        <p class="history-item-copy history-placeholder-copy">当前没有可显示的正式版本。 / No formal versions yet.</p>
      </div>
    `;
  }

  return `
    <div class="history-folder-children">
      <div class="history-version-list">
        ${items.map((threadItem, index) => (
          renderHistoryVersionItem(threadItem, index)
        )).join("")}
      </div>
    </div>
  `;
}

function renderHistoryVersionItem(item, index) {
  const isActive = item.session_id === selectedHistorySessionId;
  const archiveBadge = renderHistoryArchiveBadge(item.archive_status);
  const versionIndexLabel = `V${String(index + 1).padStart(2, "0")}`;
  const versionLabel = item.session_id === item.root_session_id
    ? `${versionIndexLabel} ROOT`
    : versionIndexLabel;
  const kindLabel = item.session_id === item.root_session_id
    ? "ROOT ANALYSIS / 根分析"
    : formatSessionKindLabel(item.session_kind);

  return `
    <article class="history-version-item ${isActive ? "is-active" : ""}">
      <div class="history-version-main">
        <div class="history-version-copy">
          <div class="history-version-headline">
            <div class="history-version-order">${escapeHtml(versionLabel)}</div>
            <p class="history-item-copy">${escapeHtml(kindLabel)}</p>
            ${archiveBadge}
          </div>
          <p class="history-item-copy">Updated ${escapeHtml(formatDateTime(item.updated_at))}</p>
        </div>
        <div class="history-version-actions">
          <button
            class="history-icon-button"
            type="button"
            data-action="open-history-session"
            data-session-id="${escapeHtml(item.session_id)}"
            aria-label="打开这个版本"
            title="打开这个版本 / Open this version"
          >
            ↗
          </button>
          <button
            class="history-icon-button history-icon-button-placeholder"
            type="button"
            disabled
            aria-label="版本删除占位"
            title="当前仅支持按想法线程整体删除，单版本删除后续再接入。"
          >
            ×
          </button>
        </div>
      </div>
    </article>
  `;
}

async function handleDeleteHistoryThread(rootSessionId, triggerButton) {
  const normalizedRootSessionId = typeof rootSessionId === "string" ? rootSessionId.trim() : "";
  if (!normalizedRootSessionId) {
    return;
  }

  const confirmed = window.confirm(
    "Delete this idea thread from local SQLite and attempt to delete its linked Feishu docs?",
  );
  if (!confirmed) {
    return;
  }

  setLoadingState(true, "DELETE THREAD", triggerButton);
  clearFeedback();

  try {
    const response = await fetch(`/api/v1/threads/${encodeURIComponent(normalizedRootSessionId)}`, {
      method: "DELETE",
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      renderApiError(data, "Failed to delete thread.");
      return;
    }

    clearDeletedThreadState(normalizedRootSessionId);
    await loadRecentSessions();

    const failures = Array.isArray(data.archive_delete_failures)
      ? data.archive_delete_failures
      : [];
    if (failures.length) {
      window.alert(
        `Local thread deleted, but ${failures.length} linked Feishu archive(s) could not be removed.`,
      );
    }
  } catch (_error) {
    renderError("Failed to delete thread.");
  } finally {
    setLoadingState(false, "分析 / ANALYZE", triggerButton);
  }
}

function clearDeletedThreadState(rootSessionId) {
  historyThreadSummaries = historyThreadSummaries.filter(
    (item) => item.root_session_id !== rootSessionId,
  );
  expandedHistoryRootIds.delete(rootSessionId);
  historyThreadCache.delete(rootSessionId);
  historyThreadLoadErrors.delete(rootSessionId);
  loadingHistoryRootIds.delete(rootSessionId);

  if (selectedThreadRootSessionId === rootSessionId) {
    clearResult();
    return;
  }

  renderHistorySessionList(historyThreadSummaries);
}

async function toggleHistoryThread(rootSessionId) {
  const normalizedRootSessionId = typeof rootSessionId === "string" ? rootSessionId.trim() : "";
  if (!normalizedRootSessionId) {
    return;
  }

  if (expandedHistoryRootIds.has(normalizedRootSessionId)) {
    expandedHistoryRootIds.delete(normalizedRootSessionId);
    renderHistorySessionList(historyThreadSummaries);
    return;
  }

  expandedHistoryRootIds.add(normalizedRootSessionId);
  historyThreadLoadErrors.delete(normalizedRootSessionId);
  renderHistorySessionList(historyThreadSummaries);

  if (historyThreadCache.has(normalizedRootSessionId) || loadingHistoryRootIds.has(normalizedRootSessionId)) {
    return;
  }

  loadingHistoryRootIds.add(normalizedRootSessionId);
  renderHistorySessionList(historyThreadSummaries);

  try {
    const response = await fetch(`/api/v1/threads/${encodeURIComponent(normalizedRootSessionId)}`);
    const data = await response.json().catch(() => ({ items: [] }));

    if (!response.ok) {
      historyThreadLoadErrors.set(normalizedRootSessionId, "failed");
      return;
    }

    historyThreadCache.set(normalizedRootSessionId, data);
    historyThreadLoadErrors.delete(normalizedRootSessionId);
  } catch (_error) {
    historyThreadLoadErrors.set(normalizedRootSessionId, "failed");
  } finally {
    loadingHistoryRootIds.delete(normalizedRootSessionId);
    renderHistorySessionList(historyThreadSummaries);
  }
}

function renderThreadView(payload) {
  if (!(historyThreadContent instanceof HTMLElement)) {
    return;
  }

  const items = Array.isArray(payload.items) ? payload.items : [];
  if (!items.length) {
    setThreadContextVisible(true);
    historyThreadContent.innerHTML = "<p class=\"history-empty\">No sessions found in this thread.</p>";
    return;
  }

  const rootTitle = items[0].archive_title || "Untitled Thread";
  setThreadContextVisible(true);
  historyThreadContent.innerHTML = `
    <section class="thread-panel-headline">
      <div class="assumptions-label">THREAD ROOT / 根链路</div>
      <h3 class="thread-title">${escapeHtml(rootTitle)}</h3>
      <p class="thread-meta-copy">Root session ${escapeHtml(payload.root_session_id || "")}</p>
      <p class="thread-meta-copy">Contains ${escapeHtml(String(items.length))} session nodes.</p>
    </section>
    <div class="history-list">
      ${items.map((item) => renderThreadItem(item)).join("")}
    </div>
  `;
}

function renderThreadItem(item) {
  const isActive = item.session_id === selectedHistorySessionId;
  const archiveBadge = renderHistoryArchiveBadge(item.archive_status);
  const continueAction = item.can_continue_follow_up
    ? `
      <button
        class="history-thread-action"
        type="button"
        data-action="continue-history-follow-up"
        data-session-id="${escapeHtml(item.session_id)}"
      >
        从这里继续 / CONTINUE HERE
      </button>
    `
    : "";

  return `
    <article class="thread-item ${isActive ? "is-active" : ""}">
      <div class="thread-item-head">
        <div>
          <h3 class="thread-item-title">${escapeHtml(item.archive_title || "Untitled Session")}</h3>
          <p class="thread-meta-copy">${escapeHtml(formatSessionKindLabel(item.session_kind))}</p>
        </div>
        ${archiveBadge}
      </div>
      <p class="thread-meta-copy">Session ${escapeHtml(item.session_id)}</p>
      <p class="thread-meta-copy">Updated ${escapeHtml(formatDateTime(item.updated_at))}</p>
      <div class="thread-item-actions">
        <button
          class="history-thread-action"
          type="button"
          data-action="open-history-session"
          data-session-id="${escapeHtml(item.session_id)}"
        >
          查看结果 / VIEW RESULT
        </button>
        ${continueAction}
      </div>
    </article>
  `;
}

function renderHistoryDetail(detail) {
  const sessionKind = typeof detail.session_kind === "string" ? detail.session_kind : "analysis";
  const clarifications = Array.isArray(detail.clarifications) ? detail.clarifications : [];

  if (sessionKind === "analysis") {
    currentView = {
      kind: "analysis",
      sessionId: detail.session_id,
      rawContent: detail.original_content,
      clarifications,
    };
    renderAnalysisView(detail, detail.original_content, clarifications);
    return;
  }

  if (sessionKind === "follow_up_refinement") {
    currentView = {
      kind: "follow_up_refinement",
      sessionId: detail.session_id,
      parentSessionId: detail.parent_session_id,
      rawContent: detail.original_content,
      followUpQuestion: detail.follow_up_question || "",
    };
    renderRefinementView(detail);
    return;
  }

  currentView = {
    kind: "full_plan_composed",
    sessionId: detail.session_id,
    rawContent: detail.original_content,
    clarifications,
  };
  renderComposedPlanView(detail);
}

function populateInputFromDetail(detail) {
  if (!(textarea instanceof HTMLTextAreaElement)) {
    return;
  }

  textarea.value = typeof detail.original_content === "string" ? detail.original_content : "";
}

function renderClarificationView(payload, rawContent) {
  const assumptions = renderListItems(payload.assumptions, "当前没有额外系统假设。");
  const questions = renderQuestionCards(payload.open_questions || []);

  resultContent.innerHTML = `
    ${renderStatusBar(
      "NEEDS CLARIFICATION",
      "One clarification round is open because the current input still lacks a few key constraints.",
      "info",
    )}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    <section class="questions-shell">
      <div class="section-head section-head-single">
        <h2 class="section-title">OPEN QUESTIONS / 关键澄清</h2>
      </div>
      <div class="questions-grid">${questions}</div>
      <div class="result-actions">
        <button class="question-submit" type="button" data-action="rerun-analysis" data-content="${escapeHtml(rawContent)}">
          补充并重新分析 / RE-RUN
        </button>
        <button class="secondary-button" type="button" data-action="reset">重新开始 / RESET</button>
      </div>
    </section>
  `;
  showContent();
}

function renderAnalysisView(payload, rawContent, clarifications) {
  const assumptions = renderListItems(payload.assumptions, "当前没有额外系统假设。");
  const analysisGrid = renderAnalysisGrid(payload.analysis);
  const draftRecovery = renderDraftRecoveryBlock(payload);
  const clarificationRecord = renderClarificationRecord(clarifications);
  const followup = renderOpenQuestionSuggestions(payload.open_questions || []);

  resultContent.innerHTML = `
    ${renderStatusBar(
      "ANALYSIS READY",
      "The analysis is ready. You can review it, check archive feedback, and continue with follow-up refinement.",
      "success",
    )}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    ${clarificationRecord}
    <section class="analysis-shell">
      <div class="analysis-grid">${analysisGrid}</div>
    </section>
    ${followup}
    ${draftRecovery}
    ${renderFollowUpEntry()}
    <div class="result-actions">
      <button class="secondary-button" type="button" data-action="reset">
        重新开始 / RESET
      </button>
    </div>
  `;
  showContent();
}

function renderFollowUpComposer() {
  if (
    !currentView
    || (currentView.kind !== "analysis" && currentView.kind !== "full_plan_composed")
  ) {
    return;
  }
  const existingComposer = resultContent.querySelector("[data-follow-up-composer]");
  if (existingComposer instanceof HTMLElement) {
    const existingInput = existingComposer.querySelector("[data-follow-up-input]");
    if (existingInput instanceof HTMLTextAreaElement) {
      existingInput.focus();
    }
    return;
  }

  const composer = `
    <section class="followup-block" data-follow-up-composer>
      <div class="assumptions-label">FOLLOW-UP / 继续完善方案</div>
      <p class="analysis-copy">
        基于当前这版完整分析，输入你想继续追问、收窄或修改的方向。系统会先返回局部完善结果，
        你再决定是否确认修改并生成新版完整方案。
      </p>
      <textarea
        class="question-input"
        rows="5"
        placeholder="例如：我想把目标用户进一步收窄到没有产品背景的独立开发者。"
        data-follow-up-input
      ></textarea>
      <div class="result-actions">
        <button class="question-submit" type="button" data-action="submit-follow-up">
          继续完善 / REFINE
        </button>
      </div>
    </section>
  `;

  resultContent.insertAdjacentHTML("beforeend", composer);
}

function renderDraftRecoveryBlock(payload) {
  const draftSessionId = typeof payload.active_follow_up_draft_id === "string"
    ? payload.active_follow_up_draft_id
    : "";
  if (!draftSessionId) {
    return "";
  }

  const draftQuestion = typeof payload.active_follow_up_draft_question === "string"
    && payload.active_follow_up_draft_question
    ? payload.active_follow_up_draft_question
    : "A saved follow-up draft is available for recovery.";
  const updatedAt = typeof payload.active_follow_up_draft_updated_at === "string"
    && payload.active_follow_up_draft_updated_at
    ? formatDateTime(payload.active_follow_up_draft_updated_at)
    : "N/A";

  return `
    <section class="followup-block followup-draft-recovery">
      <div class="assumptions-label">LOCAL DRAFT / 可恢复草稿</div>
      <p class="analysis-copy">${escapeHtml(draftQuestion)}</p>
      <p class="analysis-copy">This draft stays in local SQLite for 7 days unless you confirm compose or let it expire.</p>
      <div class="result-actions">
        <button
          class="secondary-button"
          type="button"
          data-action="restore-follow-up-draft"
          data-session-id="${escapeHtml(draftSessionId)}"
        >
          恢复上次局部完善 / RESTORE DRAFT
        </button>
        <span class="history-inline-meta">Updated ${escapeHtml(updatedAt)}</span>
      </div>
    </section>
  `;
}

function renderFollowUpClarificationView(payload, followUpQuestion) {
  const assumptions = renderListItems(payload.assumptions, "当前没有额外系统假设。");
  const questions = renderQuestionCards(payload.open_questions || []);

  resultContent.innerHTML = `
    ${renderStatusBar(
      "FOLLOW-UP NEEDS CLARIFICATION",
      "The follow-up request still needs one more clarification round before refinement can be generated.",
      "attention",
    )}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    <section class="input-echo">
      <div class="assumptions-label">FOLLOW-UP QUESTION / 继续完善问题</div>
      <p class="analysis-copy">${escapeHtml(followUpQuestion)}</p>
    </section>
    <section class="questions-shell">
      <div class="section-head section-head-single">
        <h2 class="section-title">OPEN QUESTIONS / 继续澄清</h2>
      </div>
      <div class="questions-grid">${questions}</div>
      <div class="result-actions">
        <button class="question-submit" type="button" data-action="rerun-follow-up">
          补充并继续完善 / RE-RUN
        </button>
        <button class="secondary-button" type="button" data-action="reset">重新开始 / RESET</button>
      </div>
    </section>
  `;
  showContent();
}

function renderRefinementView(payload) {
  const assumptions = renderListItems(payload.assumptions, "当前没有额外系统假设。");
  const refinement = payload.refinement_result || {};
  const affectedSections = Array.isArray(refinement.affected_sections)
    ? refinement.affected_sections.map((item) => formatSectionKeyLabel(item))
    : [];
  const updates = Array.isArray(refinement.proposed_section_updates)
    ? refinement.proposed_section_updates
    : [];
  const nextActions = renderListItems(refinement.next_actions || [], "当前没有额外后续动作。");

  resultContent.innerHTML = `
    ${renderStatusBar(
      "REFINEMENT READY",
      "The local refinement result is ready. Confirm when you want to merge it into a new full plan.",
      "success",
    )}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    <section class="analysis-shell">
      <div class="section-head section-head-single">
        <h2 class="section-title">REFINEMENT RESULT / 局部完善结果</h2>
      </div>
      <div class="analysis-grid">
        <section class="analysis-section analysis-span-12">
          <div class="analysis-index">01</div>
          <h3 class="analysis-title">QUESTION SUMMARY / 问题摘要</h3>
          <p class="analysis-copy">${escapeHtml(refinement.question_summary || "N/A")}</p>
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-index">02</div>
          <h3 class="analysis-title">REFINEMENT ANSWER / 局部完善回答</h3>
          <p class="analysis-copy">${escapeHtml(refinement.refinement_answer || "N/A")}</p>
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-index">03</div>
          <h3 class="analysis-title">AFFECTED SECTIONS / 受影响板块</h3>
          ${renderArrayBlock(affectedSections)}
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-index">04</div>
          <h3 class="analysis-title">PROPOSED SECTION UPDATES / 建议修改内容</h3>
          ${renderSectionUpdates(updates)}
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-index">05</div>
          <h3 class="analysis-title">NEXT ACTIONS / 后续动作</h3>
          <ul class="analysis-list">${nextActions}</ul>
        </section>
      </div>
    </section>
    <div class="result-actions">
      <button class="question-submit" type="button" data-action="compose-full-plan">
        确认修改并生成新版完整方案
      </button>
      <button class="secondary-button" type="button" data-action="reset">
        重新开始 / RESET
      </button>
    </div>
  `;
  showContent();
}

function renderComposedPlanView(payload) {
  const assumptions = renderListItems(payload.assumptions, "当前没有额外系统假设。");
  const analysisGrid = renderAnalysisGrid(payload.analysis);
  const draftRecovery = renderDraftRecoveryBlock(payload);
  const refinementBlock = payload.refinement_result
    ? `
      <section class="followup-block">
        <div class="assumptions-label">COMPOSED FROM / 合成来源</div>
        <p class="analysis-copy">${escapeHtml(payload.refinement_result.refinement_answer || "")}</p>
      </section>
    `
    : "";

  resultContent.innerHTML = `
    ${renderStatusBar(
      "NEW FULL PLAN READY",
      "The updated full plan has been composed from the approved refinement and is ready for another follow-up round.",
      "success",
    )}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    ${refinementBlock}
    <section class="analysis-shell">
      <div class="analysis-grid">${analysisGrid}</div>
    </section>
    ${renderOpenQuestionSuggestions(payload.open_questions || [])}
    ${draftRecovery}
    ${renderFollowUpEntry()}
    <div class="result-actions">
      <button class="secondary-button" type="button" data-action="reset">
        重新开始 / RESET
      </button>
    </div>
  `;
  showContent();
}

function renderStatusBar(label, note = "", tone = "neutral") {
  const normalizedTone = typeof tone === "string" && tone ? tone : "neutral";
  const noteBlock = note
    ? `<p class="result-status-note">${escapeHtml(note)}</p>`
    : "";
  return `
    <div class="result-status-bar result-status-bar-${escapeHtml(normalizedTone)}">
      <div class="result-status-label">STATUS</div>
      <div class="result-status-copy">
        <div class="result-status-value">${escapeHtml(label)}</div>
        ${noteBlock}
      </div>
    </div>
  `;
}

function renderArchivePanel(payload) {
  const sessionId = typeof payload.session_id === "string" && payload.session_id
    ? payload.session_id
    : "N/A";
  const rootSessionId = typeof payload.root_session_id === "string" && payload.root_session_id
    ? payload.root_session_id
    : null;
  const sessionKind = typeof payload.session_kind === "string" && payload.session_kind
    ? payload.session_kind
    : "analysis";
  const parentSessionId = typeof payload.parent_session_id === "string" && payload.parent_session_id
    ? payload.parent_session_id
    : null;
  const archiveTitle = typeof payload.archive_title === "string" && payload.archive_title
    ? payload.archive_title
    : "N/A";
  const archiveStatus = typeof payload.archive_status === "string" && payload.archive_status
    ? payload.archive_status
    : "not_triggered";
  const statusMeta = resolveArchivePanelStatusMeta(payload, archiveStatus, sessionKind);
  const archiveLink = typeof payload.archive_url === "string" && payload.archive_url
    ? payload.archive_url
    : null;
  const parentRow = parentSessionId
    ? `
      <article class="archive-meta-item">
        <div class="archive-meta-label">PARENT SESSION</div>
        <div class="archive-meta-value archive-meta-mono">${escapeHtml(parentSessionId)}</div>
      </article>
    `
    : "";
  const rootRow = rootSessionId
    ? `
      <article class="archive-meta-item">
        <div class="archive-meta-label">ROOT SESSION</div>
        <div class="archive-meta-value archive-meta-mono">${escapeHtml(rootSessionId)}</div>
      </article>
    `
    : "";
  const archiveAction = archiveLink
    ? `
      <div class="archive-actions">
        <a
          class="archive-link"
          href="${escapeHtml(archiveLink)}"
          target="_blank"
          rel="noreferrer"
        >
          OPEN FEISHU DOC
        </a>
      </div>
    `
    : "";

  return `
    <section class="archive-panel archive-panel-${escapeHtml(archiveStatus)}">
      <div class="archive-panel-head">
        <div class="assumptions-label">SESSION ARCHIVE / 归档状态</div>
        <div class="archive-badge">${escapeHtml(statusMeta.badge)}</div>
      </div>
      <div class="archive-meta-grid">
        <article class="archive-meta-item">
          <div class="archive-meta-label">SESSION ID</div>
          <div class="archive-meta-value archive-meta-mono">${escapeHtml(sessionId)}</div>
        </article>
        <article class="archive-meta-item">
          <div class="archive-meta-label">SESSION KIND</div>
          <div class="archive-meta-value">${escapeHtml(sessionKind)}</div>
        </article>
        <article class="archive-meta-item">
          <div class="archive-meta-label">ARCHIVE STATUS</div>
          <div class="archive-meta-value">${escapeHtml(statusMeta.label)}</div>
        </article>
        <article class="archive-meta-item">
          <div class="archive-meta-label">ARCHIVE TITLE</div>
          <div class="archive-meta-value">${escapeHtml(archiveTitle)}</div>
        </article>
        ${rootRow}
        ${parentRow}
      </div>
      <p class="archive-note">${escapeHtml(statusMeta.note)}</p>
      ${archiveAction}
    </section>
  `;
}

function resolveArchivePanelStatusMeta(payload, archiveStatus, sessionKind) {
  if (
    sessionKind === "follow_up_refinement"
    && archiveStatus === "not_triggered"
    && payload
    && payload.needs_clarification === false
    && payload.refinement_result
  ) {
    return {
      badge: "LOCAL DRAFT",
      label: "CACHED FOR 7 DAYS",
      note: "This refinement stays in local SQLite for 7 days. Confirm compose to generate and archive a new formal full plan.",
    };
  }

  return getArchiveStatusMeta(archiveStatus);
}

function renderInputEcho(inputEcho) {
  return `
    <section class="input-echo">
      <div class="assumptions-label">INPUT ECHO / 忠实复述</div>
      <p class="input-echo-text">${escapeHtml(inputEcho)}</p>
    </section>
  `;
}

function renderAssumptions(listHtml) {
  return `
    <section class="assumptions-block">
      <div class="assumptions-label">SYSTEM ASSUMPTIONS / 系统假设</div>
      <ul class="assumptions-list">${listHtml}</ul>
    </section>
  `;
}

function renderAnalysisGrid(analysis) {
  return ANALYSIS_FIELDS
    .map(([index, title, key, kind, spanClass]) => {
      const value = analysis ? analysis[key] : null;
      const content = kind === "list" ? renderArrayBlock(value) : renderCopyBlock(value);
      return `
        <section class="analysis-section ${spanClass}">
          <div class="analysis-index">${index}</div>
          <h3 class="analysis-title">${title}</h3>
          ${content}
        </section>
      `;
    })
    .join("");
}

function renderClarificationRecord(clarifications) {
  if (!Array.isArray(clarifications) || !clarifications.length) {
    return "";
  }

  return `
    <section class="clarification-record">
      <div class="assumptions-label">CLARIFICATION RECORD / 已补充信息</div>
      <div class="clarification-grid">
        ${clarifications
          .map((item, index) => `
            <article class="clarification-item">
              <div class="question-index">${String(index + 1).padStart(2, "0")}</div>
              <p class="clarification-question">${escapeHtml(item.question)}</p>
              <div class="clarification-answer">${escapeHtml(item.answer)}</div>
            </article>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function renderOpenQuestionSuggestions(openQuestions) {
  if (!Array.isArray(openQuestions) || !openQuestions.length) {
    return "";
  }

  return `
    <section class="followup-block">
      <div class="assumptions-label">CONTINUE SHARPENING / 可继续打磨的问题</div>
      <div class="followup-grid">
        ${openQuestions
          .map((question, index) => `
            <div class="followup-item">
              <div class="followup-index">${String(index + 1).padStart(2, "0")}</div>
              <div class="followup-copy">${escapeHtml(question)}</div>
            </div>
          `)
          .join("")}
      </div>
    </section>
  `;
}

function renderFollowUpEntry() {
  return `
    <section class="followup-block">
      <div class="assumptions-label">FOLLOW-UP / 继续完善</div>
      <p class="analysis-copy">
        如果你认可当前方向，但想继续收窄、补强或调整某些板块，可以继续发起一轮 follow-up。
      </p>
      <div class="result-actions">
        <button class="question-submit" type="button" data-action="start-follow-up">
          继续完善方案
        </button>
      </div>
    </section>
  `;
}

function renderQuestionCards(questions) {
  return (questions || [])
    .map((question, index) => `
      <article class="question-card" data-question-card data-question="${escapeHtml(question)}">
        <div class="question-index">${String(index + 1).padStart(2, "0")}</div>
        <p class="question-text">${escapeHtml(question)}</p>
        <textarea
          class="question-input"
          rows="4"
          placeholder="在这里补充你的回答"
          data-question-input
        ></textarea>
      </article>
    `)
    .join("");
}

function renderSectionUpdates(updates) {
  if (!Array.isArray(updates) || !updates.length) {
    return "<p class=\"analysis-copy\">暂无局部修改内容。</p>";
  }

  return `
    <div class="clarification-grid">
      ${updates.map((item, index) => {
        const replacement = Array.isArray(item.updated_items) && item.updated_items.length
          ? renderArrayBlock(item.updated_items)
          : renderCopyBlock(item.updated_text);
        return `
          <article class="clarification-item">
            <div class="question-index">${String(index + 1).padStart(2, "0")}</div>
            <p class="clarification-question">${escapeHtml(formatSectionKeyLabel(item.section_key))}</p>
            <div class="clarification-answer">${escapeHtml(item.change_summary || "")}</div>
            ${replacement}
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function renderListItems(items, emptyCopy) {
  if (!Array.isArray(items) || !items.length) {
    return `<li class="assumptions-item">${escapeHtml(emptyCopy)}</li>`;
  }
  return items
    .map((item) => `<li class="assumptions-item">${escapeHtml(String(item))}</li>`)
    .join("");
}

function renderArrayBlock(value) {
  if (!Array.isArray(value) || !value.length) {
    return "<p class=\"analysis-copy\">暂无内容。</p>";
  }

  return `
    <ul class="analysis-list">
      ${value
        .map((item) => `<li class="analysis-list-item">${escapeHtml(String(item))}</li>`)
        .join("")}
    </ul>
  `;
}

function renderCopyBlock(value) {
  if (!value) {
    return "<p class=\"analysis-copy\">暂无内容。</p>";
  }
  return `<p class="analysis-copy">${escapeHtml(String(value))}</p>`;
}

function formatSectionKeyLabel(sectionKey) {
  const normalized = typeof sectionKey === "string" ? sectionKey : "";
  if (normalized && SECTION_DISPLAY_LABELS[normalized]) {
    return SECTION_DISPLAY_LABELS[normalized];
  }
  if (!normalized) {
    return "UNKNOWN / 未知板块";
  }
  return normalized.replaceAll("_", " ").toUpperCase();
}

function formatSessionKindLabel(sessionKind) {
  const normalized = typeof sessionKind === "string" ? sessionKind : "";
  return SESSION_KIND_LABELS[normalized] || normalized.replaceAll("_", " ").toUpperCase();
}

function getArchiveStatusMeta(archiveStatus) {
  const normalized = typeof archiveStatus === "string" ? archiveStatus : "not_triggered";
  return ARCHIVE_STATUS_META[normalized] || ARCHIVE_STATUS_META.not_triggered;
}

function getHistoryStatusClass(archiveStatus) {
  const normalized = typeof archiveStatus === "string" ? archiveStatus : "not_triggered";
  if (normalized === "succeeded") {
    return "history-tag-success";
  }
  if (normalized === "failed") {
    return "history-tag-failed";
  }
  if (normalized === "pending") {
    return "history-tag-pending";
  }
  return "";
}

function renderHistoryArchiveBadge(archiveStatus) {
  if (archiveStatus === "succeeded") {
    return "";
  }

  const statusMeta = getArchiveStatusMeta(archiveStatus);
  return `
    <div class="history-item-meta">
      <span class="history-tag ${getHistoryStatusClass(archiveStatus)}">${escapeHtml(statusMeta.badge)}</span>
    </div>
  `;
}

function formatDateTime(value) {
  if (typeof value !== "string" || !value) {
    return "N/A";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function groupThreadsByRecency(items) {
  const grouped = new Map();

  for (const item of items) {
    const label = formatHistoryBucketLabel(item.latest_updated_at);
    const bucketItems = grouped.get(label) || [];
    bucketItems.push(item);
    grouped.set(label, bucketItems);
  }

  return Array.from(grouped.entries()).map(([label, bucketItems]) => ({
    label,
    items: bucketItems,
  }));
}

function formatHistoryBucketLabel(value) {
  if (typeof value !== "string" || !value) {
    return "更早";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "更早";
  }

  const now = new Date();
  const diffMs = Math.max(0, now.getTime() - date.getTime());
  const diffDays = diffMs / (24 * 60 * 60 * 1000);

  if (diffDays <= 7) {
    return "7天内";
  }
  if (diffDays <= 30) {
    return "30天内";
  }

  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${date.getFullYear()}-${month}`;
}

function renderApiError(data, fallbackMessage) {
  const detail = data && typeof data === "object" ? data.detail : null;
  const message = detail && typeof detail === "object" && "message" in detail
    ? String(detail.message)
    : fallbackMessage;
  renderError(message);
}

function setSidebarCollapsed(isCollapsed) {
  document.body.classList.toggle("page-sidebar-collapsed", isCollapsed);

  if (sidebarToggleButton instanceof HTMLButtonElement) {
    sidebarToggleButton.setAttribute("aria-expanded", String(!isCollapsed));
  }

  if (sidebar instanceof HTMLElement) {
    sidebar.setAttribute("data-collapsed", String(isCollapsed));
  }
}

function setSearchPanelVisible(isVisible) {
  if (sidebarSearchPanel instanceof HTMLElement) {
    sidebarSearchPanel.classList.toggle("hidden", !isVisible);
  }

  if (historySearchToggleButton instanceof HTMLButtonElement) {
    historySearchToggleButton.setAttribute("aria-expanded", String(isVisible));
  }

  if (isVisible && sidebarSearchInput instanceof HTMLInputElement) {
    sidebarSearchInput.focus();
  }
}

function setWorkspaceMode(mode) {
  const isActive = mode === "active";
  document.body.classList.toggle("page-workspace-empty", !isActive);
  document.body.classList.toggle("page-workspace-active", isActive);
}

function setThreadContextVisible(isVisible) {
  if (!(threadContextPanel instanceof HTMLElement)) {
    return;
  }

  threadContextPanel.classList.toggle("hidden", !isVisible);
}

function resetThreadContextPanel() {
  setThreadContextVisible(false);
  if (historyThreadContent instanceof HTMLElement) {
    historyThreadContent.innerHTML = "<p class=\"history-empty\">Select a session to inspect its thread.</p>";
  }
}

function clearActiveSessionMarkers() {
  const activeItems = document.querySelectorAll(
    ".history-folder.is-active, .history-version-item.is-active, .history-item.is-active, .thread-item.is-active",
  );
  for (const item of activeItems) {
    item.classList.remove("is-active");
  }
}

function renderError(message) {
  setWorkspaceMode("active");
  const hasExistingContent = Boolean(resultContent.innerHTML.trim());
  const note = hasExistingContent
    ? "<p class=\"result-error-note\">The previous result is preserved below so you can compare it while debugging.</p>"
    : "<p class=\"result-error-note\">No valid result was rendered for this request.</p>";
  resultError.innerHTML = `
    <div class="section-head">
      <span class="section-index">XX</span>
      <h2 class="section-title">ERROR / 请求失败</h2>
    </div>
    <p class="result-error-copy">${escapeHtml(message)}</p>
    ${note}
  `;
  resultPlaceholder.classList.add("hidden");
  resultError.classList.remove("hidden");

  if (!resultContent.innerHTML.trim()) {
    resultContent.classList.add("hidden");
  } else {
    resultContent.classList.remove("hidden");
  }
}

function clearFeedback() {
  resultError.classList.add("hidden");
  resultError.innerHTML = "";
}

function showContent() {
  setWorkspaceMode("active");
  resultPlaceholder.classList.add("hidden");
  resultError.classList.add("hidden");
  resultContent.classList.remove("hidden");
}

function clearResult() {
  currentSessionId = null;
  currentView = null;
  selectedHistorySessionId = null;
  selectedThreadRootSessionId = null;
  setWorkspaceMode("empty");
  setWorkspaceBusy(false);
  resultPlaceholder.classList.remove("hidden");
  resultContent.classList.add("hidden");
  resultError.classList.add("hidden");
  resultContent.innerHTML = "";
  resultError.innerHTML = "";
  clearActiveSessionMarkers();
  resetThreadContextPanel();
}

function setLoadingState(isLoading, label, triggerButton) {
  isSubmitting = isLoading;

  if (isLoading) {
    setWorkspaceMode("active");
    setWorkspaceBusy(true, formatWorkspaceBusyMessage(label));
    activeLoadingButton = triggerButton instanceof HTMLButtonElement ? triggerButton : null;
    if (activeLoadingButton !== null) {
      activeLoadingButton.dataset.originalLabel = activeLoadingButton.textContent || "";
      activeLoadingButton.textContent = `${label} ...`;
      activeLoadingButton.setAttribute("aria-busy", "true");
    }
  }

  if (!isLoading && activeLoadingButton instanceof HTMLButtonElement) {
    const originalLabel = activeLoadingButton.dataset.originalLabel;
    if (originalLabel) {
      activeLoadingButton.textContent = originalLabel;
    }
    activeLoadingButton.removeAttribute("aria-busy");
    delete activeLoadingButton.dataset.originalLabel;
    activeLoadingButton = null;
  }

  submitButton.disabled = isLoading;
  resetButton.disabled = isLoading;

  if (!isLoading) {
    submitButton.textContent = "分析 / ANALYZE";
    setWorkspaceBusy(false);
  }

  setActionButtonsDisabled(isLoading);
}

function formatWorkspaceBusyMessage(label) {
  const normalizedLabel = String(label || "").toUpperCase();
  if (normalizedLabel.includes("DELETE")) {
    return "Deleting this history thread and attempting to remove its linked Feishu archives.";
  }
  if (normalizedLabel.includes("COMPOSE")) {
    return "Composing a new full plan from the approved refinement. Please keep this workspace open.";
  }
  if (normalizedLabel.includes("REFINE")) {
    return "Generating a follow-up refinement for this session. Please keep this workspace open.";
  }
  if (normalizedLabel.includes("RE-RUN")) {
    return "Re-running the current request with the latest clarifications. Please keep this workspace open.";
  }
  return DEFAULT_WORKSPACE_BUSY_MESSAGE;
}

function setWorkspaceBusy(isBusy, message = DEFAULT_WORKSPACE_BUSY_MESSAGE) {
  if (resultShell instanceof HTMLElement) {
    resultShell.classList.toggle("is-busy", isBusy);
    resultShell.setAttribute("aria-busy", String(isBusy));
  }

  if (workspaceBusy instanceof HTMLElement) {
    workspaceBusy.classList.toggle("hidden", !isBusy);
  }

  if (workspaceBusyText instanceof HTMLElement) {
    workspaceBusyText.textContent = isBusy ? message : DEFAULT_WORKSPACE_BUSY_MESSAGE;
  }
}

function setActionButtonsDisabled(isDisabled) {
  const buttons = document.querySelectorAll("button");
  for (const button of buttons) {
    if (!(button instanceof HTMLButtonElement)) {
      continue;
    }
    if (button === activeLoadingButton) {
      button.disabled = isDisabled;
      continue;
    }
    button.disabled = isDisabled;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}
