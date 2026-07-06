"use strict";

const form = document.getElementById("idea-form");
const textarea = document.getElementById("idea-content");
const submitButton = document.getElementById("idea-submit");
const resetButton = document.getElementById("idea-reset");
const resultPlaceholder = document.getElementById("result-placeholder");
const resultError = document.getElementById("result-error");
const resultContent = document.getElementById("result-content");
let currentSessionId = null;

const ANALYSIS_FIELDS = [
  ["01", "SUMMARY", "summary", "copy", "analysis-span-12"],
  ["02", "FEASIBILITY", "feasibility", "copy", "analysis-span-12"],
  ["03", "MARKET", "market", "copy", "analysis-span-12"],
  ["04", "KNOWLEDGE GAPS", "knowledge_gaps", "list", "analysis-span-12"],
  ["05", "RESOURCE GAPS", "resource_gaps", "list", "analysis-span-12"],
  ["06", "TEAM REQUIREMENTS", "team_requirements", "list", "analysis-span-12"],
  ["07", "SIMILAR PROJECTS", "similar_projects", "list", "analysis-span-12"],
  ["08", "MVP ROADMAP", "mvp_roadmap", "list", "analysis-span-12"],
  ["09", "LONG-TERM ROADMAP", "long_term_roadmap", "list", "analysis-span-12"],
];
const ARCHIVE_STATUS_META = {
  not_triggered: {
    badge: "NOT TRIGGERED",
    label: "WAITING FOR FINAL ANALYSIS",
    note: "Archive will be created only after this session reaches a completed analysis.",
  },
  pending: {
    badge: "PENDING",
    label: "ARCHIVE IN PROGRESS",
    note: "The analysis is ready and the archive job has been triggered for this session.",
  },
  succeeded: {
    badge: "SUCCEEDED",
    label: "ARCHIVED TO FEISHU",
    note: "This completed session has been archived successfully. You can open the Feishu doc below.",
  },
  failed: {
    badge: "FAILED",
    label: "ARCHIVE FAILED",
    note: "The analysis is ready, but the Feishu archive step failed. The analysis result below is still valid.",
  },
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = textarea.value.trim();
  if (!content) {
    renderError("请输入一段原始想法后再提交。");
    return;
  }

  currentSessionId = null;
  await submitIdea({ content, clarifications: [], session_id: null }, "分析 / ANALYZE");
});

resetButton.addEventListener("click", () => {
  form.reset();
  clearResult();
  textarea.focus();
});

resultContent.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  if (target.matches("[data-action='reset']")) {
    form.reset();
    clearResult();
    textarea.focus();
    return;
  }

  if (!target.matches("[data-action='rerun']")) {
    return;
  }

  const content = target.getAttribute("data-content") || textarea.value.trim();
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
  );
});

async function submitIdea(payload, loadingLabel) {
  setLoadingState(true, loadingLabel);
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
      const detail = data && typeof data === "object" ? data.detail : null;
      const message = detail && typeof detail === "object" && "message" in detail
        ? String(detail.message)
        : "请求失败，请稍后再试。";
      renderError(message);
      return;
    }

    currentSessionId = typeof data.session_id === "string" ? data.session_id : currentSessionId;

    if (data.needs_clarification === true) {
      renderClarificationView(data, payload.content);
      return;
    }

    if (data.needs_clarification === false) {
      renderAnalysisView(data, payload.content, payload.clarifications || []);
      return;
    }

    renderError("返回结果不符合预期契约，未显示伪造内容。");
  } catch (error) {
    renderError(error instanceof Error ? error.message : "网络异常，请稍后重试。");
  } finally {
    setLoadingState(false, "分析 / ANALYZE");
  }
}

function renderClarificationView(payload, rawContent) {
  const assumptions = renderListItems(payload.assumptions);
  const questions = (payload.open_questions || [])
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
        <button class="question-submit" type="button" data-action="rerun" data-content="${escapeHtml(rawContent)}">
          补充并重新分析 / RE-RUN
        </button>
        <button class="secondary-button" type="button" data-action="reset">重新开始 / RESET</button>
      </div>
    </section>
  `;
  showContent();
}

function renderAnalysisView(payload, rawContent, clarifications) {
  const assumptions = renderListItems(payload.assumptions);
  const analysisGrid = ANALYSIS_FIELDS
    .map(([index, title, key, kind, spanClass]) => {
      const value = payload.analysis ? payload.analysis[key] : null;
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

  const clarificationRecord = Array.isArray(clarifications) && clarifications.length
    ? `
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
    `
    : "";

  const followup = Array.isArray(payload.open_questions) && payload.open_questions.length
    ? `
      <section class="followup-block">
        <div class="assumptions-label">CONTINUE SHARPENING / 可继续打磨的问题</div>
        <div class="followup-grid">
          ${payload.open_questions
            .map((question, index) => `
              <div class="followup-item">
                <div class="followup-index">${String(index + 1).padStart(2, "0")}</div>
                <div class="followup-copy">${escapeHtml(question)}</div>
              </div>
            `)
            .join("")}
        </div>
      </section>
    `
    : "";

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
    <div class="result-actions">
      <button class="secondary-button" type="button" data-action="reset" data-content="${escapeHtml(rawContent)}">
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
          <div class="archive-meta-label">ARCHIVE STATUS</div>
          <div class="archive-meta-value">${escapeHtml(statusMeta.label)}</div>
        </article>
        <article class="archive-meta-item">
          <div class="archive-meta-label">ARCHIVE TITLE</div>
          <div class="archive-meta-value">${escapeHtml(archiveTitle)}</div>
        </article>
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

function renderListItems(items) {
  if (!Array.isArray(items) || !items.length) {
    return `<li class="assumptions-item">当前没有额外假设。</li>`;
  }
  return items
    .map((item) => `<li class="assumptions-item">${escapeHtml(String(item))}</li>`)
    .join("");
}

function renderArrayBlock(value) {
  if (!Array.isArray(value) || !value.length) {
    return `<p class="analysis-copy">暂无内容。</p>`;
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
    return `<p class="analysis-copy">暂无内容。</p>`;
  }
  return `<p class="analysis-copy">${escapeHtml(String(value))}</p>`;
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
  resultContent.classList.add("hidden");
  resultError.classList.remove("hidden");
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
  resultPlaceholder.classList.remove("hidden");
  resultContent.classList.add("hidden");
  resultError.classList.add("hidden");
  resultContent.innerHTML = "";
  resultError.innerHTML = "";
}

function setLoadingState(isLoading, label) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? `${label} ...` : "分析 / ANALYZE";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
