"use strict";

const form = document.getElementById("idea-form");
const textarea = document.getElementById("idea-content");
const submitButton = document.getElementById("idea-submit");
const resetButton = document.getElementById("idea-reset");
const historyShell = document.getElementById("history-shell");
const historyRefreshButton = document.getElementById("history-refresh");
const historySessionList = document.getElementById("history-session-list");
const historyThreadContent = document.getElementById("history-thread-content");
const resultPlaceholder = document.getElementById("result-placeholder");
const resultError = document.getElementById("result-error");
const resultContent = document.getElementById("result-content");

let currentSessionId = null;
let currentView = null;
let selectedHistorySessionId = null;
let selectedThreadRootSessionId = null;
let isSubmitting = false;
let activeLoadingButton = null;

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

void initializeHistory();

if (historyRefreshButton instanceof HTMLButtonElement) {
  historyRefreshButton.addEventListener("click", async () => {
    if (isSubmitting) {
      return;
    }
    await loadRecentSessions();
    if (selectedThreadRootSessionId) {
      await loadThreadView(selectedThreadRootSessionId);
    }
  });
}

if (historyShell instanceof HTMLElement) {
  historyShell.addEventListener("click", async (event) => {
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
    }
  });
}

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

async function refreshHistoryAfterMutation(payload) {
  await loadRecentSessions();

  const sessionId = typeof payload.session_id === "string" ? payload.session_id : null;
  const rootSessionId = typeof payload.root_session_id === "string" ? payload.root_session_id : null;

  if (sessionId) {
    selectedHistorySessionId = sessionId;
  }
  if (rootSessionId) {
    selectedThreadRootSessionId = rootSessionId;
    await loadThreadView(rootSessionId);
  }
}

async function loadRecentSessions() {
  if (!(historySessionList instanceof HTMLElement)) {
    return;
  }

  historySessionList.innerHTML = "<p class=\"history-empty\">Loading recent sessions...</p>";

  try {
    const response = await fetch("/api/v1/sessions?limit=12");
    const data = await response.json().catch(() => ({ items: [] }));

    if (!response.ok) {
      historySessionList.innerHTML = "<p class=\"history-empty\">Failed to load recent sessions.</p>";
      return;
    }

    const items = Array.isArray(data.items) ? data.items : [];
    renderHistorySessionList(items);
  } catch (_error) {
    historySessionList.innerHTML = "<p class=\"history-empty\">Failed to load recent sessions.</p>";
  }
}

async function loadThreadView(rootSessionId) {
  if (!(historyThreadContent instanceof HTMLElement) || !rootSessionId) {
    return;
  }

  historyThreadContent.innerHTML = "<p class=\"history-empty\">Loading thread...</p>";

  try {
    const response = await fetch(`/api/v1/threads/${encodeURIComponent(rootSessionId)}`);
    const data = await response.json().catch(() => ({ items: [] }));

    if (!response.ok) {
      historyThreadContent.innerHTML = "<p class=\"history-empty\">Failed to load thread.</p>";
      return;
    }

    selectedThreadRootSessionId = rootSessionId;
    renderThreadView(data);
  } catch (_error) {
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
    historySessionList.innerHTML = "<p class=\"history-empty\">No completed local sessions yet.</p>";
    return;
  }

  historySessionList.innerHTML = `
    <div class="history-list">
      ${items.map((item) => renderHistorySessionItem(item)).join("")}
    </div>
  `;
}

function renderHistorySessionItem(item) {
  const statusMeta = getArchiveStatusMeta(item.archive_status);
  const isActive = item.session_id === selectedHistorySessionId;
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
        <div class="history-item-meta">
          <span class="history-tag ${getHistoryStatusClass(item.archive_status)}">${escapeHtml(statusMeta.badge)}</span>
        </div>
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

function renderThreadView(payload) {
  if (!(historyThreadContent instanceof HTMLElement)) {
    return;
  }

  const items = Array.isArray(payload.items) ? payload.items : [];
  if (!items.length) {
    historyThreadContent.innerHTML = "<p class=\"history-empty\">No sessions found in this thread.</p>";
    return;
  }

  const rootTitle = items[0].archive_title || "Untitled Thread";
  historyThreadContent.innerHTML = `
    <section class="thread-panel-headline">
      <div class="assumptions-label">THREAD ROOT / 根链路</div>
      <h3 class="thread-title">${escapeHtml(rootTitle)}</h3>
      <p class="thread-meta-copy">Root session ${escapeHtml(payload.root_session_id || "")}</p>
    </section>
    <div class="history-list">
      ${items.map((item) => renderThreadItem(item)).join("")}
    </div>
  `;
}

function renderThreadItem(item) {
  const isActive = item.session_id === selectedHistorySessionId;
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
        <div class="history-item-meta">
          <span class="history-tag ${getHistoryStatusClass(item.archive_status)}">${escapeHtml(getArchiveStatusMeta(item.archive_status).badge)}</span>
        </div>
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
    ${renderStatusBar("NEEDS CLARIFICATION")}
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
  const clarificationRecord = renderClarificationRecord(clarifications);
  const followup = renderOpenQuestionSuggestions(payload.open_questions || []);

  resultContent.innerHTML = `
    ${renderStatusBar("ANALYSIS READY")}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    ${clarificationRecord}
    <section class="analysis-shell">
      <div class="analysis-grid">${analysisGrid}</div>
    </section>
    ${followup}
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

function renderFollowUpClarificationView(payload, followUpQuestion) {
  const assumptions = renderListItems(payload.assumptions, "当前没有额外系统假设。");
  const questions = renderQuestionCards(payload.open_questions || []);

  resultContent.innerHTML = `
    ${renderStatusBar("FOLLOW-UP NEEDS CLARIFICATION")}
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
    ${renderStatusBar("REFINEMENT READY")}
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
  const refinementBlock = payload.refinement_result
    ? `
      <section class="followup-block">
        <div class="assumptions-label">COMPOSED FROM / 合成来源</div>
        <p class="analysis-copy">${escapeHtml(payload.refinement_result.refinement_answer || "")}</p>
      </section>
    `
    : "";

  resultContent.innerHTML = `
    ${renderStatusBar("NEW FULL PLAN READY")}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    ${refinementBlock}
    <section class="analysis-shell">
      <div class="analysis-grid">${analysisGrid}</div>
    </section>
    ${renderOpenQuestionSuggestions(payload.open_questions || [])}
    ${renderFollowUpEntry()}
    <div class="result-actions">
      <button class="secondary-button" type="button" data-action="reset">
        重新开始 / RESET
      </button>
    </div>
  `;
  showContent();
}

function renderStatusBar(label) {
  return `
    <div class="result-status-bar">
      <div class="result-status-label">STATUS</div>
      <div class="result-status-value">${escapeHtml(label)}</div>
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
  const statusMeta = ARCHIVE_STATUS_META[archiveStatus] || ARCHIVE_STATUS_META.not_triggered;
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

function renderApiError(data, fallbackMessage) {
  const detail = data && typeof data === "object" ? data.detail : null;
  const message = detail && typeof detail === "object" && "message" in detail
    ? String(detail.message)
    : fallbackMessage;
  renderError(message);
}

function renderError(message) {
  resultError.innerHTML = `
    <div class="section-head">
      <span class="section-index">XX</span>
      <h2 class="section-title">ERROR / 请求失败</h2>
    </div>
    <p class="result-error-copy">${escapeHtml(message)}</p>
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
  resultPlaceholder.classList.add("hidden");
  resultError.classList.add("hidden");
  resultContent.classList.remove("hidden");
}

function clearResult() {
  currentSessionId = null;
  currentView = null;
  selectedHistorySessionId = null;
  resultPlaceholder.classList.remove("hidden");
  resultContent.classList.add("hidden");
  resultError.classList.add("hidden");
  resultContent.innerHTML = "";
  resultError.innerHTML = "";
  if (historyThreadContent instanceof HTMLElement) {
    historyThreadContent.innerHTML = "<p class=\"history-empty\">Select a session to inspect its thread.</p>";
  }
}

function setLoadingState(isLoading, label, triggerButton) {
  isSubmitting = isLoading;

  if (isLoading) {
    activeLoadingButton = triggerButton instanceof HTMLButtonElement ? triggerButton : null;
    if (activeLoadingButton !== null) {
      activeLoadingButton.dataset.originalLabel = activeLoadingButton.textContent || "";
      activeLoadingButton.textContent = `${label} ...`;
    }
  }

  if (!isLoading && activeLoadingButton instanceof HTMLButtonElement) {
    const originalLabel = activeLoadingButton.dataset.originalLabel;
    if (originalLabel) {
      activeLoadingButton.textContent = originalLabel;
    }
    delete activeLoadingButton.dataset.originalLabel;
    activeLoadingButton = null;
  }

  submitButton.disabled = isLoading;
  resetButton.disabled = isLoading;

  if (!isLoading) {
    submitButton.textContent = "分析 / ANALYZE";
  }

  setActionButtonsDisabled(isLoading);
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
