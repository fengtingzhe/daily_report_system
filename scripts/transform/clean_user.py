"""
用户数据清洗模块。
将原始用户行为数据标准化为统一格式。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def clean_user(input_dir: Path | None = None, output_dir: Path | None = None) -> Path | None:
    """清洗用户原始数据：统一字段、时区转换、去重。"""
    if input_dir is None:
        input_dir = PROJECT_ROOT / "data" / "raw"
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "clean" / "user_daily"
    output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: 实现用户数据清洗逻辑
    print(f"[clean_user] 正在清洗用户数据，输入: {input_dir}, 输出: {output_dir}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    clean_user()
