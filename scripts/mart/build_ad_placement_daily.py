"""
构建广告位维度业务宽表。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def build_ad_placement_daily(report_date: str, output_dir: Path | None = None) -> Path | None:
    """构建广告位×平台×国家日维度宽表。"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "mart" / "mart_ad_placement_daily"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 从 clean 目录读取数据，按 ad_placement + platform + country 聚合
    print(f"[build_ad_placement_daily] 正在构建广告位维度宽表，日期: {report_date}")
    return None


if __name__ == "__main__":
    build_ad_placement_daily("2025-01-01")
