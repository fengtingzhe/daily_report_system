"""
广告数据清洗模块。
将原始广告变现数据标准化为统一格式。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def clean_ad(input_dir: Path | None = None, output_dir: Path | None = None) -> Path | None:
    """清洗广告原始数据：统一字段、eCPM 换算、填充率计算、去重。"""
    if input_dir is None:
        input_dir = PROJECT_ROOT / "data" / "raw"
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "clean" / "ad_daily"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 实现广告数据清洗逻辑
    print(f"[clean_ad] 正在清洗广告数据，输入: {input_dir}, 输出: {output_dir}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    clean_ad()
