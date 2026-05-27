"""
日期工具模块。
提供日报流程中常用的日期计算函数。
"""

from datetime import datetime, timedelta
from pathlib import Path


def get_report_date(default: str = "yesterday") -> str:
    """获取默认的报表日期，默认为昨天。"""
    if default == "yesterday":
        return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif default == "today":
        return datetime.now().strftime("%Y-%m-%d")
    else:
        return default


def date_to_str(dt: datetime) -> str:
    """将 datetime 对象转为 YYYY-MM-DD 字符串。"""
    return dt.strftime("%Y-%m-%d")


def str_to_date(date_str: str) -> datetime:
    """将 YYYY-MM-DD 字符串转为 datetime 对象。"""
    return datetime.strptime(date_str, "%Y-%m-%d")
