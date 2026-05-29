// ===================================================================
// Daily Report System Console — Application
// ===================================================================

const projectSelect = document.getElementById("projectSelect");
const refreshStatusBtn = document.getElementById("refreshStatusBtn");

let projects = [];
let currentStatus = null;
let isRunning = false;
let taskHistory = [];
let lastResult = null;

// ===================================================================
// Sidebar toggle
// ===================================================================

(function () {
  var SIDEBAR_KEY = "drs_sidebar_collapsed";

  function applyState(collapsed) {
    var shell = document.querySelector(".app-shell");
    var toggle = document.getElementById("sidebarToggle");
    if (!shell || !toggle) return;
    if (collapsed) {
      shell.classList.add("sidebar-collapsed");
      toggle.innerHTML = "&#9654;";
      toggle.title = "展开侧边栏";
    } else {
      shell.classList.remove("sidebar-collapsed");
      toggle.innerHTML = "&#9664;";
      toggle.title = "收起侧边栏";
    }
  }

  function restoreSidebar() {
    try {
      var stored = localStorage.getItem(SIDEBAR_KEY);
      applyState(stored === "1");
    } catch (e) {
      applyState(false);
    }
  }

  function toggleSidebar() {
    var shell = document.querySelector(".app-shell");
    if (!shell) return;
    var collapsed = !shell.classList.contains("sidebar-collapsed");
    applyState(collapsed);
    try { localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0"); } catch (e) {}
  }

  // Defer binding until DOM is ready
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("sidebarToggle");
    if (btn) btn.addEventListener("click", toggleSidebar);
    restoreSidebar();
  });

  // Also try to restore immediately if DOM is already interactive
  if (document.readyState !== "loading") {
    var btn = document.getElementById("sidebarToggle");
    if (btn) btn.addEventListener("click", toggleSidebar);
    restoreSidebar();
  }
})();

const stepLabels = {
  fetch_ga4_api: "拉取 GA4 API",
  import_raw_csv: "导入原始 CSV",
  build_mart: "生成 Mart",
  sync_tableau: "同步 Tableau 数据源",
  generate_ai_context: "生成 AI 上下文",
  generate_ai_report: "生成 AI 日报文字",
  run_real_pipeline: "运行真实日报流程",
  check_pdf: "检查 PDF",
  send_email_dry_run: "邮件 Dry-run",
};

// ===================================================================
// Helpers
// ===================================================================

function selectedProject() {
  return projectSelect.value || "default";
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "-";
}

/* Update all elements matching an ID (handles duplicate IDs in the DOM). */
function setTextAll(id, value) {
  document.querySelectorAll('[id="' + id + '"]').forEach(function (el) {
    el.textContent = value ?? "-";
  });
}

async function apiJson(url, options) {
  if (!options) options = {};
  const response = await fetch(url, {
    headers: Object.assign({ "Content-Type": "application/json" }, options.headers || {}),
    method: options.method || "GET",
    body: options.body || undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "HTTP " + response.status);
  }
  return data;
}

function formatTime() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, "0");
  const m = String(now.getMinutes()).padStart(2, "0");
  const s = String(now.getSeconds()).padStart(2, "0");
  return h + ":" + m + ":" + s;
}

// ===================================================================
// Toast notification
// ===================================================================

function showToast(message, ok) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast " + (ok ? "success" : "fail");
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(function () {
    toast.classList.add("fade-out");
  }, 2200);
}

// ===================================================================
// Quick status bar
// ===================================================================

function setQuickStatus(state, label) {
  const el = document.getElementById("quickStatus");
  if (!el) return;
  el.textContent = label;
  el.className = "quick-status " + state;
}

function setRunState(state, label) {
  const el = document.getElementById("runStatus");
  if (!el) return;
  el.className = "ga4-status-badge " + state;
  el.textContent = label;
}

// ===================================================================
// Task history
// ===================================================================

function addTaskEntry(result) {
  taskHistory.unshift({
    time: formatTime(),
    step: result.step,
    label: stepLabels[result.step] || result.step,
    ok: result.ok,
    duration: result.duration_seconds ?? 0,
    returncode: result.returncode ?? "-",
  });
  if (taskHistory.length > 5) taskHistory.length = 5;
  renderTaskTable();
}

function renderTaskTable() {
  var tbody = document.querySelector("#taskTable tbody");
  if (!tbody) return;
  if (!taskHistory.length) {
    tbody.innerHTML =
      '<tr id="taskEmptyRow"><td colspan="5" style="text-align:center;color:var(--muted);padding:24px">暂无任务记录</td></tr>';
    return;
  }
  tbody.innerHTML = taskHistory
    .map(function (t) {
      var badge = t.ok
        ? '<span class="badge-sm ok">成功</span>'
        : '<span class="badge-sm fail">失败</span>';
      return (
        "<tr>" +
        "<td>" + t.time + "</td>" +
        "<td>" + t.label + "</td>" +
        "<td>" + badge + "</td>" +
        "<td>" + t.duration + "s</td>" +
        "<td>" + t.returncode + "</td>" +
        "</tr>"
      );
    })
    .join("");
}

// ===================================================================
// Navigation
// ===================================================================

function navigateTo(pageName) {
  // Hide all page views
  document.querySelectorAll(".page-view").forEach(function (pv) {
    pv.classList.remove("active");
  });
  // Show target
  var target = document.querySelector('.page-view[data-page="' + pageName + '"]');
  if (target) target.classList.add("active");
  // Update sidebar
  document.querySelectorAll(".sidebar-item").forEach(function (item) {
    item.classList.toggle("active", item.getAttribute("data-page") === pageName);
  });
}

// ===================================================================
// Tabs
// ===================================================================

function switchTab(group, tabName) {
  var container = document.querySelector(
    '.page-view.active .tabs[data-tab-group="' + group + '"]'
  );
  if (!container) {
    // Try within the target page-view
    var pageView = document.querySelector('.page-view[data-page="' + group + '"]');
    if (pageView) {
      container = pageView.querySelector('.tabs[data-tab-group="ingestion"]') ||
                  pageView.querySelector('.tabs[data-tab-group="report"]') ||
                  pageView.querySelector('.tabs[data-tab-group="files"]') ||
                  pageView.querySelector('.tabs[data-tab-group="settings"]');
    }
  }
  if (!container) return;

  // Update tab buttons
  container.querySelectorAll(".tab-btn").forEach(function (btn) {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
  });

  // Find the parent page view and update tab panels within it
  var pageView = container.closest(".page-view");
  if (!pageView) pageView = document;
  pageView.querySelectorAll(".tab-panel[data-tab]").forEach(function (panel) {
    panel.classList.toggle("active", panel.getAttribute("data-tab") === tabName);
  });
}

// ===================================================================
// Button state
// ===================================================================

function setButtonsDisabled(disabled) {
  isRunning = disabled;
  document.querySelectorAll("button").forEach(function (btn) {
    btn.disabled = disabled;
  });
}

// ===================================================================
// Output / log handling
// ===================================================================

function setOutput(result) {
  lastResult = result;
  setText("lastCommand", result.command || "-");
  setText("lastReturnCode", String(result.returncode ?? "-"));
  setText("stdoutBox", result.stdout || "-");
  setText("stderrBox", result.stderr || "-");

  if (result.ok) {
    setRunState("ok", "Success · " + (result.duration_seconds ?? 0) + "s");
    setQuickStatus("success", "上一步成功 · " + (result.duration_seconds ?? 0) + "s");
    showToast((stepLabels[result.step] || result.step) + " 成功", true);
  } else {
    setRunState("fail", "Failed · " + (result.duration_seconds ?? 0) + "s");
    setQuickStatus("fail", "上一步失败 · " + (result.duration_seconds ?? 0) + "s");
    showToast((stepLabels[result.step] || result.step) + " 失败", false);
  }

  addTaskEntry(result);

  // Update dashboard summary cards
  if (result.step === "run_real_pipeline") {
    setText("dsPipelineStatus", result.ok ? "成功" : "失败");
    document.getElementById("dsPipelineStatus").className =
      "sc-value " + (result.ok ? "sc-ok" : "sc-fail");
  }
}

// ===================================================================
// Project & status
// ===================================================================

function updateProjectMeta() {
  var project = null;
  for (var i = 0; i < projects.length; i++) {
    if (projects[i].project_id === selectedProject()) {
      project = projects[i];
      break;
    }
  }
  var pn = project ? project.project_name : null;
  if (!pn && currentStatus) pn = currentStatus.project_name;
  setTextAll("projectName", pn || "-");
  setTextAll("projectPath", project ? project.path : "projects/" + selectedProject());

  // Sidebar project card
  setText("sidebarProjectName", pn || "Cube Match");
  setText("sidebarProjectId", selectedProject());
  setText("settingsProjectId", selectedProject());
  var icon = document.getElementById("sidebarProjectIcon");
  if (icon) icon.textContent = (pn || "C").charAt(0).toUpperCase();
}

function updateStatusView(status) {
  currentStatus = status;
  updateProjectMeta();

  // Counts — update all instances
  setTextAll("rawUnityCount", status.counts.raw_unity_csv);
  setTextAll("rawApplovinCount", status.counts.raw_applovin_csv);
  setTextAll("rawGa4Count", status.counts.raw_ga4_csv);
  setTextAll("cleanCount", status.counts.clean_csv);
  setTextAll("martCount", status.counts.mart_csv);
  setTextAll("tableauCount", status.counts.tableau_csv);
  setTextAll("pdfCount", status.counts.pdf);

  // Paths — update all instances
  setTextAll("rawUnityPath", (status.paths.raw_unity || "") + "/");
  setTextAll("rawApplovinPath", (status.paths.raw_applovin || "") + "/");
  setTextAll("rawGa4Path", (status.paths.raw_ga4 || "") + "/");

  // Settings paths page
  setText("settingsRawUnityPath", (status.paths.raw_unity || "") + "/");
  setText("settingsRawApplovinPath", (status.paths.raw_applovin || "") + "/");
  setText("settingsRawGa4Path", (status.paths.raw_ga4 || "") + "/");
  setText("settingsCleanPath", (status.paths.clean || "") + "/");
  setText("settingsMartPath", (status.paths.mart || "") + "/");
  setText("settingsTableauPath", (status.paths.tableau_datasource || "") + "/");
  setText("settingsAiContextPath", (status.paths.ai_context || "") + "/");
  setText("settingsAiDraftPath", (status.paths.ai_draft || "") + "/");
  setText("settingsPdfPath", (status.paths.pdf || "") + "/");
  setText("settingsLogsPath", "projects/" + status.project_id + "/logs/");
  setText("settingsTempPath", "projects/" + status.project_id + "/temp/");

  // Secrets status
  var secEl = document.getElementById("settingsSecretsStatus");
  if (secEl) {
    secEl.textContent = "(check via GA4 config check)";
    secEl.className = "badge-sm warn";
  }

  setTextAll("latestPdf", status.latest_files.latest_pdf || "-");
  setTextAll("latestLog", status.latest_files.latest_log || "-");

  // Dashboard specifically
  setText("dashLatestPdf", status.latest_files.latest_pdf || "-");

  // Update data source status badges
  function badge(elId, count) {
    var el = document.getElementById(elId);
    if (!el) return;
    if (count > 0) { el.textContent = "已接入"; el.className = "badge-sm ok"; }
    else { el.textContent = "无数据"; el.className = "badge-sm warn"; }
  }
  badge("dsUnityStatus", status.counts.raw_unity_csv);
  badge("dsApplovinStatus", status.counts.raw_applovin_csv);
  badge("dsGa4Status2", status.counts.raw_ga4_csv);

  // Data status summary card
  var hasData = status.counts.raw_unity_csv + status.counts.raw_applovin_csv + status.counts.raw_ga4_csv;
  var ds = document.getElementById("dsDataStatus");
  if (ds) {
    ds.textContent = hasData > 0 ? "今日已更新" : "待更新";
    ds.className = "sc-value " + (hasData > 0 ? "sc-ok" : "sc-warn");
  }
}

async function refreshStatus() {
  try {
    var status = await apiJson("/api/project-status?project=" + encodeURIComponent(selectedProject()));
    updateStatusView(status);
    updateGa4DashboardCard();
    setQuickStatus("idle", "就绪");
  } catch (e) {
    setQuickStatus("fail", "刷新失败: " + e.message);
  }
}

async function loadProjects() {
  projects = await apiJson("/api/projects");
  projectSelect.innerHTML = "";

  if (!projects.length) {
    var opt = document.createElement("option");
    opt.value = "default";
    opt.textContent = "default";
    projectSelect.appendChild(opt);
    return;
  }

  for (var i = 0; i < projects.length; i++) {
    var p = projects[i];
    var opt = document.createElement("option");
    opt.value = p.project_id;
    opt.textContent = p.project_id + " · " + (p.project_name || p.project_id);
    projectSelect.appendChild(opt);
  }

  var def = null;
  for (var j = 0; j < projects.length; j++) {
    if (projects[j].project_id === "default") { def = projects[j]; break; }
  }
  projectSelect.value = def ? "default" : projects[0].project_id;
}

// ===================================================================
// Run step
// ===================================================================

async function runStep(step) {
  if (isRunning) return;

  setButtonsDisabled(true);
  setRunState("ok", "运行中...");
  setQuickStatus("running", "运行中: " + (stepLabels[step] || step));
  setText("lastCommand", stepLabels[step] || step);
  setText("lastReturnCode", "-");
  setText("stdoutBox", "Running...");
  setText("stderrBox", "-");

  try {
    var result = await apiJson("/api/run-step", {
      method: "POST",
      body: JSON.stringify({ project: selectedProject(), step: step }),
    });
    setOutput(result);
    await refreshStatus();
  } catch (error) {
    setOutput({
      ok: false,
      step: step,
      command: step,
      returncode: "-",
      stdout: "",
      stderr: error.message,
      duration_seconds: 0,
    });
  } finally {
    setButtonsDisabled(false);
  }
}

// ===================================================================
// File preview
// ===================================================================

async function readFile(type) {
  if (isRunning) return;

  setText("previewMeta", "读取中...");
  setText("filePreview", "");

  try {
    var result = await apiJson(
      "/api/read-file?project=" + encodeURIComponent(selectedProject()) + "&type=" + encodeURIComponent(type)
    );
    if (!result.ok) {
      setText("previewMeta", result.message || "文件暂不存在。");
      setText("filePreview", "文件暂不存在。");
      return;
    }
    setText("previewMeta", result.path + (result.truncated ? " · 已截断预览" : ""));
    setText("filePreview", result.content || "(empty file)");
  } catch (error) {
    setText("previewMeta", "读取失败");
    setText("filePreview", error.message);
  }
}

// ===================================================================
// GA4 Configuration (unchanged from previous version)
// ===================================================================

function setGa4ConfigStatus(ok, text) {
  var el = document.getElementById("ga4ConfigStatus");
  if (!el) return;
  el.textContent = text;
  el.className = "ga4-status-badge " + (ok ? "ok" : "fail");

  // Also update dashboard card
  var ds = document.getElementById("dsGa4Status");
  if (ds) {
    ds.textContent = text;
    ds.className = "sc-value " + (ok ? "sc-ok" : "sc-fail");
  }
}

function setGa4CredsStatus(ok, text) {
  var el = document.getElementById("ga4CredsStatus");
  if (!el) return;
  el.textContent = text;
  el.className = "ga4-status-badge " + (ok ? "ok" : "fail");
}

function setGa4UploadMsg(ok, text) {
  var el = document.getElementById("ga4UploadMsg");
  if (!el) return;
  el.textContent = text;
  el.className = "ga4-hint " + (ok ? "success" : "error");
}

function showGa4CheckMessages(messages) {
  var el = document.getElementById("ga4CheckMessages");
  if (!el) return;
  if (messages && messages.length) {
    el.textContent = messages.join("\n");
    el.className = "ga4-check-messages visible";
  } else {
    el.textContent = "";
    el.className = "ga4-check-messages";
  }
}

function getGa4FormValues() {
  return {
    enabled: document.getElementById("ga4Enabled").checked,
    property_id: document.getElementById("ga4PropertyId").value.trim(),
    credentials_path: document.getElementById("ga4CredentialsPath").value.trim(),
    start_date: document.getElementById("ga4StartDate").value.trim(),
    end_date: document.getElementById("ga4EndDate").value.trim(),
    reports: {
      daily_overview: document.getElementById("ga4ReportDailyOverview").checked,
      country_platform_daily: document.getElementById("ga4ReportCountryPlatform").checked,
      event_daily: document.getElementById("ga4ReportEventDaily").checked,
    },
  };
}

function updateGa4IngestionStatus(config) {
  var g = config.ga4;
  setText("ga4StatusPropertyId", g.property_id || "(未设置)");
  setText("ga4StatusCredentials", g.credentials_path || "(未设置)");
  setText("ga4StatusDateRange", (g.start_date || "-") + " → " + (g.end_date || "-"));
  var reports = [];
  if (g.reports.daily_overview) reports.push("daily_overview");
  if (g.reports.country_platform_daily) reports.push("country_platform_daily");
  if (g.reports.event_daily) reports.push("event_daily");
  setText("ga4StatusReports", reports.length ? reports.join(", ") : "(无)");
}

function fillGa4Form(config) {
  var g = config.ga4;
  var enabledEl = document.getElementById("ga4Enabled");
  if (enabledEl) enabledEl.checked = g.enabled;
  var propIdEl = document.getElementById("ga4PropertyId");
  if (propIdEl) propIdEl.value = g.property_id || "";
  var credPathEl = document.getElementById("ga4CredentialsPath");
  if (credPathEl) credPathEl.value = g.credentials_path || "";
  var startEl = document.getElementById("ga4StartDate");
  if (startEl) startEl.value = g.start_date || "";
  var endEl = document.getElementById("ga4EndDate");
  if (endEl) endEl.value = g.end_date || "";
  var rdoEl = document.getElementById("ga4ReportDailyOverview");
  if (rdoEl) rdoEl.checked = g.reports.daily_overview;
  var rcpEl = document.getElementById("ga4ReportCountryPlatform");
  if (rcpEl) rcpEl.checked = g.reports.country_platform_daily;
  var redEl = document.getElementById("ga4ReportEventDaily");
  if (redEl) redEl.checked = g.reports.event_daily;

  if (config.exists) {
    setGa4ConfigStatus(true, "配置文件存在");
  } else if (g.property_id) {
    setGa4ConfigStatus(true, "已加载");
  } else {
    setGa4ConfigStatus(false, "未配置");
  }

  setGa4CredsStatus(config.credentials_exists,
    config.credentials_exists ? "凭证文件存在" : "凭证文件不存在");

  // Also update read-only GA4 status on Data Ingestion page
  updateGa4IngestionStatus(config);
}

async function updateGa4DashboardCard() {
  try {
    var config = await apiJson("/api/config/ga4");
    var g = config.ga4;
    var ds = document.getElementById("dsGa4Status");
    if (!ds) return;

    if (!g.enabled || !g.property_id) {
      ds.textContent = "未配置";
      ds.className = "sc-value sc-fail";
    } else if (!config.credentials_exists) {
      ds.textContent = "凭证缺失";
      ds.className = "sc-value sc-warn";
    } else {
      ds.textContent = "已就绪";
      ds.className = "sc-value sc-ok";
    }
  } catch (e) {
    // silently ignore
  }
}

async function loadGa4Config() {
  try {
    var config = await apiJson("/api/config/ga4");
    fillGa4Form(config);
    setGa4UploadMsg(true, "配置已加载。");
  } catch (error) {
    setGa4ConfigStatus(false, "加载失败");
    setGa4UploadMsg(false, "加载失败: " + error.message);
  }
}

async function saveGa4Config() {
  var payload = getGa4FormValues();
  try {
    var result = await apiJson("/api/config/ga4", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    fillGa4Form({
      exists: true,
      ga4: result.ga4,
      credentials_exists: result.credentials_exists,
    });
    setGa4UploadMsg(true, "配置已保存到 config/api_sources.yaml。");
    updateGa4DashboardCard();
  } catch (error) {
    setGa4UploadMsg(false, "保存失败: " + error.message);
  }
}

async function uploadGa4Credentials() {
  var fileInput = document.getElementById("ga4CredentialsFile");
  var file = fileInput.files[0];
  if (!file) {
    setGa4UploadMsg(false, "请先选择一个 .json 文件。");
    return;
  }

  var formData = new FormData();
  formData.append("file", file);
  setGa4UploadMsg(true, "上传中...");

  try {
    var response = await fetch("/api/config/ga4/upload-credentials", {
      method: "POST",
      body: formData,
    });
    var data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "HTTP " + response.status);
    }
    document.getElementById("ga4CredentialsPath").value = data.path;
    setGa4CredsStatus(true, "凭证文件存在");
    setGa4UploadMsg(true, "上传成功。");
    fileInput.value = "";
    updateGa4DashboardCard();
  } catch (error) {
    setGa4UploadMsg(false, "上传失败: " + error.message);
  }
}

async function checkGa4Config() {
  showGa4CheckMessages(["检查中..."]);
  try {
    var result = await apiJson("/api/config/ga4/check", { method: "POST" });
    showGa4CheckMessages(result.messages);
    setGa4ConfigStatus(result.ok, result.ok ? "检查通过" : "检查未通过");
  } catch (error) {
    showGa4CheckMessages(["检查失败: " + error.message]);
    setGa4ConfigStatus(false, "检查失败");
  }
}

async function fetchGa4WithSave() {
  if (isRunning) return;

  showGa4CheckMessages(["正在保存配置..."]);
  try {
    var payload = getGa4FormValues();
    var saveResult = await apiJson("/api/config/ga4", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    fillGa4Form({
      exists: true,
      ga4: saveResult.ga4,
      credentials_exists: saveResult.credentials_exists,
    });
    showGa4CheckMessages(["配置已保存。", "正在拉取 GA4 API..."]);
    updateGa4DashboardCard();
  } catch (error) {
    showGa4CheckMessages(["保存配置失败: " + error.message, "请先保存配置再拉取。"]);
    setGa4UploadMsg(false, "保存失败: " + error.message);
    return;
  }

  await runStep("fetch_ga4_api");
}

async function dashFetchGa4() {
  if (isRunning) return;

  // Check GA4 config status before running
  try {
    var config = await apiJson("/api/config/ga4");
    var g = config.ga4;
    if (!g.enabled || !g.property_id) {
      showToast("请先在 项目与配置 > 数据源配置 中完成 GA4 配置", false);
      return;
    }
    if (!config.credentials_exists) {
      showToast("GA4 凭证文件缺失，请在 项目与配置 > 数据源配置 中上传", false);
      return;
    }
  } catch (e) {
    showToast("无法检查 GA4 配置状态", false);
    return;
  }

  await runStep("fetch_ga4_api");
}

// ===================================================================
// Event binding
// ===================================================================

function bindEvents() {
  // Sidebar navigation
  document.querySelectorAll(".sidebar-item").forEach(function (item) {
    item.addEventListener("click", function () {
      navigateTo(item.getAttribute("data-page"));
    });
  });

  // Refresh status
  if (refreshStatusBtn) {
    refreshStatusBtn.addEventListener("click", refreshStatus);
  }
  if (projectSelect) {
    projectSelect.addEventListener("change", refreshStatus);
  }

  // runPipelineBtn (may appear multiple times)
  document.querySelectorAll('[id="runPipelineBtn"]').forEach(function (btn) {
    btn.addEventListener("click", function () { runStep("run_real_pipeline"); });
  });

  // Action buttons (data-step)
  document.querySelectorAll(".action-button[data-step]").forEach(function (btn) {
    btn.addEventListener("click", function () { runStep(btn.dataset.step); });
  });

  // Preview buttons (data-type)
  document.querySelectorAll(".preview-button[data-type]").forEach(function (btn) {
    btn.addEventListener("click", function () { readFile(btn.dataset.type); });
  });

  // Tab buttons
  document.querySelectorAll(".tabs .tab-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var group = btn.closest(".tabs");
      var groupName = group ? group.getAttribute("data-tab-group") : null;
      var tabName = btn.getAttribute("data-tab");
      if (groupName && tabName) switchTab(groupName, tabName);
    });
  });

  // GA4 config buttons (only bind if they exist)
  function bindGa4Btn(id, handler) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("click", handler);
  }
  // Dashboard GA4 fetch (with config check)
  var dashFetchBtn = document.getElementById("dashFetchGa4Btn");
  if (dashFetchBtn) dashFetchBtn.addEventListener("click", dashFetchGa4);

  bindGa4Btn("ga4LoadBtn", loadGa4Config);
  bindGa4Btn("ga4SaveBtn", saveGa4Config);
  bindGa4Btn("ga4CheckBtn", checkGa4Config);
  bindGa4Btn("ga4UploadBtn", uploadGa4Credentials);
  bindGa4Btn("ga4FetchBtn", fetchGa4WithSave);
}

// ===================================================================
// Today label
// ===================================================================

function setTodayLabel() {
  var el = document.getElementById("todayLabel");
  if (!el) return;
  var d = new Date();
  el.textContent =
    "今日 " +
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0");
}

// ===================================================================
// Init
// ===================================================================

async function init() {
  bindEvents();
  setTodayLabel();
  setRunState("unknown", "Idle");
  setQuickStatus("idle", "就绪");

  try {
    await loadProjects();
    await refreshStatus();
    loadGa4Config();
  } catch (error) {
    setQuickStatus("fail", "Init failed");
    setText("stderrBox", error.message);
  }
}

init();
