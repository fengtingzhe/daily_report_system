"""
检查 reports/pdf/ 下是否已有 Tableau 导出的 PDF。

本脚本只做检查，不自动生成 PDF。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "reports" / "pdf"


def relative(path: Path) -> str:
    """输出相对项目根目录的路径。"""
    return str(path.relative_to(PROJECT_ROOT))


def main() -> None:
    """查找最新 PDF 并打印信息。"""
    print("Checking PDF output...")
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
