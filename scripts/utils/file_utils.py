"""
文件工具模块。
提供安全的文件读写、CSV 检测、目录管理等通用操作。
"""

from pathlib import Path
import csv


def safe_read_csv(file_path: Path) -> list[dict] | None:
    """安全读取 CSV 文件，文件不存在或为空时返回 None。"""
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows if rows else None


def safe_write_csv(file_path: Path, headers: list[str], rows: list[dict]) -> None:
    """安全写入 CSV 文件，自动创建父目录。"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def ensure_dir(dir_path: Path) -> Path:
    """确保目录存在，不存在则创建。"""
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path
