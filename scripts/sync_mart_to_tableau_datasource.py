"""
将 data/mart 下的 mart CSV 同步到 Tableau 固定数据源目录。

注意：
- 只同步 mart_*.csv，不修改 ai_report_text.csv。
- mart 文件缺失时只打印 warning，不中断流程。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs

MART_DIR = PROJECT_ROOT / "data" / "mart"
TABLEAU_DIR = PROJECT_ROOT / "data" / "tableau_datasource"

MART_FILES = [
    "mart_daily_overview.csv",
    "mart_country_daily.csv",
    "mart_platform_daily.csv",
    "mart_version_daily.csv",
    "mart_ad_placement_daily.csv",
    "mart_campaign_daily.csv",
    "mart_retention_daily.csv",
]


def relative(path: Path) -> str:
    """输出相对项目根目录的路径，方便日志阅读。"""
    return str(path.relative_to(PROJECT_ROOT))


def sync_one(filename: str) -> bool:
    """同步单个 mart CSV，使用 utf-8-sig 写出，方便 Excel/Tableau 读取。"""
    source = MART_DIR / filename
    target = TABLEAU_DIR / filename

    if not source.exists():
        print(f"WARNING: mart file not found, skipped: {relative(source)}")
        return False

    try:
        df = pd.read_csv(source, encoding="utf-8-sig")
    except Exception as exc:
        print(f"WARNING: failed to read {relative(source)}, skipped. Reason: {exc}")
        return False

    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False, encoding="utf-8-sig")
    print(f"OK: {relative(source)} -> {relative(target)} ({len(df)} rows)")
    return True


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Sync mart CSV files to Tableau datasource.")
    add_project_arg(parser)
    return parser.parse_args()


def configure_paths(project_id: str | None) -> None:
    """根据项目 ID 配置 mart/Tableau 数据源路径。"""
    global MART_DIR, TABLEAU_DIR
    paths = ensure_project_dirs(project_id)
    MART_DIR = paths["mart_dir"]
    TABLEAU_DIR = paths["tableau_datasource_dir"]
    print(f"Project: {paths['project_id']}")
    print(f"Mart dir: {MART_DIR}")
    print(f"Tableau datasource dir: {TABLEAU_DIR}")


def main() -> None:
    """主入口：同步所有已支持的 mart 文件。"""
    args = parse_args()
    configure_paths(args.project)

    print("Start syncing mart CSV files to Tableau datasource...")
    print("ai_report_text.csv will not be modified by this script.")

    ok_count = 0
    for filename in MART_FILES:
        if sync_one(filename):
            ok_count += 1

    print(f"Done. Synced {ok_count}/{len(MART_FILES)} mart files.")


if __name__ == "__main__":
    main()
