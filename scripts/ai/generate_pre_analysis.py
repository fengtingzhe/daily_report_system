"""
AI 预分析生成模块。
在打开 Tableau 之前，让 AI 基于上下文数据生成"今日预分析"，
提醒我重点看哪些图表和指标。
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_pre_analysis(context_path: Path | None = None, output_dir: Path | None = None) -> Path | None:
    """读取 AI 上下文 JSON，调用 LLM 生成今日预分析文本。"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "ai" / "pre_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = PROJECT_ROOT / "scripts" / "ai" / "prompts" / "pre_analysis_prompt.md"
    # TODO: 加载提示词模板，拼接上下文数据，调用 AI API 生成分析文本
    print(f"[generate_pre_analysis] 正在生成今日预分析，提示词: {prompt_path}")
    return None  # 占位：返回输出文件路径


if __name__ == "__main__":
    generate_pre_analysis()
