"""
一次性构建所有业务宽表的聚合入口。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.mart.build_daily_overview import build_daily_overview
from scripts.mart.build_country_daily import build_country_daily
from scripts.mart.build_platform_daily import build_platform_daily
from scripts.mart.build_version_daily import build_version_daily
from scripts.mart.build_ad_placement_daily import build_ad_placement_daily
from scripts.mart.build_campaign_daily import build_campaign_daily
from scripts.mart.build_retention_daily import build_retention_daily
from scripts.mart.build_ai_context import build_ai_context


def build_all_marts(report_date: str) -> dict:
    """构建所有业务宽表，返回各宽表输出文件路径的字典。"""
    results = {}
    results["daily_overview"] = build_daily_overview(report_date)
    results["country_daily"] = build_country_daily(report_date)
    results["platform_daily"] = build_platform_daily(report_date)
    results["version_daily"] = build_version_daily(report_date)
    results["ad_placement_daily"] = build_ad_placement_daily(report_date)
    results["campaign_daily"] = build_campaign_daily(report_date)
    results["retention_daily"] = build_retention_daily(report_date)
    results["ai_context"] = build_ai_context(report_date)
    return results


if __name__ == "__main__":
    build_all_marts("2025-01-01")
