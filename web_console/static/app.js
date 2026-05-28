const projectSelect = document.getElementById("projectSelect");
const refreshStatusBtn = document.getElementById("refreshStatusBtn");
const runPipelineBtn = document.getElementById("runPipelineBtn");
const runStatus = document.getElementById("runStatus");

let projects = [];
let currentStatus = null;
let isRunning = false;

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

function selectedProject() {
  return projectSelect.value || "default";
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

function setText(id, value) {
  document.getElementById(id).textContent = value ?? "-";
}

function setRunState(state, label) {
  runStatus.className = `run-status ${state}`;
  runStatus.textContent = label;
}

function setButtonsDisabled(disabled) {
  isRunning = disabled;
  document
    .querySelectorAll("button")
    .forEach((button) => {
      button.disabled = disabled;
    });
}

function setOutput(result) {
  setText("lastCommand", result.command || "-");
  setText("lastReturnCode", String(result.returncode ?? "-"));
  setText("stdoutBox", result.stdout || "-");
  setText("stderrBox", result.stderr || "-");

  if (result.ok) {
    setRunState("success", `Success · ${result.duration_seconds ?? 0}s`);
  } else {
    setRunState("failed", `Failed · ${result.duration_seconds ?? 0}s`);
  }
}

function updateProjectMeta() {
  const project = projects.find((item) => item.project_id === selectedProject());
  setText("projectName", project?.project_name || currentStatus?.project_name || "-");
  setText("projectPath", project?.path || `projects/${selectedProject()}`);
}

function updateStatusView(status) {
  currentStatus = status;
  updateProjectMeta();

  setText("rawUnityCount", status.counts.raw_unity_csv);
  setText("rawApplovinCount", status.counts.raw_applovin_csv);
  setText("rawGa4Count", status.counts.raw_ga4_csv);
  setText("cleanCount", status.counts.clean_csv);
  setText("martCount", status.counts.mart_csv);
  setText("tableauCount", status.counts.tableau_csv);
  setText("pdfCount", status.counts.pdf);

  setText("latestPdf", status.latest_files.latest_pdf || "-");
  setText("latestLog", status.latest_files.latest_log || "-");

  setText("rawUnityPath", `${status.paths.raw_unity}/`);
  setText("rawApplovinPath", `${status.paths.raw_applovin}/`);
  setText("rawGa4Path", `${status.paths.raw_ga4}/`);
}

async function loadProjects() {
  projects = await apiJson("/api/projects");
  projectSelect.innerHTML = "";

  if (!projects.length) {
    const option = document.createElement("option");
    option.value = "default";
    option.textContent = "default";
    projectSelect.appendChild(option);
    return;
  }

  for (const project of projects) {
    const option = document.createElement("option");
    option.value = project.project_id;
    option.textContent = `${project.project_id} · ${project.project_name || project.project_id}`;
    projectSelect.appendChild(option);
  }

  const defaultProject = projects.find((item) => item.project_id === "default");
  projectSelect.value = defaultProject ? "default" : projects[0].project_id;
}

async function refreshStatus() {
  const project = selectedProject();
  const status = await apiJson(`/api/project-status?project=${encodeURIComponent(project)}`);
  updateStatusView(status);
}

async function runStep(step) {
  if (isRunning) {
    return;
  }

  setButtonsDisabled(true);
  setRunState("running", "运行中...");
  setText("lastCommand", stepLabels[step] || step);
  setText("lastReturnCode", "-");
  setText("stdoutBox", "Running...");
  setText("stderrBox", "-");

  try {
    const result = await apiJson("/api/run-step", {
      method: "POST",
      body: JSON.stringify({
        project: selectedProject(),
        step,
      }),
    });
    setOutput(result);
    await refreshStatus();
  } catch (error) {
    setOutput({
      ok: false,
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

async function readFile(type) {
  if (isRunning) {
    return;
  }

  setText("previewMeta", "读取中...");
  setText("filePreview", "");

  try {
    const result = await apiJson(
      `/api/read-file?project=${encodeURIComponent(selectedProject())}&type=${encodeURIComponent(type)}`
    );

    if (!result.ok) {
      setText("previewMeta", result.message || "文件暂不存在。");
      setText("filePreview", "文件暂不存在。");
      return;
    }

    const suffix = result.truncated ? " · 已截断预览" : "";
    setText("previewMeta", `${result.path}${suffix}`);
    setText("filePreview", result.content || "(empty file)");
  } catch (error) {
    setText("previewMeta", "读取失败");
    setText("filePreview", error.message);
  }
}

function bindEvents() {
  refreshStatusBtn.addEventListener("click", refreshStatus);
  projectSelect.addEventListener("change", refreshStatus);
  runPipelineBtn.addEventListener("click", () => runStep("run_real_pipeline"));

  document.querySelectorAll(".action-button").forEach((button) => {
    button.addEventListener("click", () => runStep(button.dataset.step));
  });

  document.querySelectorAll(".preview-button").forEach((button) => {
    button.addEventListener("click", () => readFile(button.dataset.type));
  });

  // GA4 config buttons
  document.getElementById("ga4LoadBtn").addEventListener("click", loadGa4Config);
  document.getElementById("ga4SaveBtn").addEventListener("click", saveGa4Config);
  document.getElementById("ga4CheckBtn").addEventListener("click", checkGa4Config);
  document.getElementById("ga4UploadBtn").addEventListener("click", uploadGa4Credentials);
  // ga4FetchBtn is handled by .action-button selector (has data-step="fetch_ga4_api")
}

// ---------------------------------------------------------------------------
// GA4 Configuration
// ---------------------------------------------------------------------------

function setGa4ConfigStatus(ok, text) {
  const el = document.getElementById("ga4ConfigStatus");
  el.textContent = text;
  el.className = `ga4-status-badge ${ok ? "ok" : "fail"}`;
}

function setGa4CredsStatus(ok, text) {
  const el = document.getElementById("ga4CredsStatus");
  el.textContent = text;
  el.className = `ga4-status-badge ${ok ? "ok" : "fail"}`;
}

function setGa4UploadMsg(ok, text) {
  const el = document.getElementById("ga4UploadMsg");
  el.textContent = text;
  el.className = `ga4-hint ${ok ? "success" : "error"}`;
}

function showGa4CheckMessages(messages) {
  const el = document.getElementById("ga4CheckMessages");
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

function fillGa4Form(config) {
  const g = config.ga4;
  document.getElementById("ga4Enabled").checked = g.enabled;
  document.getElementById("ga4PropertyId").value = g.property_id || "";
  document.getElementById("ga4CredentialsPath").value = g.credentials_path || "";
  document.getElementById("ga4StartDate").value = g.start_date || "";
  document.getElementById("ga4EndDate").value = g.end_date || "";
  document.getElementById("ga4ReportDailyOverview").checked = g.reports.daily_overview;
  document.getElementById("ga4ReportCountryPlatform").checked = g.reports.country_platform_daily;
  document.getElementById("ga4ReportEventDaily").checked = g.reports.event_daily;

  if (config.exists) {
    setGa4ConfigStatus(true, "配置文件存在");
  } else if (g.property_id) {
    setGa4ConfigStatus(true, "已加载");
  } else {
    setGa4ConfigStatus(false, "未配置");
  }

  setGa4CredsStatus(config.credentials_exists, config.credentials_exists ? "凭证文件存在" : "凭证文件不存在");
}

async function loadGa4Config() {
  try {
    const config = await apiJson("/api/config/ga4");
    fillGa4Form(config);
    setGa4UploadMsg(true, "配置已加载。");
  } catch (error) {
    setGa4ConfigStatus(false, "加载失败");
    setGa4UploadMsg(false, `加载失败: ${error.message}`);
  }
}

async function saveGa4Config() {
  const payload = getGa4FormValues();
  try {
    const result = await apiJson("/api/config/ga4", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    fillGa4Form({
      exists: true,
      ga4: result.ga4,
      credentials_exists: result.credentials_exists,
    });
    setGa4UploadMsg(true, "配置已保存到 config/api_sources.yaml。");
  } catch (error) {
    setGa4UploadMsg(false, `保存失败: ${error.message}`);
  }
}

async function uploadGa4Credentials() {
  const fileInput = document.getElementById("ga4CredentialsFile");
  const file = fileInput.files[0];
  if (!file) {
    setGa4UploadMsg(false, "请先选择一个 .json 文件。");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  setGa4UploadMsg(true, "上传中...");

  try {
    const response = await fetch("/api/config/ga4/upload-credentials", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    document.getElementById("ga4CredentialsPath").value = data.path;
    setGa4CredsStatus(true, "凭证文件存在");
    setGa4UploadMsg(true, "上传成功。");
    fileInput.value = "";
  } catch (error) {
    setGa4UploadMsg(false, `上传失败: ${error.message}`);
  }
}

async function checkGa4Config() {
  showGa4CheckMessages(["检查中..."]);
  try {
    const result = await apiJson("/api/config/ga4/check", { method: "POST" });
    showGa4CheckMessages(result.messages);
    setGa4ConfigStatus(result.ok, result.ok ? "检查通过" : "检查未通过");
  } catch (error) {
    showGa4CheckMessages([`检查失败: ${error.message}`]);
    setGa4ConfigStatus(false, "检查失败");
  }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

async function init() {
  bindEvents();
  setRunState("idle", "Idle");

  try {
    await loadProjects();
    await refreshStatus();
    loadGa4Config();
  } catch (error) {
    setRunState("failed", "Init failed");
    setText("stderrBox", error.message);
  }
}

init();
