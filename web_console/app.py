from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import json

import yaml
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = Path(__file__).resolve().parent
STATIC_DIR = WEB_ROOT / "static"

sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import (  # noqa: E402
    ensure_project_dirs,
    get_project_paths,
    load_project_config,
    normalize_project_id,
)


app = FastAPI(title="Daily Report System Console")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
PYTHON_RUNNER = "py"
MAX_PREVIEW_LINES = 200
MAX_PREVIEW_CHARS = 20_000


class RunStepRequest(BaseModel):
    project: str = "default"
    step: str


class RunSequenceRequest(BaseModel):
    project: str = "default"
    steps: list[str]


class InitProjectRequest(BaseModel):
    project: str
    name: str = ""


class Ga4ReportsConfig(BaseModel):
    daily_overview: bool = True
    country_platform_daily: bool = True
    event_daily: bool = True


class Ga4ConfigRequest(BaseModel):
    enabled: bool = False
    property_id: str = ""
    credentials_path: str = "secrets/ga4-service-account.json"
    start_date: str = "7daysAgo"
    end_date: str = "yesterday"
    reports: Ga4ReportsConfig = Ga4ReportsConfig()


def validate_project_id(project_id: str | None) -> str:
    project_id = normalize_project_id(project_id)
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise HTTPException(status_code=400, detail="Invalid project id.")
    return project_id


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def count_files(directory: Path, pattern: str, recursive: bool = False) -> int:
    if not directory.exists():
        return 0
    iterator = directory.rglob(pattern) if recursive else directory.glob(pattern)
    return sum(1 for file_path in iterator if file_path.is_file())


def latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    files = [file_path for file_path in directory.glob(pattern) if file_path.is_file()]
    if not files:
        return None
    return max(files, key=lambda file_path: file_path.stat().st_mtime)


def load_project_list() -> list[dict[str, str]]:
    projects_dir = PROJECT_ROOT / "projects"
    if not projects_dir.exists():
        return []

    projects: list[dict[str, str]] = []
    for config_path in sorted(projects_dir.glob("*/project.yaml")):
        project_id = config_path.parent.name
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            continue

        project_name = ""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                project_name = str(data.get("project_name", ""))
        except Exception:
            project_name = ""

        projects.append(
            {
                "project_id": project_id,
                "project_name": project_name,
                "path": relative_path(config_path.parent),
            }
        )
    return projects


def build_step_command(step: str, project_id: str) -> list[str]:
    commands: dict[str, list[str]] = {
        "list_projects": [PYTHON_RUNNER, "scripts/list_projects.py"],
        "fetch_ga4_api": [PYTHON_RUNNER, "scripts/fetch_ga4_api.py", "--project", project_id],
        "import_raw_csv": [PYTHON_RUNNER, "scripts/import_raw_csv.py", "--project", project_id],
        "build_mart": [PYTHON_RUNNER, "scripts/build_mart_from_clean.py", "--project", project_id],
        "sync_tableau": [
            PYTHON_RUNNER,
            "scripts/sync_mart_to_tableau_datasource.py",
            "--project",
            project_id,
        ],
        "generate_ai_context": [PYTHON_RUNNER, "scripts/generate_ai_context.py", "--project", project_id],
        "generate_ai_report": [PYTHON_RUNNER, "scripts/generate_ai_report.py", "--project", project_id],
        "run_real_pipeline": [PYTHON_RUNNER, "scripts/run_real_daily_report.py", "--project", project_id],
        "check_pdf": [PYTHON_RUNNER, "scripts/check_pdf_output.py", "--project", project_id],
        "send_email_dry_run": [PYTHON_RUNNER, "scripts/send_report_email.py", "--project", project_id],
    }
    if step not in commands:
        raise HTTPException(status_code=400, detail=f"Unsupported step: {step}")
    return commands[step]


def run_command(command: list[str], step: str, timeout_seconds: int = 300) -> dict[str, Any]:
    started_at = time.perf_counter()
    command_text = subprocess.list2cmdline(command)
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }

    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=env,
        )
        duration = round(time.perf_counter() - started_at, 2)
        return {
            "ok": result.returncode == 0,
            "step": step,
            "command": command_text,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_seconds": duration,
        }
    except subprocess.TimeoutExpired as exc:
        duration = round(time.perf_counter() - started_at, 2)
        return {
            "ok": False,
            "step": step,
            "command": command_text,
            "returncode": -1,
            "stdout": exc.stdout or "",
            "stderr": f"Command timed out after {timeout_seconds} seconds.",
            "duration_seconds": duration,
        }
    except FileNotFoundError as exc:
        duration = round(time.perf_counter() - started_at, 2)
        return {
            "ok": False,
            "step": step,
            "command": command_text,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command runner not found: {exc}",
            "duration_seconds": duration,
        }
    except Exception as exc:
        duration = round(time.perf_counter() - started_at, 2)
        return {
            "ok": False,
            "step": step,
            "command": command_text,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Unexpected error: {exc}",
            "duration_seconds": duration,
        }


def run_step_internal(step: str, project_id: str) -> dict[str, Any]:
    command = build_step_command(step, project_id)
    return run_command(command, step)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/projects")
def api_projects() -> list[dict[str, str]]:
    return load_project_list()


@app.get("/api/project-status")
def api_project_status(project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    paths = ensure_project_dirs(project_id)
    config = load_project_config(project_id)

    latest_pdf = latest_file(paths["pdf_dir"], "*.pdf")
    latest_log = latest_file(paths["logs_dir"], "*.log")

    return {
        "project_id": project_id,
        "project_name": str(config.get("project_name", "")),
        "paths": {
            "raw_unity": relative_path(paths["raw_unity_dir"]),
            "raw_applovin": relative_path(paths["raw_applovin_dir"]),
            "raw_ga4": relative_path(paths["raw_ga4_dir"]),
            "clean": relative_path(paths["clean_dir"]),
            "mart": relative_path(paths["mart_dir"]),
            "tableau_datasource": relative_path(paths["tableau_datasource_dir"]),
            "ai_context": relative_path(paths["ai_context_dir"]),
            "ai_draft": relative_path(paths["ai_draft_dir"]),
            "pdf": relative_path(paths["pdf_dir"]),
        },
        "counts": {
            "raw_unity_csv": count_files(paths["raw_unity_dir"], "*.csv"),
            "raw_applovin_csv": count_files(paths["raw_applovin_dir"], "*.csv"),
            "raw_ga4_csv": count_files(paths["raw_ga4_dir"], "*.csv"),
            "clean_csv": count_files(paths["clean_dir"], "*.csv", recursive=True),
            "mart_csv": count_files(paths["mart_dir"], "*.csv"),
            "tableau_csv": count_files(paths["tableau_datasource_dir"], "*.csv"),
            "pdf": count_files(paths["pdf_dir"], "*.pdf"),
        },
        "latest_files": {
            "latest_pdf": relative_path(latest_pdf) if latest_pdf else None,
            "latest_log": relative_path(latest_log) if latest_log else None,
        },
    }


@app.post("/api/run-step")
def api_run_step(payload: RunStepRequest) -> dict[str, Any]:
    project_id = validate_project_id(payload.project)
    return run_step_internal(payload.step, project_id)


@app.post("/api/run-sequence")
def api_run_sequence(payload: RunSequenceRequest) -> dict[str, Any]:
    project_id = validate_project_id(payload.project)
    results: list[dict[str, Any]] = []

    for step in payload.steps:
        result = run_step_internal(step, project_id)
        results.append(result)
        if not result["ok"]:
            break

    return {
        "ok": all(result["ok"] for result in results),
        "project": project_id,
        "results": results,
    }


@app.get("/api/read-file")
def api_read_file(project: str = Query(default="default"), type: str = Query(...)) -> dict[str, Any]:
    project_id = validate_project_id(project)
    paths = get_project_paths(project_id)

    file_map = {
        "ai_report_text": paths["tableau_datasource_dir"] / "ai_report_text.csv",
        "ai_context": paths["ai_context_dir"] / "daily_ai_context.json",
        "ai_draft": paths["ai_draft_dir"] / "daily_report_draft.md",
    }

    if type == "latest_log":
        target = latest_file(paths["logs_dir"], "*.log")
    elif type in file_map:
        target = file_map[type]
    else:
        raise HTTPException(status_code=400, detail="Unsupported file preview type.")

    if target is None or not target.exists():
        return {
            "ok": False,
            "type": type,
            "path": None,
            "content": "",
            "truncated": False,
            "message": "File does not exist yet.",
        }

    content = target.read_text(encoding="utf-8-sig", errors="replace")
    line_limited = "".join(content.splitlines(keepends=True)[:MAX_PREVIEW_LINES])
    truncated = line_limited != content
    if len(line_limited) > MAX_PREVIEW_CHARS:
        line_limited = line_limited[:MAX_PREVIEW_CHARS]
        truncated = True

    return {
        "ok": True,
        "type": type,
        "path": relative_path(target),
        "content": line_limited,
        "truncated": truncated,
        "message": "",
    }


@app.post("/api/init-project")
def api_init_project(payload: InitProjectRequest) -> dict[str, Any]:
    project_id = validate_project_id(payload.project)
    project_name = payload.name.strip() or project_id
    command = [
        PYTHON_RUNNER,
        "scripts/init_project.py",
        "--project",
        project_id,
        "--name",
        project_name,
    ]
    return run_command(command, "init_project")


# ---------------------------------------------------------------------------
# GA4 Configuration helpers
# ---------------------------------------------------------------------------

GA4_CONFIG_PATH = PROJECT_ROOT / "config" / "api_sources.yaml"
GA4_CREDENTIALS_PATH = PROJECT_ROOT / "secrets" / "ga4-service-account.json"
GA4_DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "property_id": "",
    "credentials_path": "secrets/ga4-service-account.json",
    "start_date": "7daysAgo",
    "end_date": "yesterday",
    "reports": {
        "daily_overview": True,
        "country_platform_daily": True,
        "event_daily": True,
    },
}


def _read_api_sources() -> dict[str, Any]:
    if not GA4_CONFIG_PATH.exists():
        return {}
    with open(GA4_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _write_api_sources(data: dict[str, Any]) -> None:
    GA4_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GA4_CONFIG_PATH, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# GA4 Configuration API endpoints
# ---------------------------------------------------------------------------


@app.get("/api/config/ga4")
def api_get_ga4_config() -> dict[str, Any]:
    data = _read_api_sources()
    ga4 = data.get("ga4", {})
    if not isinstance(ga4, dict):
        ga4 = {}

    config = {
        "exists": GA4_CONFIG_PATH.exists(),
        "ga4": {
            "enabled": bool(ga4.get("enabled", GA4_DEFAULT_CONFIG["enabled"])),
            "property_id": str(ga4.get("property_id", GA4_DEFAULT_CONFIG["property_id"])).strip(),
            "credentials_path": str(
                ga4.get("credentials_path", GA4_DEFAULT_CONFIG["credentials_path"])
            ).strip(),
            "start_date": str(ga4.get("start_date", GA4_DEFAULT_CONFIG["start_date"])).strip(),
            "end_date": str(ga4.get("end_date", GA4_DEFAULT_CONFIG["end_date"])).strip(),
            "reports": {
                "daily_overview": bool(
                    ga4.get("reports", {}).get("daily_overview", True)
                ),
                "country_platform_daily": bool(
                    ga4.get("reports", {}).get("country_platform_daily", True)
                ),
                "event_daily": bool(
                    ga4.get("reports", {}).get("event_daily", True)
                ),
            },
        },
        "credentials_exists": GA4_CREDENTIALS_PATH.exists(),
        "config_path": relative_path(GA4_CONFIG_PATH),
    }
    return config


@app.post("/api/config/ga4")
def api_save_ga4_config(payload: Ga4ConfigRequest) -> dict[str, Any]:
    data = _read_api_sources()

    data["ga4"] = {
        "enabled": payload.enabled,
        "property_id": payload.property_id.strip(),
        "credentials_path": payload.credentials_path.strip(),
        "start_date": payload.start_date.strip(),
        "end_date": payload.end_date.strip(),
        "reports": {
            "daily_overview": payload.reports.daily_overview,
            "country_platform_daily": payload.reports.country_platform_daily,
            "event_daily": payload.reports.event_daily,
        },
    }

    _write_api_sources(data)

    return {
        "ok": True,
        "ga4": data["ga4"],
        "credentials_exists": GA4_CREDENTIALS_PATH.exists(),
        "config_path": relative_path(GA4_CONFIG_PATH),
    }


@app.post("/api/config/ga4/upload-credentials")
async def api_upload_ga4_credentials(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed.")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 2 MB.")

    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}") from exc

    GA4_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GA4_CREDENTIALS_PATH.write_bytes(content)

    return {
        "ok": True,
        "path": relative_path(GA4_CREDENTIALS_PATH),
    }


@app.post("/api/config/ga4/check")
def api_check_ga4_config() -> dict[str, Any]:
    messages: list[str] = []
    ok = True

    if not GA4_CONFIG_PATH.exists():
        messages.append("config/api_sources.yaml does not exist.")
        return {"ok": False, "messages": messages}

    data = _read_api_sources()
    ga4 = data.get("ga4", {})
    if not isinstance(ga4, dict):
        messages.append("ga4 section is missing or invalid in api_sources.yaml.")
        return {"ok": False, "messages": messages}

    enabled = bool(ga4.get("enabled", False))
    if not enabled:
        messages.append("GA4 is disabled (enabled: false).")
        ok = False

    property_id = str(ga4.get("property_id", "")).strip()
    if not property_id:
        messages.append("property_id is empty.")
        ok = False
    else:
        messages.append(f"property_id: {property_id}")

    credentials_path_text = str(ga4.get("credentials_path", "")).strip()
    if not credentials_path_text:
        messages.append("credentials_path is empty.")
        ok = False
    else:
        cred_path = PROJECT_ROOT / credentials_path_text
        if not cred_path.exists():
            messages.append(f"Credentials file not found: {credentials_path_text}")
            ok = False
        else:
            try:
                with open(cred_path, "r", encoding="utf-8") as f:
                    json.load(f)
                messages.append(f"Credentials file OK: {credentials_path_text}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                messages.append(f"Credentials file is not valid JSON: {credentials_path_text}")
                ok = False

    start_date = str(ga4.get("start_date", "")).strip()
    if not start_date:
        messages.append("start_date is empty.")
        ok = False
    else:
        messages.append(f"start_date: {start_date}")

    end_date = str(ga4.get("end_date", "")).strip()
    if not end_date:
        messages.append("end_date is empty.")
        ok = False
    else:
        messages.append(f"end_date: {end_date}")

    if ok:
        messages.insert(0, "All GA4 configuration checks passed.")

    return {"ok": ok, "messages": messages}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
