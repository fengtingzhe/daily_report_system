"""
一次性拉取所有平台数据的聚合入口。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch.fetch_unity import fetch_unity_data
from scripts.fetch.fetch_applovin import fetch_applovin_data
from scripts.fetch.fetch_ga4 import fetch_ga4_data


def fetch_all(report_date: str) -> dict:
    """拉取所有平台数据，返回各平台输出文件路径的字典。"""
    results = {}
    results["unity"] = fetch_unity_data(report_date)
    results["applovin"] = fetch_applovin_data(report_date)
    results["ga4"] = fetch_ga4_data(report_date)
    return results


if __name__ == "__main__":
    fetch_all("2025-01-01")
