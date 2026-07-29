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
const loadingDialog = document.getElementById("loading-dialog");
const loadingDialogMessage = document.getElementById("loading-dialog-message");
const loadingDialogMessageSecondary = document.getElementById("loading-dialog-message-secondary");
const loadingDialogElapsed = document.getElementById("loading-dialog-elapsed");
const deleteConfirmDialog = document.getElementById("delete-confirm-dialog");
const deleteConfirmDialogMessage = document.getElementById("delete-confirm-dialog-message");
const deleteConfirmCancelButton = document.getElementById("delete-confirm-cancel");
const deleteConfirmSubmitButton = document.getElementById("delete-confirm-submit");
const archiveRetryDialog = document.getElementById("archive-retry-dialog");
const archiveRetryDialogMessage = document.getElementById("archive-retry-dialog-message");
const archiveRetryCloseButton = document.getElementById("archive-retry-close");
const archiveRetrySubmitButton = document.getElementById("archive-retry-submit");
const requestRetryDialog = document.getElementById("request-retry-dialog");
const requestRetryDialogMessage = document.getElementById("request-retry-dialog-message");
const requestRetryCloseButton = document.getElementById("request-retry-close");
const requestRetrySubmitButton = document.getElementById("request-retry-submit");
const resultPlaceholder = document.getElementById("result-placeholder");
const resultError = document.getElementById("result-error");
const resultContent = document.getElementById("result-content");
const appTooltip = document.getElementById("app-tooltip");
const profileOpenButton = document.getElementById("profile-open");
const profileDialog = document.getElementById("profile-dialog");
const profileForm = document.getElementById("profile-form");
const profileCloseButton = document.getElementById("profile-close");
const profileName = document.getElementById("profile-name");
const profileNameInput = document.getElementById("profile-name-input");
const profileAvatar = document.getElementById("profile-avatar");
const profileAvatarPreview = document.getElementById("profile-avatar-preview");
const profileAvatarInput = document.getElementById("profile-avatar-input");
const profileAvatarResetButton = document.getElementById("profile-avatar-reset");
const profileDialogStatus = document.getElementById("profile-dialog-status");
const runtimeSettingsOpenButton = document.getElementById("runtime-settings-open");
const runtimeSettingsDialog = document.getElementById("runtime-settings-dialog");
const runtimeSettingsCloseButton = document.getElementById("runtime-settings-close");
const runtimeSettingsForm = document.getElementById("runtime-settings-form");
const runtimeSettingsStatus = document.getElementById("runtime-settings-status");
const runtimeLlmHint = document.getElementById("runtime-llm-hint");
const runtimeArchiveHint = document.getElementById("runtime-archive-hint");
const runtimeFakeArchiveAck = document.getElementById("runtime-fake-archive-ack");
const runtimeFakeArchiveAckInput = document.getElementById("runtime-fake-archive-ack-input");
const runtimeLarkGuide = document.getElementById("runtime-lark-guide");
const runtimeLarkGuideCopy = document.getElementById("runtime-lark-guide-copy");
const runtimeLarkRecheckButton = document.getElementById("runtime-lark-recheck");
const runtimeLarkInstallCommand = document.getElementById("runtime-lark-install-command");
const runtimeLarkConfigureButton = document.getElementById("runtime-lark-configure");
const runtimeLarkAuthorizeButton = document.getElementById("runtime-lark-authorize");
const runtimeLarkConfiguration = document.getElementById("runtime-lark-configuration");
const runtimeLarkConfigurationStatus = document.getElementById("runtime-lark-configuration-status");
const runtimeLarkConfigurationQrcode = document.getElementById("runtime-lark-configuration-qrcode");
const runtimeLarkConfigurationLink = document.getElementById("runtime-lark-configuration-link");
const runtimeLarkConfigurationCompleteButton = document.getElementById("runtime-lark-configuration-complete");
const runtimeLarkAuthorization = document.getElementById("runtime-lark-authorization");
const runtimeLarkQrcode = document.getElementById("runtime-lark-qrcode");
const runtimeLarkVerificationLink = document.getElementById("runtime-lark-verification-link");
const runtimeLarkCompleteButton = document.getElementById("runtime-lark-complete");
const csrfToken = document.querySelector('meta[name="thinkor-csrf-token"]')?.getAttribute("content") || "";

let currentSessionId = null;
let currentView = null;
let currentSessionContext = null;
let selectedHistorySessionId = null;
let selectedThreadRootSessionId = null;
let isViewingHistoryDetail = false;
let isSubmitting = false;
let activeLoadingButton = null;
let historyThreadSummaries = [];
let historyScrollIndicatorTimeoutId = null;
let historySearchDebounceTimeoutId = null;
let currentHistorySearchQuery = "";
let loadingStartedAt = null;
let loadingElapsedTimerId = null;
let archiveRetrySessionId = null;
let failedRequestRetry = null;
let pendingDeleteAction = null;
let activeLarkSetupFlowId = null;
let activeLarkConfigurationFlowId = null;
let larkConfigurationPollTimerId = null;
let pendingProfileAvatar = null;

const PROFILE_STORAGE_KEY = "thinkor.local-profile.v1";
const DEFAULT_PROFILE_NAME = "LOCAL WORKSPACE";
const DEFAULT_PROFILE_AVATAR = "/static/assets/logo/user.png";

const expandedHistoryRootIds = new Set();
const historyThreadCache = new Map();
const historyThreadLoadErrors = new Map();
const loadingHistoryRootIds = new Set();

const DEFAULT_WORKSPACE_BUSY_MESSAGE = {
  primary: "正在生成方案",
  secondary: "Generating your plan",
};

const ANALYSIS_FIELDS = [
  ["01", "摘要 / SUMMARY", "summary", "copy", "analysis-span-12"],
  ["02", "可行性 / FEASIBILITY", "feasibility", "copy", "analysis-span-12"],
  ["03", "市场判断 / MARKET", "market", "copy", "analysis-span-12"],
  ["04", "认知缺口 / KNOWLEDGE GAPS", "knowledge_gaps", "list", "analysis-span-12"],
  ["05", "资源缺口 / RESOURCE GAPS", "resource_gaps", "list", "analysis-span-12"],
  ["06", "团队需求 / TEAM REQUIREMENTS", "team_requirements", "list", "analysis-span-12"],
  ["07", "相似项目 / SIMILAR PROJECTS", "similar_projects", "list", "analysis-span-12"],
  ["08", "MVP 路线图 / MVP ROADMAP", "mvp_roadmap", "list", "analysis-span-12"],
  ["09", "长期路线图 / LONG-TERM ROADMAP", "long_term_roadmap", "list", "analysis-span-12"],
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
  simulated: {
    badge: "SIMULATED",
    label: "SIMULATED ARCHIVE",
    note: "Fake Archive is enabled. No Feishu document was created.",
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
    renderError("请输入一段想法后再提交。");
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

initializeProfile();
initializeUi();
void initializeHistory();

if (runtimeSettingsOpenButton instanceof HTMLButtonElement) {
  runtimeSettingsOpenButton.addEventListener("click", () => {
    void openRuntimeSettings();
  });
}

if (runtimeSettingsCloseButton instanceof HTMLButtonElement) {
  runtimeSettingsCloseButton.addEventListener("click", closeRuntimeSettings);
}

if (runtimeSettingsForm instanceof HTMLFormElement) {
  runtimeSettingsForm.addEventListener("change", updateRuntimeAcknowledgement);
  runtimeSettingsForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void applyRuntimeSettings();
  });
}

if (runtimeLarkRecheckButton instanceof HTMLButtonElement) {
  runtimeLarkRecheckButton.addEventListener("click", () => {
    void loadRuntimeCapabilities();
  });
}

if (runtimeLarkAuthorizeButton instanceof HTMLButtonElement) {
  runtimeLarkAuthorizeButton.addEventListener("click", () => {
    void startLarkAuthorization();
  });
}

if (runtimeLarkConfigureButton instanceof HTMLButtonElement) {
  runtimeLarkConfigureButton.addEventListener("click", () => {
    void startLarkConfiguration();
  });
}

if (runtimeLarkConfigurationCompleteButton instanceof HTMLButtonElement) {
  runtimeLarkConfigurationCompleteButton.addEventListener("click", () => {
    activeLarkConfigurationFlowId = null;
    clearLarkConfigurationPoll();
    if (runtimeLarkConfiguration instanceof HTMLElement) {
      runtimeLarkConfiguration.classList.add("hidden");
    }
    void loadRuntimeCapabilities();
  });
}

if (profileOpenButton instanceof HTMLButtonElement) {
  profileOpenButton.addEventListener("click", openProfileDialog);
}

if (profileCloseButton instanceof HTMLButtonElement) {
  profileCloseButton.addEventListener("click", closeProfileDialog);
}

if (profileForm instanceof HTMLFormElement) {
  profileForm.addEventListener("submit", saveProfile);
}

if (profileAvatarInput instanceof HTMLInputElement) {
  profileAvatarInput.addEventListener("change", () => {
    void previewProfileAvatar();
  });
}

if (profileAvatarResetButton instanceof HTMLButtonElement) {
  profileAvatarResetButton.addEventListener("click", () => {
    pendingProfileAvatar = null;
    if (profileAvatarPreview instanceof HTMLImageElement) {
      profileAvatarPreview.src = DEFAULT_PROFILE_AVATAR;
    }
    setProfileDialogStatus("将恢复默认头像，确认保存后生效。");
  });
}

if (runtimeLarkCompleteButton instanceof HTMLButtonElement) {
  runtimeLarkCompleteButton.addEventListener("click", () => {
    void completeLarkAuthorization();
  });
}

if (archiveRetryCloseButton instanceof HTMLButtonElement) {
  archiveRetryCloseButton.addEventListener("click", hideArchiveRetryDialog);
}

if (archiveRetrySubmitButton instanceof HTMLButtonElement) {
  archiveRetrySubmitButton.addEventListener("click", () => {
    void retryFailedArchive();
  });
}

if (requestRetryCloseButton instanceof HTMLButtonElement) {
  requestRetryCloseButton.addEventListener("click", hideRequestRetryDialog);
}

if (requestRetrySubmitButton instanceof HTMLButtonElement) {
  requestRetrySubmitButton.addEventListener("click", () => {
    const retryAction = failedRequestRetry;
    if (typeof retryAction === "function") {
      hideRequestRetryDialog();
      void retryAction();
    }
  });
}

if (deleteConfirmCancelButton instanceof HTMLButtonElement) {
  deleteConfirmCancelButton.addEventListener("click", hideDeleteConfirmation);
}

if (deleteConfirmSubmitButton instanceof HTMLButtonElement) {
  deleteConfirmSubmitButton.addEventListener("click", () => {
    const deleteAction = pendingDeleteAction;
    hideDeleteConfirmation();
    if (typeof deleteAction === "function") {
      void deleteAction();
    }
  });
}

function initializeProfile() {
  const profile = loadStoredProfile();
  applyProfile(profile);
}

function loadStoredProfile() {
  try {
    const rawProfile = window.localStorage.getItem(PROFILE_STORAGE_KEY);
    if (!rawProfile) {
      return {name: DEFAULT_PROFILE_NAME, avatar: null};
    }
    const profile = JSON.parse(rawProfile);
    return {
      name: normalizeProfileName(profile?.name),
      avatar: typeof profile?.avatar === "string" && profile.avatar.startsWith("data:image/")
        ? profile.avatar
        : null,
    };
  } catch (_error) {
    return {name: DEFAULT_PROFILE_NAME, avatar: null};
  }
}

function normalizeProfileName(value) {
  const normalized = String(value || "").trim().replace(/\s+/g, " ");
  return normalized.slice(0, 32) || DEFAULT_PROFILE_NAME;
}

function applyProfile(profile) {
  const name = normalizeProfileName(profile?.name);
  const avatar = profile?.avatar || DEFAULT_PROFILE_AVATAR;
  if (profileName instanceof HTMLElement) {
    profileName.textContent = name;
  }
  if (profileAvatar instanceof HTMLImageElement) {
    profileAvatar.src = avatar;
  }
}

function openProfileDialog() {
  if (!(profileDialog instanceof HTMLElement)) {
    return;
  }
  const profile = loadStoredProfile();
  pendingProfileAvatar = profile.avatar;
  if (profileNameInput instanceof HTMLInputElement) {
    profileNameInput.value = profile.name;
  }
  if (profileAvatarPreview instanceof HTMLImageElement) {
    profileAvatarPreview.src = profile.avatar || DEFAULT_PROFILE_AVATAR;
  }
  if (profileAvatarInput instanceof HTMLInputElement) {
    profileAvatarInput.value = "";
  }
  setProfileDialogStatus("名称和头像仅保存在当前浏览器。");
  profileDialog.classList.remove("hidden");
  profileNameInput?.focus();
}

function closeProfileDialog() {
  if (profileDialog instanceof HTMLElement) {
    profileDialog.classList.add("hidden");
  }
}

async function previewProfileAvatar() {
  if (!(profileAvatarInput instanceof HTMLInputElement)) {
    return;
  }
  const file = profileAvatarInput.files?.[0];
  if (!file) {
    return;
  }
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 1024 * 1024) {
    profileAvatarInput.value = "";
    setProfileDialogStatus("请选择不超过 1 MB 的 PNG、JPG 或 WebP 图片。");
    return;
  }
  try {
    pendingProfileAvatar = await readFileAsDataUrl(file);
    if (profileAvatarPreview instanceof HTMLImageElement) {
      profileAvatarPreview.src = pendingProfileAvatar;
    }
    setProfileDialogStatus("新头像已预览，保存资料后生效。");
  } catch (_error) {
    setProfileDialogStatus("无法读取这张图片，请更换后重试。");
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result || "")), {once: true});
    reader.addEventListener("error", () => reject(reader.error), {once: true});
    reader.readAsDataURL(file);
  });
}

function saveProfile(event) {
  event.preventDefault();
  const profile = {
    name: normalizeProfileName(profileNameInput instanceof HTMLInputElement ? profileNameInput.value : ""),
    avatar: pendingProfileAvatar,
  };
  try {
    window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    applyProfile(profile);
    closeProfileDialog();
  } catch (_error) {
    setProfileDialogStatus("无法保存到当前浏览器，请缩小图片后重试。");
  }
}

function setProfileDialogStatus(message) {
  if (profileDialogStatus instanceof HTMLElement) {
    profileDialogStatus.textContent = message;
  }
}

async function openRuntimeSettings() {
  if (!(runtimeSettingsDialog instanceof HTMLElement)) {
    return;
  }
  runtimeSettingsDialog.classList.remove("hidden");
  await loadRuntimeCapabilities();
}

function closeRuntimeSettings() {
  if (runtimeSettingsDialog instanceof HTMLElement) {
    runtimeSettingsDialog.classList.add("hidden");
  }
}

async function loadRuntimeCapabilities() {
  if (!(runtimeSettingsStatus instanceof HTMLElement)) {
    return;
  }
  runtimeSettingsStatus.textContent = "正在检查本地运行状态...";
  try {
    const response = await fetch("/api/v1/runtime-capabilities");
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error("暂时无法读取本地运行状态。");
    }
    renderRuntimeCapabilities(payload);
  } catch (_error) {
    runtimeSettingsStatus.textContent = "无法读取本地运行状态，请重新检测。";
  }
}

function renderRuntimeCapabilities(payload) {
  const fakeLlm = payload?.use_fake_llm !== false;
  const fakeArchive = payload?.use_fake_archive !== false;
  const llmInput = document.querySelector(`input[name="llm-mode"][value="${fakeLlm ? "fake" : "real"}"]`);
  const archiveInput = document.querySelector(`input[name="archive-mode"][value="${fakeArchive ? "fake" : "real"}"]`);
  if (llmInput instanceof HTMLInputElement) {
    llmInput.checked = true;
  }
  if (archiveInput instanceof HTMLInputElement) {
    archiveInput.checked = true;
  }
  const missingItems = Array.isArray(payload?.llm_missing_items) ? payload.llm_missing_items : [];
  if (runtimeLlmHint instanceof HTMLElement) {
    runtimeLlmHint.textContent = fakeLlm
      ? "当前正在使用模拟 LLM。"
      : missingItems.length
        ? `真实 LLM 需要您自己在本机 .env 中填写：${missingItems.join(", ")}，以保证密钥安全。`
        : "真实 LLM 已配置，您可以尝试体验ThinkOR了。";
  }
  if (runtimeArchiveHint instanceof HTMLElement) {
    runtimeArchiveHint.textContent = fakeArchive
      ? "当前正在使用模拟归档，不会写入飞书。"
      : `真实飞书归档状态：${formatArchiveState(payload?.archive_state)}。`;
  }
  if (runtimeSettingsStatus instanceof HTMLElement) {
    runtimeSettingsStatus.textContent = `当前模式：${fakeLlm ? "模拟" : "真实"} LLM / ${fakeArchive ? "模拟" : "真实"} 归档。`;
  }
  renderLarkGuide(payload?.lark);
  updateRuntimeAcknowledgement();
}

function renderLarkGuide(lark) {
  if (!(runtimeLarkGuide instanceof HTMLElement) || !(runtimeLarkGuideCopy instanceof HTMLElement)) {
    return;
  }
  if (!lark) {
    runtimeLarkGuide.classList.add("hidden");
    return;
  }
  runtimeLarkGuide.classList.remove("hidden");
  const messages = {
    cli_missing: "本机尚未检测到 lark-cli。请在本机终端执行下列安装命令，安装完成后返回此处重新检测。",
    cli_unresponsive: "lark-cli 没有正常响应。请检查本机命令配置后重新检测。",
    cli_unconfigured: "已检测到飞书 CLI，但尚未完成本机应用配置。点击下方按钮后，可在本页继续完成二维码配置。",
    unauthenticated: "飞书 CLI 应用已配置，但所选用户尚未授权。点击下方按钮生成一次性授权二维码。",
    identity_mismatch: "当前 CLI 已授权的身份与 IDEAOS_FEISHU_ARCHIVE_AS 不一致。请更新本机配置后重新检测。",
    authenticated_unverified: "已确认当前飞书用户授权可用，您可以实际使用确认飞书归档效果了。",
  };
  runtimeLarkGuideCopy.textContent = messages[lark.availability] || "请重新检测飞书 CLI 状态。";
  if (runtimeLarkInstallCommand instanceof HTMLElement) {
    runtimeLarkInstallCommand.classList.toggle("hidden", lark.availability !== "cli_missing");
  }
  if (runtimeLarkConfigureButton instanceof HTMLButtonElement) {
    runtimeLarkConfigureButton.classList.toggle("hidden", lark.availability !== "cli_unconfigured");
  }
  if (runtimeLarkAuthorizeButton instanceof HTMLButtonElement) {
    runtimeLarkAuthorizeButton.classList.toggle("hidden", lark.availability !== "unauthenticated");
  }
}

function clearLarkConfigurationPoll() {
  if (larkConfigurationPollTimerId !== null) {
    window.clearTimeout(larkConfigurationPollTimerId);
    larkConfigurationPollTimerId = null;
  }
}

function setLarkExternalLink(link, verificationUrl) {
  if (!(link instanceof HTMLAnchorElement)) {
    return;
  }
  try {
    const url = new URL(String(verificationUrl || ""));
    if (url.protocol !== "https:" || url.username || url.password) {
      throw new TypeError("unsafe URL");
    }
    link.href = url.href;
    link.classList.remove("hidden");
  } catch (_error) {
    link.removeAttribute("href");
    link.classList.add("hidden");
  }
}

async function loadLarkQrCode(flowId, image) {
  if (!(image instanceof HTMLImageElement) || image.dataset.flowId === flowId) {
    return;
  }
  const response = await fetch(
    `/api/v1/lark/setup/${encodeURIComponent(flowId)}/qrcode`,
    {headers: {"X-ThinkOR-CSRF-Token": csrfToken}},
  );
  if (!response.ok) {
    throw new Error("无法加载飞书二维码，请重新开始此步骤。");
  }
  image.src = URL.createObjectURL(await response.blob());
  image.dataset.flowId = flowId;
}

async function startLarkConfiguration() {
  if (!(runtimeSettingsStatus instanceof HTMLElement)) {
    return;
  }
  clearLarkConfigurationPoll();
  runtimeSettingsStatus.textContent = "正在启动飞书 CLI 应用配置...";
  try {
    const response = await fetch("/api/v1/lark/setup/configuration/start", {
      method: "POST",
      headers: {"X-ThinkOR-CSRF-Token": csrfToken},
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || typeof payload.flow_id !== "string") {
      throw new Error(payload?.detail?.message || "无法启动飞书 CLI 应用配置，请重新检测后重试。");
    }
    activeLarkConfigurationFlowId = payload.flow_id;
    if (runtimeLarkConfiguration instanceof HTMLElement) {
      runtimeLarkConfiguration.classList.remove("hidden");
    }
    if (runtimeLarkConfigurationStatus instanceof HTMLElement) {
      runtimeLarkConfigurationStatus.textContent = "正在准备浏览器配置页面...";
    }
    void pollLarkConfiguration();
  } catch (error) {
    runtimeSettingsStatus.textContent = error instanceof Error
      ? error.message
      : "无法启动飞书 CLI 应用配置，请重新检测后重试。";
  }
}

async function pollLarkConfiguration() {
  const flowId = activeLarkConfigurationFlowId;
  if (!flowId || !(runtimeLarkConfigurationStatus instanceof HTMLElement)) {
    return;
  }
  try {
    const response = await fetch(
      `/api/v1/lark/setup/configuration/${encodeURIComponent(flowId)}`,
      {headers: {"X-ThinkOR-CSRF-Token": csrfToken}},
    );
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail?.message || "飞书 CLI 配置流程已失效，请重新开始。");
    }
    if (payload.status === "awaiting_browser" && typeof payload.verification_url === "string") {
      runtimeLarkConfigurationStatus.textContent = "请扫描二维码，或在新窗口中打开配置页面。完成后返回此处重新检测。";
      await loadLarkQrCode(flowId, runtimeLarkConfigurationQrcode);
      setLarkExternalLink(runtimeLarkConfigurationLink, payload.verification_url);
    } else if (payload.status === "completed") {
      clearLarkConfigurationPoll();
      activeLarkConfigurationFlowId = null;
      runtimeLarkConfigurationStatus.textContent = "飞书 CLI 应用配置已完成，正在重新检测...";
      await loadRuntimeCapabilities();
      return;
    } else if (payload.status === "failed") {
      clearLarkConfigurationPoll();
      runtimeLarkConfigurationStatus.textContent = "飞书 CLI 应用配置未完成。请重新开始此步骤，或检查浏览器中的配置页面。";
      return;
    } else {
      runtimeLarkConfigurationStatus.textContent = "正在等待飞书 CLI 准备配置页面...";
    }
    larkConfigurationPollTimerId = window.setTimeout(() => {
      void pollLarkConfiguration();
    }, 1000);
  } catch (error) {
    clearLarkConfigurationPoll();
    runtimeLarkConfigurationStatus.textContent = error instanceof Error
      ? error.message
      : "无法检查飞书 CLI 配置进度，请重试。";
  }
}

async function startLarkAuthorization() {
  if (!(runtimeSettingsStatus instanceof HTMLElement)) {
    return;
  }
  runtimeSettingsStatus.textContent = "正在生成新的飞书授权二维码...";
  try {
    const response = await fetch("/api/v1/lark/setup/start", {
      method: "POST",
      headers: {"X-ThinkOR-CSRF-Token": csrfToken},
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail?.message || "无法发起飞书授权。");
    }
    activeLarkSetupFlowId = payload.flow_id;
    await loadLarkQrCode(payload.flow_id, runtimeLarkQrcode);
    setLarkExternalLink(runtimeLarkVerificationLink, payload.verification_url);
    if (runtimeLarkAuthorization instanceof HTMLElement) {
      runtimeLarkAuthorization.classList.remove("hidden");
    }
    runtimeSettingsStatus.textContent = "请扫描二维码完成授权，再点击“我已授权，检查状态”。二维码将在短时间后失效。";
  } catch (error) {
    runtimeSettingsStatus.textContent = error instanceof Error ? error.message : "无法发起飞书授权。";
  }
}

async function completeLarkAuthorization() {
  if (!activeLarkSetupFlowId || !(runtimeSettingsStatus instanceof HTMLElement)) {
    return;
  }
  runtimeSettingsStatus.textContent = "正在检查飞书授权状态...";
  try {
    const response = await fetch(`/api/v1/lark/setup/${encodeURIComponent(activeLarkSetupFlowId)}/complete`, {
      method: "POST",
      headers: {"X-ThinkOR-CSRF-Token": csrfToken},
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail?.message || "飞书授权未完成。");
    }
    activeLarkSetupFlowId = null;
    if (runtimeLarkAuthorization instanceof HTMLElement) {
      runtimeLarkAuthorization.classList.add("hidden");
    }
    await loadRuntimeCapabilities();
  } catch (error) {
    runtimeSettingsStatus.textContent = error instanceof Error ? error.message : "飞书授权未完成。";
  }
}

function formatArchiveState(state) {
  const archiveStates = {
    available: "可用",
    unavailable: "不可用",
    unconfigured: "未配置",
    cli_missing: "未安装 CLI",
    cli_unresponsive: "CLI 不可用",
    cli_unconfigured: "等待完成 CLI 应用配置",
    unauthenticated: "未授权",
    identity_mismatch: "身份不匹配",
    authenticated_unverified: "已授权，请直接开始使用",
    unknown: "未知",
  };
  return archiveStates[String(state || "unknown")] || "未知";
}

function updateRuntimeAcknowledgement() {
  const llmReal = document.querySelector('input[name="llm-mode"]:checked')?.value === "real";
  const archiveReal = document.querySelector('input[name="archive-mode"]:checked')?.value === "real";
  const requiresAcknowledgement = !llmReal && archiveReal;
  if (runtimeFakeArchiveAck instanceof HTMLElement) {
    runtimeFakeArchiveAck.classList.toggle("hidden", !requiresAcknowledgement);
  }
  if (!requiresAcknowledgement && runtimeFakeArchiveAckInput instanceof HTMLInputElement) {
    runtimeFakeArchiveAckInput.checked = false;
  }
}

async function applyRuntimeSettings() {
  const useFakeLlm = document.querySelector('input[name="llm-mode"]:checked')?.value !== "real";
  const useFakeArchive = document.querySelector('input[name="archive-mode"]:checked')?.value !== "real";
  const acknowledged = runtimeFakeArchiveAckInput instanceof HTMLInputElement && runtimeFakeArchiveAckInput.checked;
  if (useFakeLlm && !useFakeArchive && !acknowledged) {
    if (runtimeSettingsStatus instanceof HTMLElement) {
      runtimeSettingsStatus.textContent = "请先确认模拟 LLM 内容将写入真实飞书，再保存此组合。";
    }
    return;
  }
  try {
    const response = await fetch("/api/v1/local-config/apply", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-ThinkOR-CSRF-Token": csrfToken},
      body: JSON.stringify({
        use_fake_llm: useFakeLlm,
        use_fake_archive: useFakeArchive,
        acknowledge_fake_llm_real_archive: acknowledged,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail?.message || "无法保存本地运行设置。");
    }
    renderRuntimeCapabilities(payload);
    if (runtimeSettingsStatus instanceof HTMLElement) {
      const overrideNote = Array.isArray(payload.process_environment_overrides) && payload.process_environment_overrides.length
        ? ` 已保存至 .env，但当前进程环境变量仍会覆盖：${payload.process_environment_overrides.join(", ")}。`
        : " 已保存并应用于后续请求。";
      const capabilityNote = payload.capabilities_checked === false
        ? " 当前状态暂无法检测，可点击“重新检测飞书”稍后刷新。"
        : "";
      runtimeSettingsStatus.textContent += overrideNote + capabilityNote;
    }
  } catch (error) {
    if (runtimeSettingsStatus instanceof HTMLElement) {
      runtimeSettingsStatus.textContent = error instanceof Error ? error.message : "无法保存本地运行设置。";
    }
  }
}

function initializeUi() {
  setSidebarCollapsed(false);
  setSearchPanelVisible(false);
  setWorkspaceMode("empty");
  initializeHistoryScrollIndicator();
  initializeAppTooltips();

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

  if (sidebarSearchInput instanceof HTMLInputElement) {
    sidebarSearchInput.addEventListener("input", () => {
      if (isSubmitting) {
        return;
      }
      scheduleHistorySearch(sidebarSearchInput.value);
    });

    sidebarSearchInput.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") {
        return;
      }
      if (!sidebarSearchInput.value) {
        return;
      }
      sidebarSearchInput.value = "";
      scheduleHistorySearch("");
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

function initializeAppTooltips() {
  document.addEventListener("pointerover", (event) => {
    const tooltipTarget = getTooltipTarget(event.target);
    if (tooltipTarget !== null) {
      showAppTooltip(tooltipTarget);
    }
  });

  document.addEventListener("pointerout", (event) => {
    const tooltipTarget = getTooltipTarget(event.target);
    const relatedTooltipTarget = getTooltipTarget(event.relatedTarget);
    if (tooltipTarget !== null && tooltipTarget !== relatedTooltipTarget) {
      hideAppTooltip();
    }
  });

  document.addEventListener("focusin", (event) => {
    const tooltipTarget = getTooltipTarget(event.target);
    if (tooltipTarget !== null) {
      showAppTooltip(tooltipTarget);
    }
  });

  document.addEventListener("focusout", (event) => {
    const tooltipTarget = getTooltipTarget(event.target);
    const relatedTooltipTarget = getTooltipTarget(event.relatedTarget);
    if (tooltipTarget !== null && tooltipTarget !== relatedTooltipTarget) {
      hideAppTooltip();
    }
  });

  document.addEventListener("scroll", hideAppTooltip, true);
  window.addEventListener("resize", hideAppTooltip);
}

function getTooltipTarget(target) {
  if (!(target instanceof Element)) {
    return null;
  }
  const tooltipTarget = target.closest("[data-tooltip]");
  if (!(tooltipTarget instanceof HTMLElement) || !tooltipTarget.dataset.tooltip?.trim()) {
    return null;
  }
  return tooltipTarget;
}

function showAppTooltip(target) {
  if (!(appTooltip instanceof HTMLElement)) {
    return;
  }
  const copy = target.dataset.tooltip?.trim();
  if (!copy) {
    return;
  }

  appTooltip.textContent = copy;
  appTooltip.classList.remove("hidden", "is-above");
  appTooltip.classList.toggle("is-menu-tooltip", target.id === "runtime-settings-open");
  appTooltip.setAttribute("aria-hidden", "false");

  const targetBounds = target.getBoundingClientRect();
  const tooltipBounds = appTooltip.getBoundingClientRect();
  const viewportPadding = 12;
  const left = Math.min(
    Math.max(targetBounds.left + (targetBounds.width / 2), viewportPadding + (tooltipBounds.width / 2)),
    window.innerWidth - viewportPadding - (tooltipBounds.width / 2),
  );
  const preferredTop = targetBounds.bottom + 10;
  const shouldShowAbove = preferredTop + tooltipBounds.height > window.innerHeight - viewportPadding;

  appTooltip.style.left = `${left}px`;
  appTooltip.style.top = `${shouldShowAbove ? targetBounds.top - 10 : preferredTop}px`;
  appTooltip.classList.toggle("is-above", shouldShowAbove);
}

function hideAppTooltip() {
  if (appTooltip instanceof HTMLElement) {
    appTooltip.classList.add("hidden");
    appTooltip.classList.remove("is-menu-tooltip");
    appTooltip.setAttribute("aria-hidden", "true");
  }
}

function initializeHistoryScrollIndicator() {
  if (!(historySessionList instanceof HTMLElement)) {
    return;
  }

  historySessionList.addEventListener("scroll", () => {
    historySessionList.classList.add("is-scrolling");
    if (historyScrollIndicatorTimeoutId !== null) {
      window.clearTimeout(historyScrollIndicatorTimeoutId);
    }
    historyScrollIndicatorTimeoutId = window.setTimeout(() => {
      historySessionList.classList.remove("is-scrolling");
      historyScrollIndicatorTimeoutId = null;
    }, 720);
  });
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
  const actionTarget = target.closest("[data-action]");
  if (!(actionTarget instanceof HTMLElement) || !resultContent.contains(actionTarget)) {
    return;
  }
  if (isSubmitting) {
    return;
  }

  if (actionTarget.matches("[data-action='reset']")) {
    form.reset();
    clearResult();
    textarea.focus();
    return;
  }

  if (actionTarget.matches("[data-action='rerun-analysis']")) {
    await handleClarificationRerun(actionTarget);
    return;
  }

  if (actionTarget.matches("[data-action='start-follow-up']")) {
    renderFollowUpComposer();
    return;
  }

  if (actionTarget.matches("[data-action='restore-follow-up-draft']")) {
    const sessionId = actionTarget.getAttribute("data-session-id");
    if (sessionId) {
      await openHistorySession(sessionId);
    }
    return;
  }

  if (actionTarget.matches("[data-action='submit-follow-up']")) {
    await handleFollowUpRefine(actionTarget);
    return;
  }

  if (actionTarget.matches("[data-action='rerun-follow-up']")) {
    await handleFollowUpClarificationRerun(actionTarget);
    return;
  }

  if (actionTarget.matches("[data-action='compose-full-plan']")) {
    await handleComposeFullPlan(actionTarget);
    return;
  }

  if (actionTarget.matches("[data-action='open-archive-retry']")) {
    const sessionId = actionTarget.getAttribute("data-session-id");
    if (sessionId) {
      await openArchiveRetryDialog(sessionId);
    }
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
      renderError("请先回答完全部澄清问题噢。");
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
    "补充并继续生成 / CONTINUE",
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
    renderError("请输入您想继续完善的问题。");
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
    "补充并继续完善 / CONTINUE",
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
      renderRetryableApiError(
        data,
        "生成新版完整方案失败，请稍后重试。",
        () => handleComposeFullPlan(null),
      );
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
    scrollWorkspaceToTop();
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
      renderRetryableApiError(
        data,
        "请求失败，请稍后重试。",
        () => submitIdea(payload, loadingLabel, null),
      );
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
      renderRetryableApiError(
        data,
        "继续完善失败，请稍后重试。",
        () => submitFollowUpRefine(payload, loadingLabel, null),
      );
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

    if (target.matches("[data-action='delete-history-session']")) {
      const sessionId = target.getAttribute("data-session-id");
      if (sessionId) {
        await handleDeleteHistorySession(sessionId, target);
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
  currentSessionContext = extractSessionContext(payload);
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

  const normalizedQuery = normalizeHistorySearchQuery(currentHistorySearchQuery);
  historySessionList.innerHTML = "<p class=\"history-empty\">Loading history...</p>";

  try {
    const requestPath = buildHistoryThreadsRequestPath(24, normalizedQuery);
    const response = await fetch(requestPath);
    const data = await response.json().catch(() => ({ items: [] }));

    if (!response.ok) {
      historyThreadSummaries = [];
      historySessionList.innerHTML = normalizedQuery
        ? "<p class=\"history-empty\">搜索历史失败。 / Failed to search history.</p>"
        : "<p class=\"history-empty\">Failed to load history.</p>";
      return;
    }

    const items = Array.isArray(data.items) ? data.items : [];
    historyThreadSummaries = items;
    renderHistorySessionList(items, normalizedQuery);
  } catch (_error) {
    historyThreadSummaries = [];
    historySessionList.innerHTML = normalizedQuery
      ? "<p class=\"history-empty\">搜索历史失败。 / Failed to search history.</p>"
      : "<p class=\"history-empty\">Failed to load history.</p>";
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
    currentSessionContext = extractSessionContext(data);
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

function renderHistorySessionList(items, query = currentHistorySearchQuery) {
  if (!(historySessionList instanceof HTMLElement)) {
    return;
  }

  if (!Array.isArray(items) || !items.length) {
    historySessionList.innerHTML = normalizeHistorySearchQuery(query)
      ? "<p class=\"history-empty\">未找到匹配的历史想法。 / No matching ideas found.</p>"
      : "<p class=\"history-empty\">请开始进行ThinkOR的第一次分析，想法归档会出现在这里。</p>";
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
  const fullTitle = item.root_archive_title || "Untitled Thread";
  const displayTitle = truncateHistoryCardTitle(fullTitle);

  return `
    <article class="history-folder ${isActive ? "is-active" : ""}">
      <div class="history-folder-head">
        <button
          class="history-folder-toggle"
          type="button"
          data-action="toggle-history-thread"
          data-root-session-id="${escapeHtml(item.root_session_id)}"
          aria-label="${isExpanded ? "收起版本" : "展开版本"}"
          data-tooltip="${isExpanded ? "收起版本 / Collapse versions" : "展开版本 / Expand versions"}"
        >
          ${isExpanded ? "▾" : "▸"}
        </button>
        <div class="history-folder-copy">
          <h3 class="history-item-title" data-tooltip="${escapeHtml(fullTitle)}">${escapeHtml(displayTitle)}</h3>
          <div class="history-folder-meta">
            <span class="history-count-badge">${escapeHtml(versionsLabel)}</span>
            <p class="history-item-copy history-folder-updated">Latest ${escapeHtml(formatDateTime(item.latest_updated_at))}</p>
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
            data-tooltip="打开最新版本 / Open latest version"
          >
            ↗
          </button>
          <button
            class="history-icon-button history-icon-button-danger"
            type="button"
            data-action="delete-history-thread"
            data-root-session-id="${escapeHtml(item.root_session_id)}"
            aria-label="删除这条想法线程"
            data-tooltip="删除这条想法线程并尝试清理关联飞书归档 / Delete thread"
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
  const versionLabel = formatFormalVersionLabel(item, index + 1);
  const relationshipLabel = formatParentFormalVersionLabel(item.parent_formal_version_number);
  const relationshipCopy = relationshipLabel
    ? `<p class="history-item-copy history-version-relationship">${escapeHtml(relationshipLabel)}</p>`
    : "";

  return `
    <article class="history-version-item ${isActive ? "is-active" : ""}">
      <div class="history-version-main">
        <div class="history-version-copy">
          <div class="history-version-headline">
            <div class="history-version-order">${escapeHtml(versionLabel)}</div>
            ${archiveBadge}
          </div>
          ${relationshipCopy}
          <p class="history-item-copy">Updated ${escapeHtml(formatDateTime(item.updated_at))}</p>
        </div>
        <div class="history-version-actions">
          <button
            class="history-icon-button"
            type="button"
            data-action="open-history-session"
            data-session-id="${escapeHtml(item.session_id)}"
            aria-label="打开这个版本"
            data-tooltip="打开这个版本 / Open this version"
          >
            ↗
          </button>
          ${renderHistoryVersionDeleteAction(item)}
        </div>
      </div>
    </article>
  `;
}

function renderHistoryVersionDeleteAction(item) {
  if (!item || item.session_id === item.root_session_id) {
    return "";
  }

  const deleteBlockReason = typeof item.delete_block_reason === "string"
    ? item.delete_block_reason
    : "Only leaf versions can be deleted individually.";

  if (item.can_delete_leaf === true) {
    return `
      <button
        class="history-icon-button history-icon-button-danger"
        type="button"
        data-action="delete-history-session"
        data-session-id="${escapeHtml(item.session_id)}"
        aria-label="删除这个版本"
        data-tooltip="删除这个版本 / Delete version"
      >
        ×
      </button>
    `;
  }

  return `
    <button
      class="history-icon-button history-icon-button-disabled"
      type="button"
      aria-disabled="true"
      tabindex="-1"
      aria-label="${escapeHtml(deleteBlockReason)}"
      data-tooltip="${escapeHtml(deleteBlockReason)}"
    >
      ×
    </button>
  `;
}

async function handleDeleteHistorySession(sessionId, triggerButton) {
  const normalizedSessionId = typeof sessionId === "string" ? sessionId.trim() : "";
  if (!normalizedSessionId) {
    return;
  }

  showDeleteConfirmation(
    "将从本地历史中删除该叶子版本，并清理其关联的本地 follow-up 草稿。此操作无法撤销。",
    () => deleteHistorySession(normalizedSessionId, triggerButton),
  );
}

async function deleteHistorySession(sessionId, triggerButton) {
  setLoadingState(true, "DELETE VERSION", triggerButton);
  clearFeedback();

  try {
    const response = await fetch(`/api/v1/sessions/${encodeURIComponent(normalizedSessionId)}`, {
      method: "DELETE",
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      renderApiError(data, "Failed to delete version.");
      return;
    }

    const rootSessionId = typeof data.root_session_id === "string" ? data.root_session_id : "";
    const parentSessionId = typeof data.parent_session_id === "string"
      ? data.parent_session_id
      : "";
    const deletedSessionIds = Array.isArray(data.deleted_session_ids)
      ? data.deleted_session_ids.filter((item) => typeof item === "string" && item.trim())
      : [];
    const shouldFallbackToParent = shouldFallbackAfterLeafDelete(deletedSessionIds);

    if (rootSessionId) {
      invalidateHistoryThreadState(rootSessionId);
    }
    await loadRecentSessions();

    if (shouldFallbackToParent && parentSessionId) {
      await openHistorySession(parentSessionId);
    } else if (
      rootSessionId
      && (
        selectedThreadRootSessionId === rootSessionId
        || expandedHistoryRootIds.has(rootSessionId)
      )
    ) {
      await loadThreadView(rootSessionId);
    }

    const failures = Array.isArray(data.archive_delete_failures)
      ? data.archive_delete_failures
      : [];
    if (failures.length) {
      window.alert(
        `Local version deleted, but ${failures.length} linked Feishu archive(s) could not be removed.`,
      );
    }
  } catch (_error) {
    renderError("Failed to delete version.");
  } finally {
    setLoadingState(false, "分析 / ANALYZE", triggerButton);
  }
}

async function handleDeleteHistoryThread(rootSessionId, triggerButton) {
  const normalizedRootSessionId = typeof rootSessionId === "string" ? rootSessionId.trim() : "";
  if (!normalizedRootSessionId) {
    return;
  }

  showDeleteConfirmation(
    "将删除这条本地想法链路，并尝试清理关联的飞书文档。此操作无法撤销。",
    () => deleteHistoryThread(normalizedRootSessionId, triggerButton),
  );
}

async function deleteHistoryThread(rootSessionId, triggerButton) {
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

function showDeleteConfirmation(message, deleteAction) {
  if (!(deleteConfirmDialog instanceof HTMLElement)) {
    return;
  }

  pendingDeleteAction = deleteAction;
  if (deleteConfirmDialogMessage instanceof HTMLElement) {
    deleteConfirmDialogMessage.textContent = message;
  }
  deleteConfirmDialog.classList.remove("hidden");
  deleteConfirmSubmitButton?.focus();
}

function hideDeleteConfirmation() {
  pendingDeleteAction = null;
  if (deleteConfirmDialog instanceof HTMLElement) {
    deleteConfirmDialog.classList.add("hidden");
  }
}

function clearDeletedThreadState(rootSessionId) {
  historyThreadSummaries = historyThreadSummaries.filter(
    (item) => item.root_session_id !== rootSessionId,
  );
  expandedHistoryRootIds.delete(rootSessionId);
  invalidateHistoryThreadState(rootSessionId);

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
  const threadContextMeta = buildThreadContextMeta(items, payload.root_session_id || "");
  setThreadContextVisible(true);
  historyThreadContent.innerHTML = `
    <section class="thread-panel-headline">
      <div class="assumptions-label">根链路 / THREAD ROOT</div>
      <h3 class="thread-title">${escapeHtml(rootTitle)}</h3>
      <div class="thread-context-grid">
        <article class="thread-context-stat">
          <div class="archive-meta-label">ROOT VERSION</div>
          <div class="thread-context-value">${escapeHtml(threadContextMeta.rootLabel)}</div>
        </article>
        <article class="thread-context-stat">
          <div class="archive-meta-label">PARENT</div>
          <div class="thread-context-value">${escapeHtml(threadContextMeta.parentLabel)}</div>
        </article>
        <article class="thread-context-stat">
          <div class="archive-meta-label">CURRENT</div>
          <div class="thread-context-value">${escapeHtml(threadContextMeta.currentLabel)}</div>
        </article>
        <article class="thread-context-stat thread-context-stat-wide">
          <div class="archive-meta-label">CURRENT CHAIN</div>
          <div class="thread-context-value">${escapeHtml(threadContextMeta.chainLabel)}</div>
        </article>
      </div>
      <p class="thread-meta-copy">
        Root session ${escapeHtml(payload.root_session_id || "")} (${escapeHtml(String(items.length))})
      </p>
    </section>
    <div class="thread-node-list">
      ${items.map((item) => renderThreadItem(item)).join("")}
    </div>
  `;
}

function renderThreadItem(item) {
  const isActive = item.session_id === selectedHistorySessionId;
  const versionLabel = formatFormalVersionLabel(item);
  const parentVersionLabel = formatParentFormalVersionLabel(item.parent_formal_version_number);
  const relationship = parentVersionLabel
    ? `<span class="thread-node-parent">${escapeHtml(parentVersionLabel)}</span>`
    : "";

  return `
    <button
      class="thread-node-button ${isActive ? "is-active" : ""}"
      type="button"
      data-action="open-history-session"
      data-session-id="${escapeHtml(item.session_id)}"
    >
      <span class="thread-node-version-group">
        <span class="thread-node-version">${escapeHtml(versionLabel)}</span>
        ${relationship}
      </span>
      <span class="thread-node-time">${escapeHtml(formatDateTime(item.updated_at))}</span>
    </button>
  `;
}

function renderHistoryDetail(detail) {
  const sessionKind = typeof detail.session_kind === "string" ? detail.session_kind : "analysis";
  const clarifications = Array.isArray(detail.clarifications) ? detail.clarifications : [];
  currentSessionContext = extractSessionContext(detail);
  isViewingHistoryDetail = true;

  if (sessionKind === "analysis") {
    currentView = {
      kind: "analysis",
      sessionId: detail.session_id,
      rawContent: detail.original_content,
      clarifications,
    };
    renderAnalysisView(detail, detail.original_content, clarifications);
  } else if (sessionKind === "follow_up_refinement") {
    currentView = {
      kind: "follow_up_refinement",
      sessionId: detail.session_id,
      parentSessionId: detail.parent_session_id,
      rawContent: detail.original_content,
      followUpQuestion: detail.follow_up_question || "",
    };
    renderRefinementView(detail);
  } else {
    currentView = {
      kind: "full_plan_composed",
      sessionId: detail.session_id,
      rawContent: detail.original_content,
      clarifications,
    };
    renderComposedPlanView(detail);
  }

  setWorkspaceMode("history-detail");
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
        <h2 class="section-title">关键澄清 / OPEN QUESTIONS</h2>
      </div>
      <div class="questions-grid">${questions}</div>
      <div class="result-actions">
        <button class="question-submit" type="button" data-action="rerun-analysis" data-content="${escapeHtml(rawContent)}">
          补充并继续生成 / CONTINUE
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
    ${renderFollowUpActions()}
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
    existingComposer.scrollIntoView({behavior: "smooth", block: "center"});
    const existingInput = existingComposer.querySelector("[data-follow-up-input]");
    if (existingInput instanceof HTMLTextAreaElement) {
      existingInput.focus({preventScroll: true});
    }
    return;
  }

  const composer = `
    <section class="followup-block" data-follow-up-composer>
      <div class="assumptions-label">继续完善方案 / FOLLOW-UP</div>
      <p class="analysis-copy">
        基于当前这版完整分析，输入你想继续追问、收窄或修改的方向。系统会先返回局部完善结果，
        你再决定是否确认修改并生成新版完整方案。
      </p>
      <textarea
        class="question-input"
        rows="5"
        placeholder="例如：请优先打磨这个方案的核心路径、验证方式或落地边界。"
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
  const composerElement = resultContent.querySelector("[data-follow-up-composer]");
  if (composerElement instanceof HTMLElement) {
    composerElement.scrollIntoView({behavior: "smooth", block: "center"});
    const composerInput = composerElement.querySelector("[data-follow-up-input]");
    if (composerInput instanceof HTMLTextAreaElement) {
      composerInput.focus({preventScroll: true});
    }
  }
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
      <div class="assumptions-label">可恢复草稿 / LOCAL DRAFT</div>
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
      <div class="assumptions-label">继续完善问题 / FOLLOW-UP QUESTION</div>
      <p class="analysis-copy">${escapeHtml(followUpQuestion)}</p>
    </section>
    <section class="questions-shell">
      <div class="section-head section-head-single">
        <h2 class="section-title">继续澄清 / OPEN QUESTIONS</h2>
      </div>
      <div class="questions-grid">${questions}</div>
      <div class="result-actions">
        <button class="question-submit" type="button" data-action="rerun-follow-up">
          补充并继续完善 / CONTINUE
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
        <h2 class="section-title">局部完善结果 / REFINEMENT RESULT</h2>
      </div>
      <div class="analysis-grid">
        <section class="analysis-section analysis-span-12">
          <div class="analysis-heading">
            <div class="analysis-index">01</div>
            <h3 class="analysis-title">问题摘要 / QUESTION SUMMARY</h3>
          </div>
          <p class="analysis-copy">${escapeHtml(refinement.question_summary || "N/A")}</p>
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-heading">
            <div class="analysis-index">02</div>
            <h3 class="analysis-title">局部完善回答 / REFINEMENT ANSWER</h3>
          </div>
          <p class="analysis-copy">${escapeHtml(refinement.refinement_answer || "N/A")}</p>
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-heading">
            <div class="analysis-index">03</div>
            <h3 class="analysis-title">受影响板块 / AFFECTED SECTIONS</h3>
          </div>
          ${renderArrayBlock(affectedSections)}
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-heading">
            <div class="analysis-index">04</div>
            <h3 class="analysis-title">建议修改内容 / PROPOSED SECTION UPDATES</h3>
          </div>
          ${renderSectionUpdates(updates)}
        </section>
        <section class="analysis-section analysis-span-12">
          <div class="analysis-heading">
            <div class="analysis-index">05</div>
            <h3 class="analysis-title">后续动作 / NEXT ACTIONS</h3>
          </div>
          <ul class="analysis-list">${nextActions}</ul>
        </section>
      </div>
    </section>
    <div class="result-actions">
      <button class="question-submit" type="button" data-action="compose-full-plan">
        确认修改并生成新版完整方案
      </button>
      ${renderHomeAction()}
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
        <div class="assumptions-label">合成来源 / COMPOSED FROM</div>
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
    ${renderCompletionNotice(payload)}
    ${renderArchivePanel(payload)}
    ${renderInputEcho(payload.input_echo)}
    ${renderAssumptions(assumptions)}
    ${refinementBlock}
    <section class="analysis-shell">
      <div class="analysis-grid">${analysisGrid}</div>
    </section>
    ${renderOpenQuestionSuggestions(payload.open_questions || [])}
    ${draftRecovery}
    ${renderFollowUpActions()}
  `;
  showContent();
}

function renderHomeAction() {
  const label = isViewingHistoryDetail ? "返回主页" : "重新开始";
  return `
    <button class="secondary-button action-button" type="button" data-action="reset">
      <span class="action-button-icon" aria-hidden="true">⌂</span>
      <span>${label}</span>
    </button>
  `;
}

function renderStatusBar() {
  return "";
}

function renderCompletionNotice(payload) {
  if (!payload || payload.archive_status !== "succeeded") {
    return "";
  }

  return `
    <section class="completion-notice" role="status">
      <span class="completion-notice-icon" aria-hidden="true">✦</span>
      <div>
        <strong>新方案已生成并成功归档</strong>
        <span>New version created and archived to Feishu</span>
      </div>
    </section>
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
  const archiveTitle = typeof payload.archive_title === "string" && payload.archive_title
    ? payload.archive_title
    : "N/A";
  const archiveStatus = typeof payload.archive_status === "string" && payload.archive_status
    ? payload.archive_status
    : "not_triggered";
  const archiveSummary = resolveArchiveSummary(payload, archiveStatus, sessionKind);
  const archiveLink = getTrustedFeishuArchiveUrl(payload.archive_url);
  const rootRow = rootSessionId
    ? `
      <article class="archive-meta-item">
        <div class="archive-meta-label">ROOT SESSION</div>
        <div class="archive-meta-value archive-meta-mono">${escapeHtml(rootSessionId)}</div>
      </article>
    `
    : "";
  const archiveLinkAction = archiveLink
    ? `
      <a
        class="archive-link"
        href="${escapeHtml(archiveLink)}"
        target="_blank"
        rel="noreferrer"
      >
        <span class="action-button-icon" aria-hidden="true">↗</span>
        <span>打开飞书文档</span>
      </a>
    `
    : "";
  const archiveRetryAction = archiveStatus === "failed" && sessionId !== "N/A"
    ? `
      <button
        class="archive-retry-button"
        type="button"
        data-action="open-archive-retry"
        data-session-id="${escapeHtml(sessionId)}"
      >
        <span class="action-button-icon" aria-hidden="true">!</span>
        <span>查看错误并重试</span>
      </button>
    `
    : "";
  const archiveActions = archiveLinkAction || archiveRetryAction
    ? `<div class="archive-actions">${archiveLinkAction}${archiveRetryAction}</div>`
    : "";

  return `
    <section class="archive-panel archive-panel-${escapeHtml(archiveStatus)}">
      <div class="archive-panel-head">
        <div class="assumptions-label">归档状态</div>
        <div class="archive-status-list">
          <div class="archive-badge">${archiveSummary.local}</div>
          ${archiveSummary.archive ? `<div class="archive-badge">${archiveSummary.archive}</div>` : ""}
        </div>
      </div>
      <div class="archive-meta-grid">
        <article class="archive-meta-item">
          <div class="archive-meta-label">SESSION ID</div>
          <div class="archive-meta-value archive-meta-mono">${escapeHtml(sessionId)}</div>
        </article>
        <article class="archive-meta-item">
          <div class="archive-meta-label">ARCHIVE TITLE</div>
          <div class="archive-meta-value">${escapeHtml(archiveTitle)}</div>
        </article>
        ${rootRow}
      </div>
      ${archiveActions}
    </section>
  `;
}

async function openArchiveRetryDialog(sessionId) {
  const normalizedSessionId = typeof sessionId === "string" ? sessionId.trim() : "";
  if (!normalizedSessionId || !(archiveRetryDialog instanceof HTMLElement)) {
    return;
  }

  try {
    const response = await fetch(`/api/v1/sessions/${encodeURIComponent(normalizedSessionId)}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      renderApiError(data, "无法读取当前归档失败信息，请稍后重试。");
      return;
    }
    if (data.archive_status !== "failed") {
      renderError("当前版本的飞书归档不处于失败状态，无法再次尝试。");
      return;
    }

    archiveRetrySessionId = normalizedSessionId;
    if (archiveRetryDialogMessage instanceof HTMLElement) {
      archiveRetryDialogMessage.textContent = typeof data.archive_error === "string"
        ? data.archive_error
        : "飞书归档未完成，请检查登录状态和文档创建权限后再次尝试。";
    }
    archiveRetryDialog.classList.remove("hidden");
    archiveRetrySubmitButton?.focus();
  } catch (_error) {
    renderError("读取归档失败信息时发生网络异常，请稍后重试。");
  }
}

function hideArchiveRetryDialog() {
  archiveRetrySessionId = null;
  if (archiveRetryDialog instanceof HTMLElement) {
    archiveRetryDialog.classList.add("hidden");
  }
}

async function retryFailedArchive() {
  if (!archiveRetrySessionId || !(archiveRetrySubmitButton instanceof HTMLButtonElement)) {
    return;
  }

  const sessionId = archiveRetrySessionId;
  let retrySucceeded = false;
  setLoadingState(true, "重新尝试飞书归档 / RETRY", archiveRetrySubmitButton);

  try {
    const response = await fetch(
      `/api/v1/sessions/${encodeURIComponent(sessionId)}/retry-archive`,
      {method: "POST"},
    );
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (archiveRetryDialogMessage instanceof HTMLElement) {
        const detail = data && typeof data === "object" ? data.detail : null;
        archiveRetryDialogMessage.textContent = detail
          && typeof detail === "object"
          && typeof detail.message === "string"
          ? detail.message
          : "重新尝试飞书归档失败，请稍后重试。";
      }
      return;
    }
    if (data.archive_status !== "succeeded") {
      if (archiveRetryDialogMessage instanceof HTMLElement) {
        archiveRetryDialogMessage.textContent = typeof data.archive_error === "string"
          ? data.archive_error
          : "飞书归档仍未完成，请检查授权后再次尝试。";
      }
      return;
    }
    retrySucceeded = true;
    hideArchiveRetryDialog();
  } catch (_error) {
    if (archiveRetryDialogMessage instanceof HTMLElement) {
      archiveRetryDialogMessage.textContent = "网络异常，未能确认归档重试结果，请刷新历史后确认。";
    }
  } finally {
    setLoadingState(false, "分析 / ANALYZE", archiveRetrySubmitButton);
  }

  if (retrySucceeded) {
    await openHistorySession(sessionId);
  }
}

function resolveArchiveSummary(payload, archiveStatus, sessionKind) {
  if (payload && payload.needs_clarification) {
    return {local: "等待补充信息", archive: ""};
  }

  if (
    sessionKind === "follow_up_refinement"
    && archiveStatus === "not_triggered"
    && payload
    && payload.needs_clarification === false
    && payload.refinement_result
  ) {
    return {local: "本地草稿已保存", archive: ""};
  }

  if (archiveStatus === "succeeded") {
    return {local: "本地已生成", archive: "飞书已归档"};
  }
  if (archiveStatus === "simulated") {
    return {local: "本地已生成", archive: "模拟归档（未写入飞书）"};
  }
  if (archiveStatus === "pending") {
    return {local: "本地已生成", archive: "飞书归档中"};
  }
  if (archiveStatus === "failed") {
    return {local: "本地已生成", archive: "飞书归档失败"};
  }
  return {local: "本地已生成", archive: ""};
}

function renderInputEcho(inputEcho) {
  return `
    <section class="input-echo">
      <div class="assumptions-label">忠实复述 / INPUT ECHO</div>
      <p class="input-echo-text">${escapeHtml(inputEcho)}</p>
    </section>
  `;
}

function renderAssumptions(listHtml) {
  return `
    <section class="assumptions-block">
      <div class="assumptions-label">系统假设 / SYSTEM ASSUMPTIONS</div>
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
          <div class="analysis-heading">
            <div class="analysis-index">${index}</div>
            <h3 class="analysis-title">${title}</h3>
          </div>
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
      <div class="assumptions-label">已补充信息 / CLARIFICATION RECORD</div>
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
      <div class="assumptions-label">可继续打磨的问题 / CONTINUE SHARPENING</div>
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

function renderFollowUpActions() {
  return `
    <div class="result-actions result-actions-bottom">
      <button class="question-submit action-button" type="button" data-action="start-follow-up">
        <span class="action-button-icon" aria-hidden="true">✦</span>
        <span>继续完善方案</span>
      </button>
      ${renderHomeAction()}
    </div>
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
  if (normalized === "simulated") {
    return "history-tag-simulated";
  }
  return "";
}

function getTrustedFeishuArchiveUrl(value) {
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }

  try {
    const parsedUrl = new URL(value);
    const host = parsedUrl.hostname.toLowerCase();
    const isFeishuHost = host === "feishu.cn" || host.endsWith(".feishu.cn");
    const isLarkHost = host === "larksuite.com" || host.endsWith(".larksuite.com");
    if (parsedUrl.protocol !== "https:" || (!isFeishuHost && !isLarkHost)) {
      return null;
    }
    return value.trim();
  } catch (_error) {
    return null;
  }
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

function extractSessionContext(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const sessionId = typeof payload.session_id === "string" ? payload.session_id : "";
  const rootSessionId = typeof payload.root_session_id === "string" ? payload.root_session_id : "";
  if (!sessionId || !rootSessionId) {
    return null;
  }

  return {
    sessionId,
    rootSessionId,
    parentSessionId: typeof payload.parent_session_id === "string"
      ? payload.parent_session_id
      : null,
    sessionKind: typeof payload.session_kind === "string" ? payload.session_kind : "analysis",
    formalVersionNumber: resolvePositiveInteger(payload.formal_version_number),
    parentFormalVersionNumber: resolvePositiveInteger(payload.parent_formal_version_number),
  };
}

function resolvePositiveInteger(value) {
  const number = Number(value);
  if (!Number.isInteger(number) || number <= 0) {
    return null;
  }
  return number;
}

function formatFormalVersionShort(value, fallbackNumber = null) {
  const resolved = resolvePositiveInteger(value) ?? resolvePositiveInteger(fallbackNumber);
  if (resolved === null) {
    return "V??";
  }
  return `V${String(resolved).padStart(2, "0")}`;
}

function formatFormalVersionLabel(item, fallbackNumber = null) {
  const shortLabel = formatFormalVersionShort(item.formal_version_number, fallbackNumber);
  return item.session_id === item.root_session_id ? `${shortLabel} ROOT` : shortLabel;
}

function formatParentFormalVersionLabel(parentFormalVersionNumber) {
  const resolved = resolvePositiveInteger(parentFormalVersionNumber);
  if (resolved === null) {
    return "";
  }
  return `from ${formatFormalVersionShort(resolved)}`;
}

function buildThreadContextMeta(items, rootSessionId) {
  const itemsById = new Map(
    items
      .filter((item) => item && typeof item.session_id === "string")
      .map((item) => [item.session_id, item]),
  );
  const rootItem = itemsById.get(rootSessionId) || items[0] || null;
  const rootLabel = rootItem ? formatFormalVersionLabel(rootItem, 1) : "V01 ROOT";

  return {
    rootLabel,
    parentLabel: formatCurrentParentLabel(currentSessionContext, itemsById),
    currentLabel: formatCurrentSessionLabel(currentSessionContext, itemsById),
    chainLabel: formatCurrentChainLabel(currentSessionContext, itemsById),
  };
}

function formatCurrentSessionLabel(sessionContext, itemsById) {
  if (!sessionContext) {
    return "N/A";
  }
  if (sessionContext.sessionKind === "follow_up_refinement") {
    const parentShort = sessionContext.parentFormalVersionNumber !== null
      ? formatFormalVersionShort(sessionContext.parentFormalVersionNumber)
      : null;
    return parentShort ? `LOCAL DRAFT FROM ${parentShort}` : "LOCAL DRAFT";
  }

  const currentItem = itemsById.get(sessionContext.sessionId);
  if (currentItem) {
    return formatFormalVersionLabel(currentItem);
  }
  if (sessionContext.formalVersionNumber !== null) {
    const shortLabel = formatFormalVersionShort(sessionContext.formalVersionNumber);
    return sessionContext.sessionId === sessionContext.rootSessionId
      ? `${shortLabel} ROOT`
      : shortLabel;
  }
  return "N/A";
}

function formatCurrentParentLabel(sessionContext, itemsById) {
  if (!sessionContext || !sessionContext.parentSessionId) {
    return "N/A";
  }

  const parentItem = itemsById.get(sessionContext.parentSessionId);
  if (parentItem) {
    return formatFormalVersionLabel(parentItem);
  }
  if (sessionContext.parentFormalVersionNumber !== null) {
    return formatFormalVersionShort(sessionContext.parentFormalVersionNumber);
  }
  return "N/A";
}

function formatCurrentChainLabel(sessionContext, itemsById) {
  if (!sessionContext) {
    return "N/A";
  }

  const anchorSessionId = sessionContext.sessionKind === "follow_up_refinement"
    ? sessionContext.parentSessionId
    : sessionContext.sessionId;
  const chainItems = [];
  const visitedSessionIds = new Set();
  let cursorSessionId = anchorSessionId;

  while (
    cursorSessionId
    && itemsById.has(cursorSessionId)
    && !visitedSessionIds.has(cursorSessionId)
  ) {
    visitedSessionIds.add(cursorSessionId);
    const item = itemsById.get(cursorSessionId);
    chainItems.push(item);
    cursorSessionId = item.parent_session_id || null;
  }

  const chainLabels = chainItems.reverse().map((item) => formatFormalVersionLabel(item));
  if (sessionContext.sessionKind === "follow_up_refinement") {
    const parentShort = sessionContext.parentFormalVersionNumber !== null
      ? formatFormalVersionShort(sessionContext.parentFormalVersionNumber)
      : null;
    chainLabels.push(parentShort ? `DRAFT FROM ${parentShort}` : "LOCAL DRAFT");
  }

  if (!chainLabels.length) {
    return formatCurrentSessionLabel(sessionContext, itemsById);
  }
  return chainLabels.join(" -> ");
}

function truncateHistoryCardTitle(title, maxLength = 10) {
  const normalized = typeof title === "string" ? title.trim() : "";
  if (!normalized) {
    return "Untitled Thread";
  }

  const characters = Array.from(normalized);
  if (characters.length <= maxLength) {
    return normalized;
  }

  return `${characters.slice(0, maxLength).join("")}…`;
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

function renderRetryableApiError(data, fallbackMessage, retryAction) {
  const detail = data && typeof data === "object" ? data.detail : null;
  const message = detail && typeof detail === "object" && "message" in detail
    ? String(detail.message)
    : fallbackMessage;
  renderError(message);
  showRequestRetryDialog(message, retryAction);
}

function showRequestRetryDialog(message, retryAction) {
  if (!(requestRetryDialog instanceof HTMLElement)) {
    return;
  }

  failedRequestRetry = retryAction;
  if (requestRetryDialogMessage instanceof HTMLElement) {
    requestRetryDialogMessage.textContent = message;
  }
  requestRetryDialog.classList.remove("hidden");
  requestRetrySubmitButton?.focus();
}

function hideRequestRetryDialog() {
  failedRequestRetry = null;
  if (requestRetryDialog instanceof HTMLElement) {
    requestRetryDialog.classList.add("hidden");
  }
}

function setSidebarCollapsed(isCollapsed) {
  document.body.classList.toggle("page-sidebar-collapsed", isCollapsed);

  if (sidebarToggleButton instanceof HTMLButtonElement) {
    sidebarToggleButton.setAttribute("aria-expanded", String(!isCollapsed));
    sidebarToggleButton.setAttribute("aria-label", isCollapsed ? "展开侧栏" : "收起侧栏");
    sidebarToggleButton.dataset.tooltip = isCollapsed
      ? "展开侧栏 / Expand sidebar"
      : "收起侧栏 / Collapse sidebar";
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
    historySearchToggleButton.setAttribute("aria-label", isVisible ? "关闭历史搜索" : "搜索历史");
    historySearchToggleButton.dataset.tooltip = isVisible
      ? "关闭历史搜索 / Close search"
      : "搜索历史 / Search history";
  }

  if (isVisible && sidebarSearchInput instanceof HTMLInputElement) {
    sidebarSearchInput.focus();
  }
}

function scheduleHistorySearch(query) {
  currentHistorySearchQuery = normalizeHistorySearchQuery(query);
  if (historySearchDebounceTimeoutId !== null) {
    window.clearTimeout(historySearchDebounceTimeoutId);
  }
  historySearchDebounceTimeoutId = window.setTimeout(() => {
    historySearchDebounceTimeoutId = null;
    void loadRecentSessions();
  }, 180);
}

function normalizeHistorySearchQuery(value) {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim();
}

function shouldFallbackAfterLeafDelete(deletedSessionIds) {
  if (!Array.isArray(deletedSessionIds) || !deletedSessionIds.length) {
    return false;
  }

  if (
    currentSessionContext
    && typeof currentSessionContext.sessionId === "string"
    && deletedSessionIds.includes(currentSessionContext.sessionId)
  ) {
    return true;
  }

  return typeof selectedHistorySessionId === "string"
    && deletedSessionIds.includes(selectedHistorySessionId);
}

function invalidateHistoryThreadState(rootSessionId) {
  if (typeof rootSessionId !== "string" || !rootSessionId.trim()) {
    return;
  }

  historyThreadCache.delete(rootSessionId);
  historyThreadLoadErrors.delete(rootSessionId);
  loadingHistoryRootIds.delete(rootSessionId);
}

function buildHistoryThreadsRequestPath(limit = 24, query = currentHistorySearchQuery) {
  const normalizedQuery = normalizeHistorySearchQuery(query);
  if (!normalizedQuery) {
    return `/api/v1/threads?limit=${encodeURIComponent(String(limit))}`;
  }

  const params = new URLSearchParams({
    limit: String(limit),
    q: normalizedQuery,
  });
  return `/api/v1/threads?${params.toString()}`;
}

function setWorkspaceMode(mode) {
  const isHistoryDetail = mode === "history-detail";
  const isActive = mode === "active" || isHistoryDetail;
  document.body.classList.toggle("page-workspace-empty", !isActive);
  document.body.classList.toggle("page-workspace-active", isActive);
  document.body.classList.toggle("page-workspace-history-detail", isHistoryDetail);
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
    ".history-folder.is-active, .history-version-item.is-active, .history-item.is-active, .thread-item.is-active, .thread-node-button.is-active",
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
      <h2 class="section-title">请求失败 / ERROR</h2>
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

function scrollWorkspaceToTop() {
  const scrollBehavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? "auto"
    : "smooth";
  window.scrollTo({top: 0, behavior: scrollBehavior});
}

function clearResult() {
  currentSessionId = null;
  currentView = null;
  currentSessionContext = null;
  selectedHistorySessionId = null;
  selectedThreadRootSessionId = null;
  isViewingHistoryDetail = false;
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
  if (normalizedLabel.includes("DELETE VERSION")) {
    return {primary: "正在删除版本", secondary: "Removing this version"};
  }
  if (normalizedLabel.includes("DELETE THREAD")) {
    return {primary: "正在删除链路", secondary: "Removing this thread"};
  }
  if (normalizedLabel.includes("DELETE")) {
    return {primary: "正在删除本地记录", secondary: "Removing local history"};
  }
  if (normalizedLabel.includes("COMPOSE")) {
    return {primary: "正在生成新方案", secondary: "Creating the new version"};
  }
  if (normalizedLabel.includes("REFINE")) {
    return {primary: "正在完善方案", secondary: "Refining this version"};
  }
  if (normalizedLabel.includes("CONTINUE")) {
    return {primary: "正在继续生成", secondary: "Continuing generation"};
  }
  if (normalizedLabel.includes("RETRY")) {
    return {primary: "正在重试飞书归档", secondary: "Retrying Feishu archive"};
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
    workspaceBusyText.textContent = isBusy ? message.primary : DEFAULT_WORKSPACE_BUSY_MESSAGE.primary;
  }

  setLoadingDialog(isBusy, message);
}

function setLoadingDialog(isLoading, message = DEFAULT_WORKSPACE_BUSY_MESSAGE) {
  if (!(loadingDialog instanceof HTMLElement)) {
    return;
  }

  loadingDialog.classList.toggle("hidden", !isLoading);

  if (loadingDialogMessage instanceof HTMLElement) {
    loadingDialogMessage.textContent = isLoading ? message.primary : DEFAULT_WORKSPACE_BUSY_MESSAGE.primary;
  }

  if (loadingDialogMessageSecondary instanceof HTMLElement) {
    loadingDialogMessageSecondary.textContent = isLoading
      ? message.secondary
      : DEFAULT_WORKSPACE_BUSY_MESSAGE.secondary;
  }

  if (isLoading) {
    loadingStartedAt = Date.now();
    updateLoadingElapsedTime();
    if (loadingElapsedTimerId !== null) {
      window.clearInterval(loadingElapsedTimerId);
    }
    loadingElapsedTimerId = window.setInterval(updateLoadingElapsedTime, 1000);
    return;
  }

  if (loadingElapsedTimerId !== null) {
    window.clearInterval(loadingElapsedTimerId);
    loadingElapsedTimerId = null;
  }
  loadingStartedAt = null;
  if (loadingDialogElapsed instanceof HTMLElement) {
    loadingDialogElapsed.textContent = "00:00";
  }
}

function updateLoadingElapsedTime() {
  if (!(loadingDialogElapsed instanceof HTMLElement) || loadingStartedAt === null) {
    return;
  }

  const elapsedSeconds = Math.floor((Date.now() - loadingStartedAt) / 1000);
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  loadingDialogElapsed.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
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
