// ===================================================================
// Daily Report System Console — Application (v2)
// ===================================================================

const projectSelect = document.getElementById("projectSelect");
const refreshStatusBtn = document.getElementById("refreshStatusBtn");

let projects = [];
let currentStatus = null;
let isRunning = false;
let taskHistory = [];

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

// step -> stepper element id
const stepElement = {
  fetch_ga4_api: "stepIngest",
  import_raw_csv: "stepIngest",
  build_mart: "stepMart",
  sync_tableau: "stepTableau",
  generate_ai_context: "stepAi",
  generate_ai_report: "stepAi",
  check_pdf: "stepDeliver",
  send_email_dry_run: "stepDeliver",
};
const allStepElements = ["stepIngest", "stepMart", "stepTableau", "stepAi", "stepDeliver"];

const KPI_DEFS = [
  { key: "revenue", label: "总收入" },
  { key: "dau", label: "DAU" },
  { key: "new_users", label: "新增用户" },
  { key: "arpdau", label: "ARPDAU" },
  { key: "ecpm", label: "eCPM" },
  { key: "d1_retention", label: "次日留存" },
];

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

  function toggleSidebar() {
    var shell = document.querySelector(".app-shell");
    if (!shell) return;
    var collapsed = !shell.classList.contains("sidebar-collapsed");
    applyState(collapsed);
    try { localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0"); } catch (e) {}
  }

  function restore() {
    var btn = document.getElementById("sidebarToggle");
    if (btn) btn.addEventListener("click", toggleSidebar);
    try { applyState(localStorage.getItem(SIDEBAR_KEY) === "1"); } catch (e) { applyState(false); }
  }

  if (document.readyState !== "loading") restore();
  else document.addEventListener("DOMContentLoaded", restore);
})();

// ===================================================================
// Helpers
// ===================================================================

function selectedProject() {
  return projectSelect.value || "default";
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value == null ? "-" : value;
}

function setBadge(id, state, text) {
  var el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = "badge " + state;
}

async function apiJson(url, options) {
  if (!options) options = {};
  const response = await fetch(url, {
    headers: Object.assign({ "Content-Type": "application/json" }, options.headers || {}),
    method: options.method || "GET",
    body: options.body || undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "HTTP " + response.status);
  return data;
}

function formatTime() {
  const now = new Date();
  return [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}

// ===================================================================
// Toast & status
// ===================================================================

function showToast(message, ok) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast " + (ok ? "success" : "fail");
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(function () { toast.classList.add("fade-out"); }, 2200);
}

function setQuickStatus(state, label) {
  const el = document.getElementById("quickStatus");
  if (el) { el.className = "quick-status " + state; el.textContent = label; }
}

function setRunStatus(state, label) {
  setBadge("runStatus", state, label);
}

// ===================================================================
// Task history
// ===================================================================

function addTaskEntry(result) {
  taskHistory.unshift({
    time: formatTime(),
    label: stepLabels[result.step] || result.step,
    ok: result.ok,
    duration: result.duration_seconds == null ? 0 : result.duration_seconds,
  });
  if (taskHistory.length > 6) taskHistory.length = 6;
  renderTaskList();
}

function renderTaskList() {
  var el = document.getElementById("taskList");
  if (!el) return;
  if (!taskHistory.length) {
    el.innerHTML = '<div class="empty-hint">暂无任务记录</div>';
    return;
  }
  el.innerHTML = taskHistory.map(function (t) {
    var badge = t.ok ? '<span class="badge ok">成功</span>' : '<span class="badge fail">失败</span>';
    return (
      '<div class="task-item">' +
      '<span class="ti-label" title="' + t.label + '">' + t.label + "</span>" +
      '<span class="ti-meta"><span class="ti-time">' + t.time + "</span>" + badge +
      '<span class="ti-time">' + t.duration + "s</span></span></div>"
    );
  }).join("");
}

// ===================================================================
// Stepper state
// ===================================================================

function setStepState(elementId, state) {
  var el = document.getElementById(elementId);
  if (!el) return;
  el.classList.remove("done", "fail");
  var idx = el.querySelector(".step-index");
  var num = el.querySelector(".step-index").getAttribute("data-num");
  if (state === "done") { el.classList.add("done"); idx.textContent = "✓"; }
  else if (state === "fail") { el.classList.add("fail"); idx.textContent = "!"; }
  else if (idx) { idx.textContent = num; }
}

function initStepNumbers() {
  document.querySelectorAll(".step .step-index").forEach(function (el) {
    el.setAttribute("data-num", el.textContent.trim());
  });
}

function markStepFromResult(result) {
  if (result.step === "run_real_pipeline") {
    allStepElements.forEach(function (id) { setStepState(id, result.ok ? "done" : "fail"); });
    return;
  }
  var target = stepElement[result.step];
  if (target) setStepState(target, result.ok ? "done" : "fail");
}

// ===================================================================
// Navigation & tabs
// ===================================================================

function navigateTo(pageName) {
  document.querySelectorAll(".page-view").forEach(function (pv) {
    pv.classList.toggle("active", pv.getAttribute("data-page") === pageName);
  });
  document.querySelectorAll(".sidebar-item").forEach(function (item) {
    item.classList.toggle("active", item.getAttribute("data-page") === pageName);
  });
}

function switchTab(group, tabName) {
  var container = document.querySelector('.tabs[data-tab-group="' + group + '"]');
  if (!container) return;
  container.querySelectorAll(".tab-btn").forEach(function (btn) {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
  });
  var pageView = container.closest(".page-view") || document;
  pageView.querySelectorAll(".tab-panel[data-tab]").forEach(function (panel) {
    panel.classList.toggle("active", panel.getAttribute("data-tab") === tabName);
  });
}

// ===================================================================
// Button state
// ===================================================================

function setButtonsDisabled(disabled) {
  isRunning = disabled;
  document.querySelectorAll("button").forEach(function (btn) { btn.disabled = disabled; });
}

// ===================================================================
// Run step
// ===================================================================

function setOutput(result) {
  setText("lastCommand", result.command || "-");
  setText("lastReturnCode", String(result.returncode == null ? "-" : result.returncode));

  var out = document.getElementById("stdoutBox");
  if (out) { out.textContent = result.stdout || "-"; out.classList.remove("muted"); }
  var err = document.getElementById("stderrBox");
  if (err) { err.textContent = result.stderr || "-"; err.classList.toggle("muted", !result.stderr); }

  var label = stepLabels[result.step] || result.step;
  if (result.ok) {
    setRunStatus("ok", "成功 · " + (result.duration_seconds || 0) + "s");
    setQuickStatus("success", "上一步成功：" + label + " · " + (result.duration_seconds || 0) + "s");
    showToast(label + " 成功", true);
  } else {
    setRunStatus("fail", "失败 · " + (result.duration_seconds || 0) + "s");
    setQuickStatus("fail", "上一步失败：" + label);
    showToast(label + " 失败", false);
  }

  addTaskEntry(result);
  markStepFromResult(result);
}

async function runStep(step) {
  if (isRunning) return;
  setButtonsDisabled(true);
  setRunStatus("running", "运行中…");
  setQuickStatus("running", "运行中：" + (stepLabels[step] || step));
  setText("lastCommand", stepLabels[step] || step);
  setText("lastReturnCode", "-");
  var out = document.getElementById("stdoutBox");
  if (out) { out.textContent = "Running…"; out.classList.remove("muted"); }

  try {
    var result = await apiJson("/api/run-step", {
      method: "POST",
      body: JSON.stringify({ project: selectedProject(), step: step }),
    });
    setOutput(result);
    await refreshStatus();
    await refreshKpis();
  } catch (error) {
    setOutput({ ok: false, step: step, command: step, returncode: "-", stdout: "", stderr: error.message, duration_seconds: 0 });
  } finally {
    setButtonsDisabled(false);
  }
}

// ===================================================================
// File preview
// ===================================================================

async function readFile(type) {
  if (isRunning) return;
  navigateTo("files");
  setText("previewMeta", "读取中…");
  var pv = document.getElementById("filePreview");
  if (pv) { pv.textContent = ""; pv.classList.remove("muted"); }

  try {
    var result = await apiJson(
      "/api/read-file?project=" + encodeURIComponent(selectedProject()) + "&type=" + encodeURIComponent(type)
    );
    if (!result.ok) {
      setText("previewMeta", result.message || "文件暂不存在。");
      if (pv) { pv.textContent = "文件暂不存在。"; pv.classList.add("muted"); }
      return;
    }
    setText("previewMeta", result.path + (result.truncated ? " · 已截断预览" : ""));
    if (pv) pv.textContent = result.content || "(空文件)";
  } catch (error) {
    setText("previewMeta", "读取失败");
    if (pv) pv.textContent = error.message;
  }
}

// ===================================================================
// KPI cards
// ===================================================================

function formatKpi(key, value) {
  if (value == null) return "-";
  switch (key) {
    case "revenue":
    case "ecpm":
      return "$" + Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    case "arpdau":
      return "$" + Number(value).toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
    case "dau":
    case "new_users":
      return Math.round(Number(value)).toLocaleString("en-US");
    case "d1_retention":
      return (Number(value) * 100).toFixed(1) + "%";
    default:
      return String(value);
  }
}

function renderKpiCards(metrics) {
  var grid = document.getElementById("kpiGrid");
  if (!grid) return;
  grid.innerHTML = metrics.map(function (m) {
    var deltaHtml = "";
    if (m.delta_pct == null) {
      deltaHtml = '<span class="kpi-delta flat">— 无环比</span>';
    } else if (m.delta_pct > 0) {
      deltaHtml = '<span class="kpi-delta up">▲ ' + m.delta_pct.toFixed(1) + "%</span>";
    } else if (m.delta_pct < 0) {
      deltaHtml = '<span class="kpi-delta down">▼ ' + Math.abs(m.delta_pct).toFixed(1) + "%</span>";
    } else {
      deltaHtml = '<span class="kpi-delta flat">– 0.0%</span>';
    }
    return (
      '<div class="kpi-card">' +
      '<span class="kpi-label">' + m.label + "</span>" +
      '<span class="kpi-value">' + (m.value == null ? "-" : formatKpi(m.key, m.value)) + "</span>" +
      deltaHtml + "</div>"
    );
  }).join("");
}

function renderKpiEmpty(message) {
  var grid = document.getElementById("kpiGrid");
  if (!grid) return;
  grid.innerHTML = KPI_DEFS.map(function (d, i) {
    var note = i === 0 ? '<span class="kpi-delta flat">' + (message || "暂无数据") + "</span>" : '<span class="kpi-delta flat">—</span>';
    return (
      '<div class="kpi-card empty">' +
      '<span class="kpi-label">' + d.label + "</span>" +
      '<span class="kpi-value">—</span>' + note + "</div>"
    );
  }).join("");
}

async function refreshKpis() {
  try {
    var data = await apiJson("/api/kpi?project=" + encodeURIComponent(selectedProject()));
    if (data.ok && data.metrics && data.metrics.length) renderKpiCards(data.metrics);
    else renderKpiEmpty("运行流程后生成");
  } catch (e) {
    renderKpiEmpty("加载失败");
  }
}

// ===================================================================
// Project & status
// ===================================================================

function updateProjectMeta() {
  var project = null;
  for (var i = 0; i < projects.length; i++) {
    if (projects[i].project_id === selectedProject()) { project = projects[i]; break; }
  }
  var pn = project ? project.project_name : null;
  if (!pn && currentStatus) pn = currentStatus.project_name;

  setText("settingsProjectName", pn || "-");
  setText("settingsProjectPath", project ? project.path : "projects/" + selectedProject());
  setText("settingsProjectId", selectedProject());

  setText("sidebarProjectName", pn || "未命名项目");
  setText("sidebarProjectId", selectedProject());
  var icon = document.getElementById("sidebarProjectIcon");
  if (icon) icon.textContent = (pn || "?").charAt(0).toUpperCase();
}

function dsBadge(id, count) {
  if (count > 0) setBadge(id, "ok", "已接入");
  else setBadge(id, "warn", "无数据");
}

function updateStatusView(status) {
  currentStatus = status;
  updateProjectMeta();

  var c = status.counts;
  // Overview datasource
  setText("dsUnityCount", c.raw_unity_csv);
  setText("dsApplovinCount", c.raw_applovin_csv);
  setText("dsGa4Count", c.raw_ga4_csv);
  dsBadge("dsUnityBadge", c.raw_unity_csv);
  dsBadge("dsApplovinBadge", c.raw_applovin_csv);
  dsBadge("dsGa4Badge", c.raw_ga4_csv);

  // Pipeline inline counts
  setText("pipeRawUnity", c.raw_unity_csv);
  setText("pipeRawApplovin", c.raw_applovin_csv);
  setText("pipeRawGa4", c.raw_ga4_csv);
  setText("pipeMartCount", c.mart_csv);
  setText("pipeTableauCount", c.tableau_csv);

  // Files page counts
  setText("filesRawUnity", c.raw_unity_csv);
  setText("filesRawApplovin", c.raw_applovin_csv);
  setText("filesRawGa4", c.raw_ga4_csv);
  setText("filesMart", c.mart_csv);
  setText("filesTableau", c.tableau_csv);
  setText("filesPdf", c.pdf);
  setText("ovPdfCount", c.pdf);

  // Paths — files page
  setText("filesRawUnityPath", (status.paths.raw_unity || "") + "/");
  setText("filesRawApplovinPath", (status.paths.raw_applovin || "") + "/");
  setText("filesRawGa4Path", (status.paths.raw_ga4 || "") + "/");

  // Paths — settings page
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

  // Latest files
  setText("ovLatestPdf", status.latest_files.latest_pdf || "-");
  setText("filesLatestPdf", status.latest_files.latest_pdf || "-");
  setText("filesLatestLog", status.latest_files.latest_log || "-");
}

async function refreshStatus() {
  try {
    var status = await apiJson("/api/project-status?project=" + encodeURIComponent(selectedProject()));
    updateStatusView(status);
    updateGa4PipelineStatus();
    setQuickStatus("idle", "就绪");
  } catch (e) {
    setQuickStatus("fail", "刷新失败：" + e.message);
  }
}

async function loadProjects() {
  projects = await apiJson("/api/projects");
  projectSelect.innerHTML = "";

  if (!projects.length) {
    var opt = document.createElement("option");
    opt.value = "default"; opt.textContent = "default";
    projectSelect.appendChild(opt);
    return;
  }
  for (var i = 0; i < projects.length; i++) {
    var p = projects[i];
    var o = document.createElement("option");
    o.value = p.project_id;
    o.textContent = p.project_id + " · " + (p.project_name || p.project_id);
    projectSelect.appendChild(o);
  }
  var hasDefault = projects.some(function (p) { return p.project_id === "default"; });
  projectSelect.value = hasDefault ? "default" : projects[0].project_id;
}

// ===================================================================
// GA4 configuration
// ===================================================================

function setGa4ConfigStatus(ok, text) { setBadge("ga4ConfigStatus", ok ? "ok" : "fail", text); }
function setGa4CredsStatus(ok, text) { setBadge("ga4CredsStatus", ok ? "ok" : "fail", text); }

function setGa4UploadMsg(ok, text) {
  var el = document.getElementById("ga4UploadMsg");
  if (!el) return;
  el.textContent = text;
  el.className = "ga4-hint " + (ok ? "success" : "error");
}

function showGa4CheckMessages(messages) {
  var el = document.getElementById("ga4CheckMessages");
  if (!el) return;
  if (messages && messages.length) { el.textContent = messages.join("\n"); el.className = "ga4-check-messages visible"; }
  else { el.textContent = ""; el.className = "ga4-check-messages"; }
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

function fillGa4Form(config) {
  var g = config.ga4;
  document.getElementById("ga4Enabled").checked = g.enabled;
  document.getElementById("ga4PropertyId").value = g.property_id || "";
  document.getElementById("ga4CredentialsPath").value = g.credentials_path || "";
  document.getElementById("ga4StartDate").value = g.start_date || "";
  document.getElementById("ga4EndDate").value = g.end_date || "";
  document.getElementById("ga4ReportDailyOverview").checked = g.reports.daily_overview;
  document.getElementById("ga4ReportCountryPlatform").checked = g.reports.country_platform_daily;
  document.getElementById("ga4ReportEventDaily").checked = g.reports.event_daily;

  if (config.exists) setGa4ConfigStatus(true, "配置文件存在");
  else if (g.property_id) setGa4ConfigStatus(true, "已加载");
  else setGa4ConfigStatus(false, "未配置");

  setGa4CredsStatus(config.credentials_exists, config.credentials_exists ? "凭证文件存在" : "凭证文件不存在");
}

async function updateGa4PipelineStatus() {
  try {
    var config = await apiJson("/api/config/ga4?project=" + encodeURIComponent(selectedProject()));
    var g = config.ga4;
    if (!g.enabled || !g.property_id) setBadge("pipeGa4Status", "fail", "未配置");
    else if (!config.credentials_exists) setBadge("pipeGa4Status", "warn", "凭证缺失");
    else setBadge("pipeGa4Status", "ok", "已就绪");
  } catch (e) { /* ignore */ }
}

async function loadGa4Config() {
  try {
    var config = await apiJson("/api/config/ga4?project=" + encodeURIComponent(selectedProject()));
    fillGa4Form(config);
    updateGa4PipelineStatus();
  } catch (error) {
    setGa4ConfigStatus(false, "加载失败");
    setGa4UploadMsg(false, "加载失败：" + error.message);
  }
}

async function saveGa4Config() {
  try {
    var result = await apiJson("/api/config/ga4?project=" + encodeURIComponent(selectedProject()), {
      method: "POST", body: JSON.stringify(getGa4FormValues()),
    });
    fillGa4Form({ exists: true, ga4: result.ga4, credentials_exists: result.credentials_exists });
    setGa4UploadMsg(true, "配置已保存到 config/api_sources.yaml。");
    updateGa4PipelineStatus();
  } catch (error) {
    setGa4UploadMsg(false, "保存失败：" + error.message);
  }
}

async function uploadGa4Credentials() {
  var fileInput = document.getElementById("ga4CredentialsFile");
  var file = fileInput.files[0];
  if (!file) { setGa4UploadMsg(false, "请先选择一个 .json 文件。"); return; }

  var formData = new FormData();
  formData.append("file", file);
  setGa4UploadMsg(true, "上传中…");
  try {
    var response = await fetch("/api/config/ga4/upload-credentials?project=" + encodeURIComponent(selectedProject()), {
      method: "POST", body: formData,
    });
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || "HTTP " + response.status);
    document.getElementById("ga4CredentialsPath").value = data.path;
    setGa4CredsStatus(true, "凭证文件存在");
    setGa4UploadMsg(true, "上传成功。");
    fileInput.value = "";
    updateGa4PipelineStatus();
  } catch (error) {
    setGa4UploadMsg(false, "上传失败：" + error.message);
  }
}

async function checkGa4Config() {
  showGa4CheckMessages(["检查中…"]);
  try {
    var result = await apiJson("/api/config/ga4/check?project=" + encodeURIComponent(selectedProject()), { method: "POST" });
    showGa4CheckMessages(result.messages);
    setGa4ConfigStatus(result.ok, result.ok ? "检查通过" : "检查未通过");
  } catch (error) {
    showGa4CheckMessages(["检查失败：" + error.message]);
    setGa4ConfigStatus(false, "检查失败");
  }
}

async function fetchGa4WithSave() {
  if (isRunning) return;
  try {
    await apiJson("/api/config/ga4?project=" + encodeURIComponent(selectedProject()), {
      method: "POST", body: JSON.stringify(getGa4FormValues()),
    });
    updateGa4PipelineStatus();
  } catch (error) {
    showToast("保存 GA4 配置失败，请先在设置中配置", false);
    return;
  }
  await runStep("fetch_ga4_api");
}

// ===================================================================
// Event binding
// ===================================================================

function bindEvents() {
  document.querySelectorAll(".sidebar-item").forEach(function (item) {
    item.addEventListener("click", function () { navigateTo(item.getAttribute("data-page")); });
  });

  if (refreshStatusBtn) refreshStatusBtn.addEventListener("click", function () { refreshStatus(); refreshKpis(); });
  if (projectSelect) projectSelect.addEventListener("change", function () { refreshStatus(); refreshKpis(); loadGa4Config(); });

  document.querySelectorAll(".runPipelineBtn").forEach(function (btn) {
    btn.addEventListener("click", function () { runStep("run_real_pipeline"); });
  });

  document.querySelectorAll(".action-button[data-step]").forEach(function (btn) {
    btn.addEventListener("click", function () { runStep(btn.dataset.step); });
  });

  document.querySelectorAll(".preview-button[data-type]").forEach(function (btn) {
    btn.addEventListener("click", function () { readFile(btn.dataset.type); });
  });

  document.querySelectorAll("[data-goto-ga4]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      navigateTo("settings");
      setTimeout(function () { switchTab("settings", "ga4-config"); }, 50);
    });
  });

  document.querySelectorAll(".tabs .tab-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var group = btn.closest(".tabs");
      var groupName = group ? group.getAttribute("data-tab-group") : null;
      if (groupName) switchTab(groupName, btn.getAttribute("data-tab"));
    });
  });

  function bind(id, handler) { var el = document.getElementById(id); if (el) el.addEventListener("click", handler); }
  bind("ga4LoadBtn", loadGa4Config);
  bind("ga4SaveBtn", saveGa4Config);
  bind("ga4CheckBtn", checkGa4Config);
  bind("ga4UploadBtn", uploadGa4Credentials);
  bind("ga4FetchBtn", fetchGa4WithSave);
}

// ===================================================================
// Today label
// ===================================================================

function setTodayLabel() {
  var el = document.getElementById("todayLabel");
  if (!el) return;
  var d = new Date();
  el.textContent = "今日 " + d.getFullYear() + "-" +
    String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

// ===================================================================
// Init
// ===================================================================

async function init() {
  initStepNumbers();
  bindEvents();
  setTodayLabel();
  setRunStatus("idle", "空闲");
  setQuickStatus("idle", "就绪");
  renderKpiEmpty("加载中…");
  renderTaskList();

  try {
    await loadProjects();
    await refreshStatus();
    await refreshKpis();
    loadGa4Config();
  } catch (error) {
    setQuickStatus("fail", "初始化失败");
    var err = document.getElementById("stderrBox");
    if (err) err.textContent = error.message;
  }
}

init();
