"""
AppLovin 平台数据拉取模块。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def fetch_applovin_data(report_date: str, output_dir: Path | None = None) -> Path | None:
    """从 AppLovin API 拉取指定日期的广告收入与展示数据。"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "raw" / "applovin"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 实现 AppLovin API 调用逻辑，将结果写入 output_dir 下的 CSV 文件
    print(f"[fetch_applovin] 正在拉取 AppLovin 数据，日期: {report_date}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    fetch_applovin_data("2025-01-01")
