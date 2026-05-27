"""
AI 日报草稿生成模块。
根据数据摘要、异常列表、人工备注，生成正式运营日报的初稿文字。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_report_draft(context_path: Path | None = None, output_dir: Path | None = None) -> Path | None:
    """读取 AI 上下文和预分析结果，调用 LLM 生成日报初稿。"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "ai" / "draft"
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = PROJECT_ROOT / "scripts" / "ai" / "prompts" / "report_draft_prompt.md"
    # TODO: 加载提示词模板，拼接上下文和预分析，调用 AI API 生成初稿
    print(f"[generate_report_draft] 正在生成日报初稿，提示词: {prompt_path}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    generate_report_draft()
