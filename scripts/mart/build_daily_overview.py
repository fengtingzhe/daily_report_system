"""
构建日概览业务宽表。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def build_daily_overview(report_date: str, output_dir: Path | None = None) -> Path | None:
    """构建每日概览宽表：合并营收、用户、广告数据。"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "mart" / "mart_daily_overview"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 从 clean 目录读取清洗数据，按 report_date 聚合为日概览宽表
    print(f"[build_daily_overview] 正在构建日概览宽表，日期: {report_date}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    build_daily_overview("2025-01-01")
