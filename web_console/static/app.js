const projectSelect = document.getElementById("projectSelect");
const refreshStatusBtn = document.getElementById("refreshStatusBtn");
const runPipelineBtn = document.getElementById("runPipelineBtn");
const runStatus = document.getElementById("runStatus");

let projects = [];
let currentStatus = null;
let isRunning = false;

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
  setText("lastCommand", step);
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
}

async function init() {
  bindEvents();
  setRunState("idle", "Idle");

  try {
    await loadProjects();
    await refreshStatus();
  } catch (error) {
    setRunState("failed", "Init failed");
    setText("stderrBox", error.message);
  }
}

init();
