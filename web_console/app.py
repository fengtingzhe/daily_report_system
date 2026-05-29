from __future__ import annotations

import asyncio
import csv
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import json

import yaml
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = Path(__file__).resolve().parent
STATIC_DIR = WEB_ROOT / "static"

sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import (  # noqa: E402
    ensure_project_dirs,
    get_project_paths,
    get_project_root,
    load_project_config,
    normalize_project_id,
)


app = FastAPI(title="Daily Report System Console")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
# 使用当前运行控制台的解释器，便于在虚拟环境/其他机器上稳定运行
PYTHON_RUNNER = sys.executable or "py"
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


KPI_METRICS: list[dict[str, str]] = [
    {"key": "revenue", "label": "总收入"},
    {"key": "dau", "label": "DAU"},
    {"key": "new_users", "label": "新增用户"},
    {"key": "arpdau", "label": "ARPDAU"},
    {"key": "ecpm", "label": "eCPM"},
    {"key": "payment_rate", "label": "付费率"},
    {"key": "d1_retention", "label": "次日留存"},
]


def _read_overview_rows(project_id: str) -> list[dict[str, str]]:
    paths = get_project_paths(project_id)
    candidates = [
        paths["mart_dir"] / "mart_daily_overview.csv",
        paths["tableau_datasource_dir"] / "mart_daily_overview.csv",
    ]
    target = next((path for path in candidates if path.exists()), None)
    if target is None:
        return []
    with open(target, "r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("date")]


def _to_float(value: object) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _aggregate_by_date(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Sum across projects so KPIs reflect a single daily timeline."""
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        date = row.get("date", "").strip()
        if not date:
            continue
        bucket = buckets.setdefault(
            date,
            {"dau": 0.0, "new_users": 0.0, "revenue": 0.0, "ad_revenue": 0.0,
             "impressions": 0.0, "payers": 0.0, "_ret_w": 0.0, "_ret_wn": 0.0},
        )
        bucket["dau"] += _to_float(row.get("dau"))
        bucket["new_users"] += _to_float(row.get("new_users"))
        bucket["revenue"] += _to_float(row.get("revenue"))
        bucket["ad_revenue"] += _to_float(row.get("ad_revenue"))
        bucket["impressions"] += _to_float(row.get("impressions"))
        bucket["payers"] += _to_float(row.get("payers"))
        if row.get("d1_retention") not in (None, ""):
            # 按 new_users 加权（缺失时退化为等权），与 mart 聚合口径一致。
            weight = _to_float(row.get("new_users")) or 1.0
            bucket["_ret_w"] += _to_float(row.get("d1_retention")) * weight
            bucket["_ret_wn"] += weight
    return buckets


def _metrics_for(bucket: dict[str, float]) -> dict[str, float]:
    dau = bucket["dau"]
    impressions = bucket["impressions"]
    ret_wn = bucket["_ret_wn"]
    return {
        "revenue": bucket["revenue"],
        "dau": dau,
        "new_users": bucket["new_users"],
        "arpdau": (bucket["revenue"] / dau) if dau else 0.0,
        "ecpm": (bucket["ad_revenue"] / impressions * 1000) if impressions else 0.0,
        "payment_rate": (bucket["payers"] / dau) if dau else 0.0,
        "d1_retention": (bucket["_ret_w"] / ret_wn) if ret_wn else 0.0,
    }


@app.get("/api/kpi")
def api_kpi(project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    rows = _read_overview_rows(project_id)
    if not rows:
        return {"ok": False, "message": "mart_daily_overview.csv 不存在或为空。", "metrics": []}

    buckets = _aggregate_by_date(rows)
    dates = sorted(buckets.keys())
    if not dates:
        return {"ok": False, "message": "无有效日期数据。", "metrics": []}

    latest_date = dates[-1]
    prev_date = dates[-2] if len(dates) > 1 else None
    latest = _metrics_for(buckets[latest_date])
    prev = _metrics_for(buckets[prev_date]) if prev_date else None

    metrics: list[dict[str, Any]] = []
    for meta in KPI_METRICS:
        key = meta["key"]
        value = latest.get(key, 0.0)
        delta_pct: float | None = None
        if prev is not None:
            base = prev.get(key, 0.0)
            if base:
                delta_pct = round((value - base) / abs(base) * 100, 1)
        metrics.append({"key": key, "label": meta["label"], "value": value, "delta_pct": delta_pct})

    return {"ok": True, "date": latest_date, "prev_date": prev_date, "metrics": metrics}


@app.get("/api/alerts")
def api_alerts(project: str = Query(default="default")) -> dict[str, Any]:
    """返回最近一次生成的 AI 上下文中的异常告警，供总览页呈现。"""
    project_id = validate_project_id(project)
    paths = get_project_paths(project_id)
    context_path = paths["ai_context_dir"] / "daily_ai_context.json"
    if not context_path.exists():
        return {"ok": False, "message": "尚未生成 AI 上下文，请先运行流水线。", "alerts": []}
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "message": f"读取告警失败：{exc}", "alerts": []}
    alerts = data.get("alerts", []) if isinstance(data, dict) else []
    return {
        "ok": True,
        "report_date": data.get("report_date") if isinstance(data, dict) else None,
        "alerts": alerts,
    }


@app.post("/api/run-step")
def api_run_step(payload: RunStepRequest) -> dict[str, Any]:
    project_id = validate_project_id(payload.project)
    return run_step_internal(payload.step, project_id)


# ---------------------------------------------------------------------------
# Streaming run (SSE) — live log output, non-blocking UI
# ---------------------------------------------------------------------------

_run_lock = threading.Lock()


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/run-stream")
async def api_run_stream(
    project: str = Query(default="default"),
    step: str = Query(...),
) -> StreamingResponse:
    project_id = validate_project_id(project)
    command = build_step_command(step, project_id)  # raises 400 for unknown steps
    command_text = subprocess.list2cmdline(command)

    async def event_gen():
        if not _run_lock.acquire(blocking=False):
            yield _sse("busy", {"message": "已有任务正在运行，请稍候。"})
            return

        proc: subprocess.Popen | None = None
        try:
            yield _sse("start", {"step": step, "command": command_text})
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
            started_at = time.perf_counter()

            try:
                proc = subprocess.Popen(
                    command,
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    bufsize=1,
                )
            except Exception as exc:  # noqa: BLE001
                yield _sse("done", {
                    "ok": False, "step": step, "returncode": -1,
                    "duration_seconds": 0.0, "error": f"无法启动命令: {exc}",
                })
                return

            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()

            def reader() -> None:
                try:
                    for line in proc.stdout:  # type: ignore[union-attr]
                        loop.call_soon_threadsafe(queue.put_nowait, line.rstrip("\n"))
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            threading.Thread(target=reader, daemon=True).start()

            while True:
                line = await queue.get()
                if line is None:
                    break
                yield _sse("log", {"line": line})

            proc.wait()
            duration = round(time.perf_counter() - started_at, 2)
            yield _sse("done", {
                "ok": proc.returncode == 0,
                "step": step,
                "returncode": proc.returncode,
                "duration_seconds": duration,
            })
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
            _run_lock.release()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


def _ga4_credentials_path(project_id: str) -> Path:
    return get_project_root(project_id) / "secrets" / "ga4-service-account.json"



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
def api_get_ga4_config(project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    cred_path = _ga4_credentials_path(project_id)

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
        "credentials_exists": cred_path.exists(),
        "config_path": relative_path(GA4_CONFIG_PATH),
    }
    return config


@app.post("/api/config/ga4")
def api_save_ga4_config(payload: Ga4ConfigRequest, project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    cred_path = _ga4_credentials_path(project_id)
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
        "credentials_exists": cred_path.exists(),
        "config_path": relative_path(GA4_CONFIG_PATH),
    }


@app.post("/api/config/ga4/upload-credentials")
async def api_upload_ga4_credentials(
    project: str = Query(default="default"),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    project_id = validate_project_id(project)
    target = _ga4_credentials_path(project_id)

    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed.")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 2 MB.")

    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}") from exc

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    return {
        "ok": True,
        "path": relative_path(target),
    }


@app.post("/api/config/ga4/check")
def api_check_ga4_config(project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    project_root = get_project_root(project_id)

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
        # Resolve relative credentials_path against project root
        cred_path = Path(credentials_path_text)
        if not cred_path.is_absolute():
            cred_path = project_root / credentials_path_text
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


# ===========================================================================
# Config Center (要求1：所有配置都可在网页编辑)
# ===========================================================================

CONFIG_DIR = PROJECT_ROOT / "config"
AI_CONFIG_PATH = CONFIG_DIR / "ai_report.yaml"
METRIC_RULES_PATH = CONFIG_DIR / "metric_rules.yaml"
RECIPIENTS_PATH = CONFIG_DIR / "report_recipients.yaml"
ENV_PATH = PROJECT_ROOT / ".env"

# 可用「原始 YAML 编辑器」编辑的高级配置（白名单，防止越权写文件）
RAW_CONFIG_FILES: dict[str, Path] = {
    "field_mappings": CONFIG_DIR / "field_mappings.yaml",
    "tableau_config": CONFIG_DIR / "tableau_config.yaml",
}

AI_DEFAULTS: dict[str, Any] = {
    "use_deepseek": False,
    "base_url": "https://api.deepseek.com/chat/completions",
    "model": "deepseek-chat",
    "temperature": 0.3,
    "max_tokens": 2000,
    "fallback_to_rule_template": True,
}

METRIC_RULES_DEFAULTS: dict[str, float] = {
    "revenue_drop_threshold": -0.1,
    "dau_drop_threshold": -0.1,
    "ecpm_drop_threshold": -0.15,
    "payment_rate_drop_threshold": -0.15,
    "retention_drop_point_threshold": -0.03,
}


class ProjectConfigRequest(BaseModel):
    project_name: str = ""
    timezone: str = "Asia/Shanghai"
    currency: str = "USD"
    tableau_workbook: str = ""


class AiConfigRequest(BaseModel):
    use_deepseek: bool = False
    base_url: str = AI_DEFAULTS["base_url"]
    model: str = AI_DEFAULTS["model"]
    temperature: float = AI_DEFAULTS["temperature"]
    max_tokens: int = AI_DEFAULTS["max_tokens"]
    fallback_to_rule_template: bool = True
    deepseek_api_key: str | None = None


class MetricRulesRequest(BaseModel):
    revenue_drop_threshold: float = METRIC_RULES_DEFAULTS["revenue_drop_threshold"]
    dau_drop_threshold: float = METRIC_RULES_DEFAULTS["dau_drop_threshold"]
    ecpm_drop_threshold: float = METRIC_RULES_DEFAULTS["ecpm_drop_threshold"]
    payment_rate_drop_threshold: float = METRIC_RULES_DEFAULTS["payment_rate_drop_threshold"]
    retention_drop_point_threshold: float = METRIC_RULES_DEFAULTS["retention_drop_point_threshold"]


class EmailConfigRequest(BaseModel):
    smtp_host: str = ""
    smtp_port: str = ""
    smtp_user: str = ""
    smtp_password: str | None = None
    mail_from: str = ""
    mail_to: str = ""
    cc: list[str] = []


class SourceConfig(BaseModel):
    enabled: bool = False
    api_key: str | None = None


class SourcesConfigRequest(BaseModel):
    unity: SourceConfig = SourceConfig()
    applovin: SourceConfig = SourceConfig()


class RawConfigRequest(BaseModel):
    content: str


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _read_env() -> dict[str, str]:
    result: dict[str, str] = {}
    if not ENV_PATH.exists():
        return result
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _update_env(updates: dict[str, str]) -> None:
    """更新 .env 中的指定键，保留其它已有键；值为空字符串表示清空该键。"""
    env = _read_env()
    env.update(updates)
    lines = [f"{key}={value}" for key, value in env.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _project_yaml_path(project_id: str) -> Path:
    return get_project_root(project_id) / "project.yaml"


# --- 项目信息 ---------------------------------------------------------------

@app.get("/api/config/project")
def api_get_project_config(project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    data = _read_yaml(_project_yaml_path(project_id))
    return {
        "project_id": project_id,
        "project_name": str(data.get("project_name", "")),
        "timezone": str(data.get("timezone", "Asia/Shanghai")),
        "currency": str(data.get("currency", "USD")),
        "tableau_workbook": str(data.get("tableau_workbook", "")),
    }


@app.post("/api/config/project")
def api_save_project_config(payload: ProjectConfigRequest, project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    data = _read_yaml(_project_yaml_path(project_id))
    data["project_id"] = project_id
    data["project_name"] = payload.project_name.strip() or project_id
    data["timezone"] = payload.timezone.strip() or "Asia/Shanghai"
    data["currency"] = payload.currency.strip() or "USD"
    data["tableau_workbook"] = payload.tableau_workbook.strip()
    _write_yaml(_project_yaml_path(project_id), data)
    return {"ok": True, "config": data}


# --- AI 配置 ----------------------------------------------------------------

@app.get("/api/config/ai")
def api_get_ai_config() -> dict[str, Any]:
    data = _read_yaml(AI_CONFIG_PATH)
    env = _read_env()
    return {
        "use_deepseek": bool(data.get("use_deepseek", AI_DEFAULTS["use_deepseek"])),
        "base_url": str(data.get("base_url", AI_DEFAULTS["base_url"])),
        "model": str(data.get("model", AI_DEFAULTS["model"])),
        "temperature": float(data.get("temperature", AI_DEFAULTS["temperature"])),
        "max_tokens": int(data.get("max_tokens", AI_DEFAULTS["max_tokens"])),
        "fallback_to_rule_template": bool(data.get("fallback_to_rule_template", True)),
        "deepseek_api_key_set": bool(env.get("DEEPSEEK_API_KEY", "").strip()),
    }


@app.post("/api/config/ai")
def api_save_ai_config(payload: AiConfigRequest) -> dict[str, Any]:
    data = _read_yaml(AI_CONFIG_PATH)
    data["use_deepseek"] = payload.use_deepseek
    data["base_url"] = payload.base_url.strip() or AI_DEFAULTS["base_url"]
    data["model"] = payload.model.strip() or AI_DEFAULTS["model"]
    data["temperature"] = payload.temperature
    data["max_tokens"] = payload.max_tokens
    data["fallback_to_rule_template"] = payload.fallback_to_rule_template
    _write_yaml(AI_CONFIG_PATH, data)

    if payload.deepseek_api_key is not None and payload.deepseek_api_key.strip():
        _update_env({"DEEPSEEK_API_KEY": payload.deepseek_api_key.strip()})

    env = _read_env()
    return {"ok": True, "deepseek_api_key_set": bool(env.get("DEEPSEEK_API_KEY", "").strip())}


# --- 指标规则（告警阈值）----------------------------------------------------

@app.get("/api/config/metric-rules")
def api_get_metric_rules() -> dict[str, Any]:
    data = _read_yaml(METRIC_RULES_PATH)
    return {key: float(data.get(key, default)) for key, default in METRIC_RULES_DEFAULTS.items()}


@app.post("/api/config/metric-rules")
def api_save_metric_rules(payload: MetricRulesRequest) -> dict[str, Any]:
    data = {
        "revenue_drop_threshold": payload.revenue_drop_threshold,
        "dau_drop_threshold": payload.dau_drop_threshold,
        "ecpm_drop_threshold": payload.ecpm_drop_threshold,
        "payment_rate_drop_threshold": payload.payment_rate_drop_threshold,
        "retention_drop_point_threshold": payload.retention_drop_point_threshold,
    }
    _write_yaml(METRIC_RULES_PATH, data)
    return {"ok": True, "config": data}


# --- 邮件（收件人 + SMTP）---------------------------------------------------

@app.get("/api/config/email")
def api_get_email_config() -> dict[str, Any]:
    env = _read_env()
    recipients = _read_yaml(RECIPIENTS_PATH)
    cc = recipients.get("cc", [])
    return {
        "smtp_host": env.get("SMTP_HOST", ""),
        "smtp_port": env.get("SMTP_PORT", ""),
        "smtp_user": env.get("SMTP_USER", ""),
        "smtp_password_set": bool(env.get("SMTP_PASSWORD", "").strip()),
        "mail_from": env.get("MAIL_FROM", ""),
        "mail_to": env.get("MAIL_TO", ""),
        "cc": cc if isinstance(cc, list) else [],
    }


@app.post("/api/config/email")
def api_save_email_config(payload: EmailConfigRequest) -> dict[str, Any]:
    updates = {
        "SMTP_HOST": payload.smtp_host.strip(),
        "SMTP_PORT": payload.smtp_port.strip(),
        "SMTP_USER": payload.smtp_user.strip(),
        "MAIL_FROM": payload.mail_from.strip(),
        "MAIL_TO": payload.mail_to.strip(),
    }
    if payload.smtp_password is not None and payload.smtp_password.strip():
        updates["SMTP_PASSWORD"] = payload.smtp_password.strip()
    _update_env(updates)

    to_list = [addr.strip() for addr in payload.mail_to.split(",") if addr.strip()]
    recipients = {"to": to_list, "cc": [c.strip() for c in payload.cc if c.strip()]}
    _write_yaml(RECIPIENTS_PATH, recipients)

    env = _read_env()
    return {"ok": True, "smtp_password_set": bool(env.get("SMTP_PASSWORD", "").strip())}


# --- 数据源 Unity / AppLovin ------------------------------------------------

def _source_view(section: dict[str, Any], default_env: str, env: dict[str, str]) -> dict[str, Any]:
    api_key_env = str(section.get("api_key_env", default_env)) or default_env
    return {
        "enabled": bool(section.get("enabled", False)),
        "api_key_env": api_key_env,
        "api_key_set": bool(env.get(api_key_env, "").strip()),
    }


@app.get("/api/config/sources")
def api_get_sources_config() -> dict[str, Any]:
    data = _read_api_sources()
    env = _read_env()
    unity = data.get("unity", {})
    applovin = data.get("applovin", {})
    return {
        "unity": _source_view(unity if isinstance(unity, dict) else {}, "UNITY_API_KEY", env),
        "applovin": _source_view(applovin if isinstance(applovin, dict) else {}, "APPLOVIN_API_KEY", env),
    }


@app.post("/api/config/sources")
def api_save_sources_config(payload: SourcesConfigRequest) -> dict[str, Any]:
    data = _read_api_sources()
    env_updates: dict[str, str] = {}

    for name, default_env, cfg in (
        ("unity", "UNITY_API_KEY", payload.unity),
        ("applovin", "APPLOVIN_API_KEY", payload.applovin),
    ):
        section = data.get(name, {})
        if not isinstance(section, dict):
            section = {}
        api_key_env = str(section.get("api_key_env", default_env)) or default_env
        section["enabled"] = cfg.enabled
        section["api_key_env"] = api_key_env
        data[name] = section
        if cfg.api_key is not None and cfg.api_key.strip():
            env_updates[api_key_env] = cfg.api_key.strip()

    _write_api_sources(data)
    if env_updates:
        _update_env(env_updates)

    return api_get_sources_config()


# --- 原始 YAML 编辑器（高级）-----------------------------------------------

@app.get("/api/config/raw")
def api_get_raw_config(name: str = Query(...)) -> dict[str, Any]:
    if name not in RAW_CONFIG_FILES:
        raise HTTPException(status_code=400, detail="Unknown config file.")
    path = RAW_CONFIG_FILES[name]
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    return {"name": name, "path": relative_path(path), "content": content, "exists": path.exists()}


@app.post("/api/config/raw")
def api_save_raw_config(payload: RawConfigRequest, name: str = Query(...)) -> dict[str, Any]:
    if name not in RAW_CONFIG_FILES:
        raise HTTPException(status_code=400, detail="Unknown config file.")
    try:
        yaml.safe_load(payload.content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML 解析失败: {exc}") from exc
    path = RAW_CONFIG_FILES[name]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.content, encoding="utf-8", newline="\n")
    return {"ok": True, "name": name, "path": relative_path(path)}


# --- KPI 时间序列（用于 sparkline）-----------------------------------------

@app.get("/api/kpi-series")
def api_kpi_series(project: str = Query(default="default"), days: int = Query(default=14)) -> dict[str, Any]:
    project_id = validate_project_id(project)
    days = max(2, min(days, 90))
    rows = _read_overview_rows(project_id)
    buckets = _aggregate_by_date(rows)
    dates = sorted(buckets.keys())[-days:]
    if not dates:
        return {"ok": False, "dates": [], "series": {}}
    series: dict[str, list[float]] = {}
    for meta in KPI_METRICS:
        key = meta["key"]
        series[key] = [round(_metrics_for(buckets[d]).get(key, 0.0), 4) for d in dates]
    return {"ok": True, "dates": dates, "series": series}


# --- 自动调度（Windows 计划任务）------------------------------------------

SCHEDULE_STATE_PATH = CONFIG_DIR / "schedule.json"
SCHEDULED_BAT = PROJECT_ROOT / "scheduled_daily_report.bat"
MANAGE_SCHEDULE_BAT = PROJECT_ROOT / "manage_schedule.bat"
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _run_schedule_elevated(action: str, project_id: str, run_time: str | None = None) -> tuple[bool, str]:
    """通过 UAC 提权运行 manage_schedule.bat（写入计划任务需要管理员权限）。

    返回 (是否成功, 提示信息)。以提权进程退出码判断 schtasks 是否成功。
    """
    args = [action, project_id]
    if run_time:
        args.append(run_time)
    arg_list = ",".join(f"'{a}'" for a in args)
    ps = (
        f"$p = Start-Process -FilePath '{MANAGE_SCHEDULE_BAT}' "
        f"-ArgumentList {arg_list} -Verb RunAs -WindowStyle Hidden -Wait -PassThru; "
        "exit $p.ExitCode"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"提权执行失败：{exc}"

    if result.returncode == 0:
        return True, ""

    raw = (result.stderr or b"") + (result.stdout or b"")
    text = ""
    for enc in ("mbcs", "gbk", "utf-8"):
        try:
            candidate = raw.decode(enc, errors="strict").strip()
        except (LookupError, ValueError, UnicodeDecodeError):
            continue
        if candidate:
            text = candidate
            break
    # 用户在 UAC 弹窗点了“否/取消”时，Start-Process 会抛错。
    if "取消" in text or "canceled" in text.lower() or "cancelled" in text.lower():
        return False, "已取消授权：注册计划任务需要在弹出的 UAC 窗口中点击“是”。"
    return False, text or f"提权进程返回码 {result.returncode}（可能未通过 UAC 授权）。"


class ScheduleRequest(BaseModel):
    project: str = "default"
    time: str = "08:30"


def _task_name(project_id: str) -> str:
    return f"DailyReportSystem_{project_id}"


def _read_schedule_state() -> dict[str, Any]:
    if SCHEDULE_STATE_PATH.exists():
        try:
            return json.loads(SCHEDULE_STATE_PATH.read_text(encoding="utf-8")) or {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_schedule_state(state: dict[str, Any]) -> None:
    SCHEDULE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _task_exists(task_name: str) -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@app.get("/api/schedule")
def api_get_schedule(project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    task = _task_name(project_id)
    state = _read_schedule_state().get(project_id, {})
    return {
        "ok": True,
        "supported": os.name == "nt",
        "enabled": _task_exists(task),
        "time": state.get("time", "08:30"),
        "task": task,
        "project": project_id,
    }


@app.post("/api/schedule")
def api_set_schedule(payload: ScheduleRequest) -> dict[str, Any]:
    project_id = validate_project_id(payload.project)
    if os.name != "nt":
        raise HTTPException(status_code=400, detail="自动调度仅支持 Windows。")
    run_time = payload.time.strip()
    if not TIME_PATTERN.match(run_time):
        raise HTTPException(status_code=400, detail="时间格式应为 HH:MM（24 小时制）。")
    if not SCHEDULED_BAT.exists():
        raise HTTPException(status_code=500, detail="缺少 scheduled_daily_report.bat。")

    if not MANAGE_SCHEDULE_BAT.exists():
        raise HTTPException(status_code=500, detail="缺少 manage_schedule.bat。")

    task = _task_name(project_id)
    ok, message = _run_schedule_elevated("create", project_id, run_time)
    if not ok and not _task_exists(task):
        raise HTTPException(status_code=500, detail=f"创建计划任务失败：{message}")

    state = _read_schedule_state()
    state[project_id] = {"time": run_time, "task": task}
    _write_schedule_state(state)
    return {"ok": True, "enabled": True, "time": run_time, "task": task, "project": project_id}


@app.delete("/api/schedule")
def api_delete_schedule(project: str = Query(default="default")) -> dict[str, Any]:
    project_id = validate_project_id(project)
    task = _task_name(project_id)
    if os.name == "nt" and _task_exists(task):
        ok, message = _run_schedule_elevated("delete", project_id)
        if not ok and _task_exists(task):
            raise HTTPException(status_code=500, detail=f"删除计划任务失败：{message}")
    state = _read_schedule_state()
    state.pop(project_id, None)
    _write_schedule_state(state)
    return {"ok": True, "enabled": False, "project": project_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
