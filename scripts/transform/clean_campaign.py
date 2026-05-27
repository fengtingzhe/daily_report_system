"""
投放数据清洗模块。
将原始投放数据标准化为统一格式。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def clean_campaign(input_dir: Path | None = None, output_dir: Path | None = None) -> Path | None:
    """清洗投放原始数据：统一字段、CPI 计算、ROAS 计算、去重。"""
    if input_dir is None:
        input_dir = PROJECT_ROOT / "data" / "raw"
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "clean" / "campaign_daily"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 实现投放数据清洗逻辑
    print(f"[clean_campaign] 正在清洗投放数据，输入: {input_dir}, 输出: {output_dir}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    clean_campaign()
