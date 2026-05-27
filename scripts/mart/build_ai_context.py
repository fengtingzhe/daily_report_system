"""
构建 AI 可读的数据上下文摘要（JSON 格式）。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def build_ai_context(report_date: str, output_dir: Path | None = None) -> Path | None:
    """从各业务宽表中提取关键指标，汇总为 AI 可读的 daily_ai_context.json。"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "mart" / "mart_ai_summary"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 读取 mart 宽表，提取摘要指标，写入 JSON 文件
    print(f"[build_ai_context] 正在构建 AI 上下文摘要，日期: {report_date}")
    return None


if __name__ == "__main__":
    build_ai_context("2025-01-01")
