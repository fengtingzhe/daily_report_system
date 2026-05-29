"""
游戏运营日报自动化系统 —— 主流程脚本。
按顺序调用子脚本，串联当前已完成的最小流程：
  1. 生成 Tableau 测试数据
  2. 生成 AI 上下文 JSON
  3. 生成 AI 日报草稿并写回 Tableau CSV
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.log_utils import setup_logger

# 初始化日志记录器
logger = setup_logger(log_dir=PROJECT_ROOT / "logs", log_name="run")

# Python 解释器路径（优先使用当前运行的解释器）
PYTHON_EXE = sys.executable


def run_script(script_path: Path, step_name: str, project_id: str) -> None:
    """
    使用 subprocess 运行子脚本。
    步骤名用于日志打印；若子进程返回非 0 退出码，抛出 RuntimeError。
    """
    logger.info(f"========== {step_name} ==========")
    logger.info(f"脚本路径: {script_path}")

    result = subprocess.run(
        [PYTHON_EXE, str(script_path), "--project", project_id],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        },
    )

    # 将子进程输出打印到控制台和日志
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            logger.info(f"  | {line}")

    if result.returncode != 0:
        # 打印 stderr 并抛出异常
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                logger.error(f"  | {line}")
        raise RuntimeError(
            f"'{step_name}' 执行失败，退出码: {result.returncode}"
        )

    logger.info(f"'{step_name}' 执行成功。")


def main() -> None:
    """执行完整的日报最小流程。"""
    parser = argparse.ArgumentParser(description="Run test daily report pipeline (synthetic data).")
    parser.add_argument(
        "--project",
        default="demo",
        help="Project ID for test data. Default: demo (isolated from real projects)",
    )
    args = parser.parse_args()
    project_id = args.project

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"日报流程开始，时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"项目: {project_id}")
    logger.info(f"Python 解释器: {PYTHON_EXE}")
    logger.info("=" * 60)

    # 定义流程步骤（脚本相对路径, 步骤名称）
    steps = [
        ("scripts/build_test_data.py",       "步骤1：生成 Tableau 测试数据"),
        ("scripts/generate_ai_context.py",   "步骤2：生成 AI 上下文"),
        ("scripts/generate_ai_report.py",    "步骤3：生成 AI 日报草稿"),
    ]

    try:
        for rel_path, name in steps:
            script_path = PROJECT_ROOT / rel_path
            run_script(script_path, name, project_id)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"日报流程全部完成，耗时: {elapsed:.1f} 秒")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"日报流程执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
