"""
检查 reports/pdf/ 下是否已有 Tableau 导出的 PDF。

本脚本只做检查，不自动生成 PDF。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs

PDF_DIR = PROJECT_ROOT / "reports" / "pdf"


def relative(path: Path) -> str:
    """输出相对项目根目录的路径。"""
    return str(path.relative_to(PROJECT_ROOT))


def main() -> None:
    """查找最新 PDF 并打印信息。"""
    parser = argparse.ArgumentParser(description="Check latest PDF output.")
    add_project_arg(parser)
    args = parser.parse_args()

    global PDF_DIR
    paths = ensure_project_dirs(args.project)
    PDF_DIR = paths["pdf_dir"]

    print("Checking PDF output...")
    print(f"Project: {paths['project_id']}")
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PDF_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not pdf_files:
        print(f"No PDF found under {relative(PDF_DIR)}.")
        print("Please export the Tableau report PDF manually into reports/pdf/ first.")
        return

    latest = pdf_files[0]
    stat = latest.stat()
    size_mb = stat.st_size / 1024 / 1024
    modified_at = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    print(f"Latest PDF: {relative(latest)}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Modified at: {modified_at}")


if __name__ == "__main__":
    main()
