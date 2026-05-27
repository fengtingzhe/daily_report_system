"""
Google Analytics 4 平台数据拉取模块。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def fetch_ga4_data(report_date: str, output_dir: Path | None = None) -> Path | None:
    """从 Google Analytics Data API (GA4) 拉取指定日期的用户行为数据。"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "raw" / "ga4"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 实现 GA4 Data API 调用逻辑，将结果写入 output_dir 下的 CSV 文件
    print(f"[fetch_ga4] 正在拉取 GA4 数据，日期: {report_date}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    fetch_ga4_data("2025-01-01")
