"""
为 Tableau 生成 AI 分析文本。
将 AI 生成的日报分析文字按 section 写入 ai_report_text.csv，供 Tableau 仪表板直接展示。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def write_ai_text_for_tableau(report_date: str, output_path: Path | None = None) -> Path | None:
    """从最终分析文本中提取各 section，写入 Tableau 数据源 CSV。"""
    if output_path is None:
        output_path = PROJECT_ROOT / "data" / "tableau_datasource" / "ai_report_text.csv"
    # TODO: 从 ai/final_text/ 目录读取最终文本，按 section 写入 CSV
    print(f"[write_ai_text_for_tableau] 正在写入 Tableau AI 文本，日期: {report_date}, 输出: {output_path}")
    return output_path


if __name__ == "__main__":
    write_ai_text_for_tableau("2025-01-01")
