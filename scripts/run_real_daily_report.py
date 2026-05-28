"""
真实日报流程入口。

串联 raw -> clean -> mart -> Tableau datasource -> AI context -> AI report。
现有 scripts/run_all.py 仍保留为测试数据流程，本脚本不替代测试流程。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PYTHON_EXE = sys.executable


STEPS = [
    ("scripts/import_raw_csv.py", "Step 1: import raw CSV to clean"),
    ("scripts/build_mart_from_clean.py", "Step 2: build mart from clean"),
    ("scripts/sync_mart_to_tableau_datasource.py", "Step 3: sync mart to Tableau datasource"),
    ("scripts/generate_ai_context.py", "Step 4: generate AI context"),
    ("scripts/generate_ai_report.py", "Step 5: generate AI report text"),
]


def write_log(log_file: Path, message: str) -> None:
    """同时写入日志文件和控制台。"""
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def run_step(script_rel_path: str, step_name: str, log_file: Path, project_id: str) -> None:
    """运行单个子脚本；失败时抛出异常并停止真实流程。"""
    script_path = PROJECT_ROOT / script_rel_path
    write_log(log_file, "=" * 60)
    write_log(log_file, step_name)
    write_log(log_file, f"Script: {script_rel_path}")

    result = subprocess.run(
        [PYTHON_EXE, str(script_path), "--project", project_id],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        },
    )

    if result.stdout:
        for line in result.stdout.strip().splitlines():
            write_log(log_file, f"  | {line}")

    if result.stderr:
        for line in result.stderr.strip().splitlines():
            write_log(log_file, f"  ! {line}")

    if result.returncode != 0:
        raise RuntimeError(f"{step_name} failed with exit code {result.returncode}")

    write_log(log_file, f"OK: {step_name}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Run real daily report pipeline.")
    add_project_arg(parser)
    return parser.parse_args()


def main() -> None:
    """执行真实日报流程。"""
    args = parse_args()
    paths = ensure_project_dirs(args.project)
    project_id = paths["project_id"]
    log_dir = paths["logs_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now()
    log_file = log_dir / f"real_daily_report_{started_at.strftime('%Y%m%d_%H%M%S')}.log"

    write_log(log_file, "Real daily report pipeline started.")
    write_log(log_file, f"Project: {project_id}")
    write_log(log_file, f"Project root: {paths['project_root']}")
    write_log(log_file, f"Start time: {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    write_log(log_file, f"Python: {PYTHON_EXE}")

    try:
        for script_rel_path, step_name in STEPS:
            run_step(script_rel_path, step_name, log_file, project_id)
    except Exception as exc:
        write_log(log_file, "")
        write_log(log_file, f"FAILED: {exc}")
        write_log(log_file, f"Log file: {log_file}")
        sys.exit(1)

    elapsed = (datetime.now() - started_at).total_seconds()
    write_log(log_file, "")
    write_log(log_file, f"SUCCESS: Real daily report pipeline completed in {elapsed:.1f} seconds.")
    write_log(log_file, f"Log file: {log_file}")


if __name__ == "__main__":
    main()
