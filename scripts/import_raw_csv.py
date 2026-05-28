"""
真实 CSV 原始数据导入脚本。
扫描 data/raw/ 下的各平台 CSV 文件，执行字段名清洗、编码转换，
并输出到 data/clean/ 对应目录。每行追加 source_platform、source_file、
imported_at 三个元信息字段。

运行方式：
    python scripts/import_raw_csv.py
"""

import csv
import argparse
import re
import sys
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs

# ============================================================
# 默认路径常量；main() 会根据 --project 覆盖。
# ============================================================
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"

# 支持的平台列表（与 raw 子目录名一致）
PLATFORMS = ["unity", "applovin", "ga4"]

# 尝试的编码顺序
ENCODINGS = ["utf-8-sig", "utf-8", "gbk"]


def clean_field_name(name: str) -> str:
    """
    清洗单个字段名：
    1. 去除 BOM 字符
    2. 去除前后空格
    3. 英文字段统一转小写
    4. 空格、横线、斜杠、括号、冒号等替换为下划线
    5. 多个连续下划线合并为一个
    6. 去除字段名前后下划线
    返回清洗后的字段名。
    """
    # 去除 BOM（﻿）
    name = name.replace("﻿", "").replace("﻿", "")
    # 去除前后空格
    name = name.strip()
    # 统一转小写
    name = name.lower()
    # 将非字母数字的字符替换为下划线（保留中文字符和字母数字）
    # 一-鿿 是中文字符范围
    name = re.sub(r"[^\w一-鿿]", "_", name)
    # 多个连续下划线合并为一个
    name = re.sub(r"_+", "_", name)
    # 去除前后下划线
    name = name.strip("_")
    return name


def deduplicate_field_names(names: list[str]) -> list[str]:
    """
    处理重复字段名。
    如果多个字段清洗后同名，自动加后缀 _1, _2, ...。
    第一个保留原名，从第二个开始依次加后缀。
    返回去重后的字段名列表。
    """
    seen: dict[str, int] = {}
    result: list[str] = []
    for name in names:
        if name not in seen:
            seen[name] = 1
            result.append(name)
        else:
            suffix = seen[name]
            new_name = f"{name}_{suffix}"
            # 如果加了后缀还是冲突，继续递增
            while new_name in seen:
                suffix += 1
                new_name = f"{name}_{suffix}"
            seen[name] = suffix + 1
            seen[new_name] = 1
            result.append(new_name)
    return result


def read_csv_with_encoding(file_path: Path) -> tuple[list[str], list[list[str]]]:
    """
    尝试多种编码读取 CSV 文件。
    返回 (header, rows) 元组，header 为原始字段名列表。
    如果所有编码都失败，抛出 ValueError。
    """
    for enc in ENCODINGS:
        try:
            with open(file_path, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                raise ValueError(f"CSV 文件为空: {file_path}")
            header = rows[0]
            data_rows = rows[1:]
            return header, data_rows
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            # 其他错误直接抛出
            raise ValueError(f"读取 CSV 失败 {file_path}: {e}") from e

    raise ValueError(
        f"无法解码 CSV 文件 {file_path.name}，"
        f"已尝试编码: {', '.join(ENCODINGS)}"
    )


def process_platform(platform: str, raw_platform_dir: Path, clean_platform_dir: Path) -> dict:
    """
    处理单个平台的所有 CSV 文件。
    返回统计信息字典。
    """
    result = {
        "platform": platform,
        "files_found": 0,
        "files_ok": 0,
        "files_failed": 0,
        "total_rows": 0,
        "errors": [],
    }

    # 确保 raw 目录存在
    if not raw_platform_dir.exists():
        print(f"[{platform}] raw 目录不存在: {raw_platform_dir}")
        return result

    # 扫描 CSV 文件
    csv_files = sorted(raw_platform_dir.glob("*.csv"))
    result["files_found"] = len(csv_files)

    if not csv_files:
        print(f"[{platform}] 未发现 CSV 文件")
        return result

    print(f"[{platform}] 发现 {len(csv_files)} 个 CSV 文件")

    # 确保 clean 输出目录存在
    clean_platform_dir.mkdir(parents=True, exist_ok=True)

    for csv_path in csv_files:
        try:
            # 读取原始 CSV
            raw_header, raw_rows = read_csv_with_encoding(csv_path)

            # 清洗字段名
            cleaned_header = [clean_field_name(h) for h in raw_header]
            # 去重
            cleaned_header = deduplicate_field_names(cleaned_header)

            # 添加元信息字段
            cleaned_header.extend(["source_platform", "source_file", "imported_at"])
            import_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 为每行追加元信息
            output_rows = []
            for row in raw_rows:
                # 补齐长度（处理可能存在的字段数不一致问题）
                padded_row = row + [""] * (len(raw_header) - len(row))
                padded_row = padded_row[:len(raw_header)]
                padded_row.extend([platform, csv_path.name, import_time])
                output_rows.append(padded_row)

            # 写入 clean CSV
            output_path = clean_platform_dir / csv_path.name
            with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(cleaned_header)
                writer.writerows(output_rows)

            row_count = len(output_rows)
            result["files_ok"] += 1
            result["total_rows"] += row_count
            print(f"  OK: {csv_path.name} -> {output_path}，{row_count} rows")

        except Exception as e:
            result["files_failed"] += 1
            result["errors"].append(f"{csv_path.name}: {e}")
            print(f"  FAIL: {csv_path.name} —— {e}")

    return result


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Import raw CSV files into clean layer.")
    add_project_arg(parser)
    return parser.parse_args()


def configure_paths(project_id: str | None) -> None:
    """根据项目 ID 配置 raw/clean 路径。"""
    global RAW_DIR, CLEAN_DIR
    paths = ensure_project_dirs(project_id)
    RAW_DIR = paths["raw_dir"]
    CLEAN_DIR = paths["clean_dir"]
    print(f"Project: {paths['project_id']}")
    print(f"Raw dir: {RAW_DIR}")
    print(f"Clean dir: {CLEAN_DIR}")


def main() -> None:
    """主入口：遍历所有平台，导入原始 CSV 文件。"""
    args = parse_args()
    configure_paths(args.project)

    print("开始导入真实 CSV...")
    print()

    all_results: list[dict] = []
    total_ok = 0
    total_rows = 0

    for platform in PLATFORMS:
        raw_platform_dir = RAW_DIR / platform
        clean_platform_dir = CLEAN_DIR / platform
        result = process_platform(platform, raw_platform_dir, clean_platform_dir)
        all_results.append(result)
        total_ok += result["files_ok"]
        total_rows += result["total_rows"]

    # 打印汇总
    print()
    print(f"导入完成。成功: {total_ok} 个文件，失败: "
          f"{sum(r['files_failed'] for r in all_results)} 个文件，"
          f"共 {total_rows} 行数据。")


if __name__ == "__main__":
    main()
