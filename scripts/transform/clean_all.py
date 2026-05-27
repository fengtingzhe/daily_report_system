"""
一次性清洗所有模块数据的聚合入口。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.transform.clean_revenue import clean_revenue
from scripts.transform.clean_user import clean_user
from scripts.transform.clean_ad import clean_ad
from scripts.transform.clean_campaign import clean_campaign


def clean_all(input_dir: Path | None = None) -> dict:
    """清洗所有模块原始数据，返回各模块输出文件路径的字典。"""
    results = {}
    results["revenue"] = clean_revenue(input_dir=input_dir)
    results["user"] = clean_user(input_dir=input_dir)
    results["ad"] = clean_ad(input_dir=input_dir)
    results["campaign"] = clean_campaign(input_dir=input_dir)
    return results


if __name__ == "__main__":
    clean_all()
