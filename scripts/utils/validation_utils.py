"""
数据校验工具模块。
提供数据完整性、异常阈值检测等校验函数。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_csv_not_empty(file_path: Path) -> bool:
    """校验 CSV 文件是否存在且非空。"""
    if not file_path.exists():
        return False
    with open(file_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    # 至少要有表头 + 一行数据
    return len(lines) >= 2


def check_metric_threshold(value: float, threshold: float, metric_name: str = "") -> tuple[bool, str]:
    """检查指标是否超过阈值，返回 (是否异常, 异常描述)。"""
    if value < threshold:
        msg = f"[异常] {metric_name}: {value:.2%} < 阈值 {threshold:.2%}"
        return True, msg
    return False, ""
