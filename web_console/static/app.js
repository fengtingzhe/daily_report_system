// ===================================================================
// Daily Report System Console — Application (v2)
// ===================================================================

const projectSelect = document.getElementById("projectSelect");
const refreshStatusBtn = document.getElementById("refreshStatusBtn");

let projects = [];
let currentStatus = null;
let isRunning = false;
let taskHistory = [];

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

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
  { key: "payment_rate", label: "付费率" },
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
  setBadge("runStatusInline", state, label);
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
  el.classList.remove("done", "fail", "running");
  var idx = el.querySelector(".step-index");
  var num = idx ? idx.getAttribute("data-num") : "";
  if (state === "done") { el.classList.add("done"); if (idx) idx.textContent = "✓"; }
  else if (state === "fail") { el.classList.add("fail"); if (idx) idx.textContent = "!"; }
  else if (state === "running") { el.classList.add("running"); if (idx) idx.textContent = "…"; }
  else if (idx) { idx.textContent = num; }
}

function setStepRunning(step) {
  if (step === "run_real_pipeline") {
    allStepElements.forEach(function (id) { setStepState(id, "running"); });
    return;
  }
  var target = stepElement[step];
  if (target) setStepState(target, "running");
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
  if (pageName === "settings" && !settingsLoaded) {
    settingsLoaded = true;
    loadAllSettings();
  }
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

function appendLog(line) {
  var out = document.getElementById("stdoutBox");
  if (!out) return;
  out.textContent += (out.textContent ? "\n" : "") + line;
  out.scrollTop = out.scrollHeight;
}

function finalizeRun(result) {
  setButtonsDisabled(false);
  setText("lastReturnCode", String(result.returncode == null ? "-" : result.returncode));
  var label = stepLabels[result.step] || result.step;
  var secs = result.duration_seconds == null ? 0 : result.duration_seconds;

  if (result.ok) {
    setRunStatus("ok", "成功 · " + secs + "s");
    setQuickStatus("success", "上一步成功：" + label + " · " + secs + "s");
    showToast(label + " 成功", true);
  } else {
    setRunStatus("fail", "失败 · " + secs + "s");
    setQuickStatus("fail", "上一步失败：" + label);
    showToast(label + " 失败", false);
  }

  addTaskEntry({ step: result.step, ok: result.ok, duration_seconds: secs });
  markStepFromResult(result);
  refreshStatus();
  refreshKpis();
}

// Live streaming run via Server-Sent Events.
function runStep(step) {
  if (isRunning) return;
  setButtonsDisabled(true);
  setRunStatus("running", "运行中…");
  setQuickStatus("running", "运行中：" + (stepLabels[step] || step));
  setStepRunning(step);
  setText("lastCommand", stepLabels[step] || step);
  setText("lastReturnCode", "-");

  var out = document.getElementById("stdoutBox");
  if (out) { out.textContent = ""; out.classList.remove("muted"); }

  var url = "/api/run-stream?project=" + encodeURIComponent(selectedProject()) +
    "&step=" + encodeURIComponent(step);
  var es = new EventSource(url);
  es._done = false;

  es.addEventListener("start", function (e) {
    try { var d = JSON.parse(e.data); if (d.command) setText("lastCommand", d.command); } catch (x) {}
  });

  es.addEventListener("log", function (e) {
    try { appendLog(JSON.parse(e.data).line); } catch (x) {}
  });

  // Server-side busy/precondition message (distinct from native connection error).
  es.addEventListener("busy", function (e) {
    var msg = "已有任务正在运行，请稍候。";
    try { if (e.data) msg = JSON.parse(e.data).message || msg; } catch (x) {}
    es._done = true;
    es.close();
    appendLog("[提示] " + msg);
    showToast(msg, false);
    setButtonsDisabled(false);
    setRunStatus("idle", "空闲");
    setQuickStatus("idle", "就绪");
    setStepState(stepElement[step] || "", "");
  });

  es.addEventListener("done", function (e) {
    es._done = true;
    es.close();
    var d = { ok: false, step: step, returncode: "-", duration_seconds: 0 };
    try { d = JSON.parse(e.data); } catch (x) {}
    if (d.error) appendLog("[错误] " + d.error);
    finalizeRun(d);
  });

  // Native EventSource error (connection dropped). Ignore if we already finished.
  es.onerror = function () {
    if (es._done) return;
    es._done = true;
    es.close();
    appendLog("[错误] 与服务器的连接中断。");
    finalizeRun({ ok: false, step: step, returncode: "-", duration_seconds: 0 });
  };
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
    case "payment_rate":
      return (Number(value) * 100).toFixed(2) + "%";
    default:
      return String(value);
  }
}

function buildSparkline(values) {
  if (!values || values.length < 2) return "";
  var w = 132, h = 30, pad = 2;
  var min = Math.min.apply(null, values);
  var max = Math.max.apply(null, values);
  var range = max - min || 1;
  var n = values.length;
  function px(i) { return pad + (i * (w - 2 * pad)) / (n - 1); }
  function py(v) { return h - pad - ((v - min) / range) * (h - 2 * pad); }
  var pts = values.map(function (v, i) { return px(i).toFixed(1) + "," + py(v).toFixed(1); });
  var cls = values[n - 1] >= values[0] ? "up" : "down";
  return (
    '<svg class="kpi-spark ' + cls + '" viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">' +
    '<polyline points="' + pts.join(" ") + '" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />' +
    '<circle cx="' + px(n - 1).toFixed(1) + '" cy="' + py(values[n - 1]).toFixed(1) + '" r="2" fill="currentColor" />' +
    "</svg>"
  );
}

function renderKpiCards(metrics, series) {
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
    var spark = series && series[m.key] ? buildSparkline(series[m.key]) : "";
    return (
      '<div class="kpi-card">' +
      '<span class="kpi-label">' + m.label + "</span>" +
      '<span class="kpi-value">' + (m.value == null ? "-" : formatKpi(m.key, m.value)) + "</span>" +
      '<div class="kpi-foot">' + deltaHtml + spark + "</div>" +
      "</div>"
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
    if (data.ok && data.metrics && data.metrics.length) {
      var series = {};
      try {
        var s = await apiJson("/api/kpi-series?project=" + encodeURIComponent(selectedProject()));
        if (s.ok) series = s.series;
      } catch (e) { /* sparkline optional */ }
      renderKpiCards(data.metrics, series);
    } else {
      renderKpiEmpty("运行流程后生成");
    }
  } catch (e) {
    renderKpiEmpty("加载失败");
  }
  refreshAlerts();
}

var ALERT_LABELS = {
  revenue: "收入", dau: "DAU", ecpm: "eCPM",
  payment_rate: "付费率", d1_retention: "次日留存", d7_retention: "7 日留存",
};

async function refreshAlerts() {
  var banner = document.getElementById("alertBanner");
  if (!banner) return;
  try {
    var data = await apiJson("/api/alerts?project=" + encodeURIComponent(selectedProject()));
    var alerts = (data && data.alerts) || [];
    if (!data.ok || !alerts.length) {
      banner.hidden = true;
      banner.innerHTML = "";
      return;
    }
    var items = alerts.map(function (a) {
      var label = ALERT_LABELS[a.metric] || a.metric;
      return '<li><span class="alert-metric">' + label + "</span>" + escapeHtml(a.message) + "</li>";
    }).join("");
    banner.innerHTML =
      '<div class="alert-head">⚠ 异常告警 · ' + escapeHtml(data.report_date || "") +
      ' <span class="alert-count">' + alerts.length + " 项</span></div>" +
      "<ul class=\"alert-list\">" + items + "</ul>";
    banner.hidden = false;
  } catch (e) {
    banner.hidden = true;
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

  setVal("settingsProjectPath", project ? project.path : "projects/" + selectedProject());
  setVal("settingsProjectId", selectedProject());

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
// Config center (Settings forms)
// ===================================================================

let settingsLoaded = false;

function setVal(id, value) {
  var el = document.getElementById(id);
  if (el) el.value = value == null ? "" : value;
}
function getVal(id) {
  var el = document.getElementById(id);
  return el ? el.value.trim() : "";
}
function getChecked(id) {
  var el = document.getElementById(id);
  return el ? !!el.checked : false;
}
function setChecked(id, value) {
  var el = document.getElementById(id);
  if (el) el.checked = !!value;
}
function setCfgMsg(id, ok, text) {
  var el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = "cfg-hint " + (ok ? "success" : "error");
}
function setKeyBadge(id, isSet) {
  setBadge(id, isSet ? "ok" : "unknown", isSet ? "已设置" : "未设置");
}

// --- Project config ---
async function loadProjectConfig() {
  try {
    var c = await apiJson("/api/config/project?project=" + encodeURIComponent(selectedProject()));
    setVal("cfgProjectName", c.project_name);
    setVal("cfgTimezone", c.timezone);
    setVal("cfgCurrency", c.currency);
    setVal("cfgTableauWorkbook", c.tableau_workbook);
    setVal("settingsProjectId", c.project_id);
  } catch (e) { setCfgMsg("projMsg", false, "加载失败"); }
}
async function saveProjectConfig() {
  try {
    await apiJson("/api/config/project?project=" + encodeURIComponent(selectedProject()), {
      method: "POST",
      body: JSON.stringify({
        project_name: getVal("cfgProjectName"),
        timezone: getVal("cfgTimezone"),
        currency: getVal("cfgCurrency"),
        tableau_workbook: getVal("cfgTableauWorkbook"),
      }),
    });
    setCfgMsg("projMsg", true, "已保存");
    showToast("项目信息已保存", true);
    await loadProjects();
    refreshStatus();
  } catch (e) { setCfgMsg("projMsg", false, "保存失败：" + e.message); showToast("保存失败", false); }
}
async function createProject() {
  var pid = getVal("newProjectId");
  if (!pid) { setCfgMsg("createProjectMsg", false, "请输入项目 ID"); return; }
  setCfgMsg("createProjectMsg", true, "创建中…");
  try {
    var r = await apiJson("/api/init-project", {
      method: "POST",
      body: JSON.stringify({ project: pid, name: getVal("newProjectName") }),
    });
    if (r.ok === false) throw new Error(r.stderr || "创建失败");
    setCfgMsg("createProjectMsg", true, "已创建：" + pid);
    showToast("项目已创建：" + pid, true);
    setVal("newProjectId", ""); setVal("newProjectName", "");
    await loadProjects();
    projectSelect.value = pid;
    refreshStatus(); refreshKpis(); loadProjectConfig();
  } catch (e) { setCfgMsg("createProjectMsg", false, "创建失败：" + e.message); showToast("创建失败", false); }
}

// --- AI config ---
async function loadAiConfig() {
  try {
    var c = await apiJson("/api/config/ai");
    setChecked("aiUseDeepseek", c.use_deepseek);
    setChecked("aiFallback", c.fallback_to_rule_template);
    setVal("aiModel", c.model);
    setVal("aiBaseUrl", c.base_url);
    setVal("aiTemperature", c.temperature);
    setVal("aiMaxTokens", c.max_tokens);
    setKeyBadge("aiKeyStatus", c.deepseek_api_key_set);
  } catch (e) { setCfgMsg("aiMsg", false, "加载失败"); }
}
async function saveAiConfig() {
  try {
    var r = await apiJson("/api/config/ai", {
      method: "POST",
      body: JSON.stringify({
        use_deepseek: getChecked("aiUseDeepseek"),
        fallback_to_rule_template: getChecked("aiFallback"),
        model: getVal("aiModel"),
        base_url: getVal("aiBaseUrl"),
        temperature: parseFloat(getVal("aiTemperature")) || 0.3,
        max_tokens: parseInt(getVal("aiMaxTokens"), 10) || 2000,
        deepseek_api_key: getVal("aiApiKey") || null,
      }),
    });
    setVal("aiApiKey", "");
    setKeyBadge("aiKeyStatus", r.deepseek_api_key_set);
    setCfgMsg("aiMsg", true, "已保存");
    showToast("AI 配置已保存", true);
  } catch (e) { setCfgMsg("aiMsg", false, "保存失败：" + e.message); showToast("保存失败", false); }
}

// --- Metric rules ---
async function loadMetricRules() {
  try {
    var c = await apiJson("/api/config/metric-rules");
    setVal("ruleRevenue", c.revenue_drop_threshold);
    setVal("ruleDau", c.dau_drop_threshold);
    setVal("ruleEcpm", c.ecpm_drop_threshold);
    setVal("rulePaymentRate", c.payment_rate_drop_threshold);
    setVal("ruleRetention", c.retention_drop_point_threshold);
  } catch (e) { setCfgMsg("rulesMsg", false, "加载失败"); }
}
async function saveMetricRules() {
  try {
    await apiJson("/api/config/metric-rules", {
      method: "POST",
      body: JSON.stringify({
        revenue_drop_threshold: parseFloat(getVal("ruleRevenue")) || 0,
        dau_drop_threshold: parseFloat(getVal("ruleDau")) || 0,
        ecpm_drop_threshold: parseFloat(getVal("ruleEcpm")) || 0,
        payment_rate_drop_threshold: parseFloat(getVal("rulePaymentRate")) || 0,
        retention_drop_point_threshold: parseFloat(getVal("ruleRetention")) || 0,
      }),
    });
    setCfgMsg("rulesMsg", true, "已保存");
    showToast("指标规则已保存", true);
  } catch (e) { setCfgMsg("rulesMsg", false, "保存失败：" + e.message); showToast("保存失败", false); }
}

// --- Email config ---
async function loadEmailConfig() {
  try {
    var c = await apiJson("/api/config/email");
    setVal("mailHost", c.smtp_host);
    setVal("mailPort", c.smtp_port);
    setVal("mailUser", c.smtp_user);
    setVal("mailFrom", c.mail_from);
    setVal("mailTo", c.mail_to);
    setVal("mailCc", (c.cc || []).join(", "));
    setKeyBadge("mailPwStatus", c.smtp_password_set);
  } catch (e) { setCfgMsg("emailMsg", false, "加载失败"); }
}
async function saveEmailConfig() {
  try {
    var r = await apiJson("/api/config/email", {
      method: "POST",
      body: JSON.stringify({
        smtp_host: getVal("mailHost"),
        smtp_port: getVal("mailPort"),
        smtp_user: getVal("mailUser"),
        smtp_password: getVal("mailPassword") || null,
        mail_from: getVal("mailFrom"),
        mail_to: getVal("mailTo"),
        cc: getVal("mailCc").split(",").map(function (s) { return s.trim(); }).filter(Boolean),
      }),
    });
    setVal("mailPassword", "");
    setKeyBadge("mailPwStatus", r.smtp_password_set);
    setCfgMsg("emailMsg", true, "已保存");
    showToast("邮件配置已保存", true);
  } catch (e) { setCfgMsg("emailMsg", false, "保存失败：" + e.message); showToast("保存失败", false); }
}

// --- Sources (Unity / AppLovin) ---
async function loadSourcesConfig() {
  try {
    var c = await apiJson("/api/config/sources");
    setChecked("unityEnabled", c.unity.enabled);
    setKeyBadge("unityKeyStatus", c.unity.api_key_set);
    setChecked("applovinEnabled", c.applovin.enabled);
    setKeyBadge("applovinKeyStatus", c.applovin.api_key_set);
  } catch (e) { setCfgMsg("sourcesMsg", false, "加载失败"); }
}
async function saveSourcesConfig() {
  try {
    var r = await apiJson("/api/config/sources", {
      method: "POST",
      body: JSON.stringify({
        unity: { enabled: getChecked("unityEnabled"), api_key: getVal("unityApiKey") || null },
        applovin: { enabled: getChecked("applovinEnabled"), api_key: getVal("applovinApiKey") || null },
      }),
    });
    setVal("unityApiKey", ""); setVal("applovinApiKey", "");
    setKeyBadge("unityKeyStatus", r.unity.api_key_set);
    setKeyBadge("applovinKeyStatus", r.applovin.api_key_set);
    setCfgMsg("sourcesMsg", true, "已保存");
    showToast("数据源配置已保存", true);
    refreshStatus();
  } catch (e) { setCfgMsg("sourcesMsg", false, "保存失败：" + e.message); showToast("保存失败", false); }
}

// --- Raw YAML editor ---
async function loadRawConfig() {
  var name = getVal("rawConfigName") || "field_mappings";
  try {
    var c = await apiJson("/api/config/raw?name=" + encodeURIComponent(name));
    setVal("rawConfigContent", c.content);
    setCfgMsg("rawMsg", true, c.path);
  } catch (e) { setCfgMsg("rawMsg", false, "加载失败：" + e.message); }
}
async function saveRawConfig() {
  var name = getVal("rawConfigName") || "field_mappings";
  try {
    await apiJson("/api/config/raw?name=" + encodeURIComponent(name), {
      method: "POST",
      body: JSON.stringify({ content: document.getElementById("rawConfigContent").value }),
    });
    setCfgMsg("rawMsg", true, "已保存并通过 YAML 校验");
    showToast("配置已保存", true);
  } catch (e) { setCfgMsg("rawMsg", false, "保存失败：" + e.message); showToast("YAML 校验/保存失败", false); }
}

// --- Auto schedule (Windows Task Scheduler) ---
async function loadSchedule() {
  var statusEl = document.getElementById("scheduleStatusText");
  try {
    var c = await apiJson("/api/schedule?project=" + encodeURIComponent(selectedProject()));
    setChecked("scheduleEnabled", !!c.enabled);
    if (c.time) setVal("scheduleTime", c.time);
    if (statusEl) {
      if (!c.supported) {
        statusEl.textContent = "当前系统非 Windows，无法注册计划任务。";
      } else if (c.enabled) {
        statusEl.textContent = "已启用：每天 " + (c.time || "") + " 运行项目 " + c.project + "（任务 " + c.task + "）。";
      } else {
        statusEl.textContent = "未启用。勾选后保存即可注册每日计划任务（保存时会弹出 UAC 授权窗口，请点“是”）。";
      }
    }
  } catch (e) {
    if (statusEl) statusEl.textContent = "加载调度状态失败：" + e.message;
  }
}
async function saveSchedule() {
  var enabled = getChecked("scheduleEnabled");
  try {
    if (enabled) {
      await apiJson("/api/schedule", {
        method: "POST",
        body: JSON.stringify({ project: selectedProject(), time: getVal("scheduleTime") || "08:30" }),
      });
      setCfgMsg("scheduleMsg", true, "已注册计划任务");
      showToast("自动调度已启用", true);
    } else {
      await apiJson("/api/schedule?project=" + encodeURIComponent(selectedProject()), { method: "DELETE" });
      setCfgMsg("scheduleMsg", true, "已移除计划任务");
      showToast("自动调度已关闭", true);
    }
    loadSchedule();
  } catch (e) {
    setCfgMsg("scheduleMsg", false, "保存失败：" + e.message);
    showToast("调度保存失败", false);
  }
}

function loadAllSettings() {
  loadProjectConfig();
  loadAiConfig();
  loadMetricRules();
  loadEmailConfig();
  loadSourcesConfig();
  loadRawConfig();
  loadGa4Config();
  loadSchedule();
}

// ===================================================================
// Event binding
// ===================================================================

function bindEvents() {
  document.querySelectorAll(".sidebar-item").forEach(function (item) {
    item.addEventListener("click", function () { navigateTo(item.getAttribute("data-page")); });
  });

  if (refreshStatusBtn) refreshStatusBtn.addEventListener("click", function () { refreshStatus(); refreshKpis(); });
  if (projectSelect) projectSelect.addEventListener("change", function () {
    refreshStatus(); refreshKpis(); loadGa4Config(); loadProjectConfig(); loadSchedule();
  });

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

  // Config center
  bind("projLoadBtn", loadProjectConfig);
  bind("projSaveBtn", saveProjectConfig);
  bind("createProjectBtn", createProject);
  bind("aiLoadBtn", loadAiConfig);
  bind("aiSaveBtn", saveAiConfig);
  bind("rulesLoadBtn", loadMetricRules);
  bind("rulesSaveBtn", saveMetricRules);
  bind("emailLoadBtn", loadEmailConfig);
  bind("emailSaveBtn", saveEmailConfig);
  bind("sourcesLoadBtn", loadSourcesConfig);
  bind("sourcesSaveBtn", saveSourcesConfig);
  bind("rawLoadBtn", loadRawConfig);
  bind("rawSaveBtn", saveRawConfig);
  bind("scheduleSaveBtn", saveSchedule);
  var rawSel = document.getElementById("rawConfigName");
  if (rawSel) rawSel.addEventListener("change", loadRawConfig);

  // New project quick button (header) → settings project tab
  bind("newProjectBtn", function () {
    navigateTo("settings");
    setTimeout(function () {
      switchTab("settings", "project");
      var el = document.getElementById("newProjectId");
      if (el) el.focus();
    }, 50);
  });
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
    appendLog("[初始化失败] " + error.message);
  }
}

init();
