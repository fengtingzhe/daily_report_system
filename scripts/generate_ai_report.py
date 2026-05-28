"""
AI 日报草稿生成脚本。

默认使用本地规则模板生成日报文字；当 config/ai_report.yaml 中 use_deepseek=true，
且 .env 中存在 DEEPSEEK_API_KEY 时，优先调用 DeepSeek API。
如果 API 调用失败，会自动回退到规则模板，保证日报流程不中断。
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv


# ============================================================
# 路径常量
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTEXT_PATH = PROJECT_ROOT / "ai" / "context" / "daily_ai_context.json"
MARKDOWN_OUTPUT = PROJECT_ROOT / "ai" / "draft" / "daily_report_draft.md"
TABLEAU_CSV = PROJECT_ROOT / "data" / "tableau_datasource" / "ai_report_text.csv"
CONFIG_PATH = PROJECT_ROOT / "config" / "ai_report.yaml"
ENV_PATH = PROJECT_ROOT / ".env"


CSV_HEADER = ["report_date", "project", "section", "display_order", "analysis_text"]
SECTION_DEFS = [
    ("核心结论", 1),
    ("整体表现", 2),
    ("收入与用户分析", 3),
    ("广告位与平台分析", 4),
    ("今日建议", 5),
]

DEFAULT_CONFIG = {
    "use_deepseek": False,
    "base_url": "https://api.deepseek.com/chat/completions",
    "model": "deepseek-chat",
    "temperature": 0.3,
    "max_tokens": 2000,
    "fallback_to_rule_template": True,
}


def relative(path: Path) -> str:
    """输出相对项目根目录的路径，方便日志阅读。"""
    return str(path.relative_to(PROJECT_ROOT))


def load_config() -> dict[str, Any]:
    """读取 AI 配置；配置缺失时使用默认值。"""
    if not CONFIG_PATH.exists():
        print(f"WARNING: 找不到 {relative(CONFIG_PATH)}，使用默认规则模板配置。")
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config = DEFAULT_CONFIG.copy()
    config.update(data)
    return config


def load_context() -> dict[str, Any]:
    """读取 daily_ai_context.json。"""
    if not CONTEXT_PATH.exists():
        raise FileNotFoundError(
            f"找不到 AI 上下文文件: {relative(CONTEXT_PATH)}，"
            "请先运行 scripts/generate_ai_context.py。"
        )
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_money(value: Any) -> str:
    """格式化金额。"""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def fmt_int(value: Any) -> str:
    """格式化整数。"""
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "0"


def fmt_pct(value: Any, *, point_change: bool = False) -> str:
    """格式化百分比或百分点变化。"""
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    sign = "+" if number >= 0 else ""
    suffix = "pp" if point_change else "%"
    return f"{sign}{number * 100:.1f}{suffix}"


def safe_get(mapping: dict[str, Any], key: str, default: Any = 0) -> Any:
    """从字典中安全取值。"""
    value = mapping.get(key, default)
    return default if value is None else value


def build_rule_sections(ctx: dict[str, Any]) -> dict[str, str]:
    """用本地规则模板生成 5 段日报文字。"""
    overview = ctx.get("overview", {})
    current = overview.get("current", {})
    change = overview.get("change", {})
    alerts = ctx.get("alerts", [])
    country_top = ctx.get("country_top", [])
    platform_summary = ctx.get("platform_summary", [])
    ad_top = ctx.get("ad_placement_top", [])

    revenue = safe_get(current, "revenue", 0)
    ad_revenue = safe_get(current, "ad_revenue", 0)
    iap_revenue = safe_get(current, "iap_revenue", 0)
    dau = safe_get(current, "dau", 0)
    new_users = safe_get(current, "new_users", 0)

    if alerts:
        alert_text = "；".join(str(item.get("message", "")) for item in alerts)
        core_judgement = f"今日存在需要关注的异常：{alert_text}。"
    elif change.get("revenue") is not None and float(change.get("revenue", 0)) > 0:
        core_judgement = "今日收入环比增长，整体经营表现偏正向。"
    else:
        core_judgement = "今日核心指标整体平稳，暂未发现明显异常。"

    top_country_text = "暂无国家维度数据。"
    if country_top:
        top = country_top[0]
        top_country_text = (
            f"收入最高的国家/平台组合为 {top.get('country', 'unknown')} / "
            f"{top.get('platform', 'unknown')}，收入 {fmt_money(top.get('revenue'))}，"
            f"DAU {fmt_int(top.get('dau'))}。"
        )

    platform_text = "暂无平台维度数据。"
    if platform_summary:
        parts = [
            f"{item.get('platform', 'unknown')}: DAU {fmt_int(item.get('dau'))}, "
            f"收入 {fmt_money(item.get('revenue'))}"
            for item in platform_summary
        ]
        platform_text = "；".join(parts) + "。"

    ad_text = "暂无广告位维度数据。"
    if ad_top:
        ad = ad_top[0]
        ad_text = (
            f"广告收入最高的广告位为 {ad.get('ad_placement', 'unknown')}，"
            f"广告网络 {ad.get('ad_network', 'unknown')}，"
            f"收入 {fmt_money(ad.get('revenue'))}，"
            f"展示 {fmt_int(ad.get('impressions'))}，eCPM {fmt_money(ad.get('ecpm'))}。"
        )

    return {
        "核心结论": (
            f"{core_judgement} 报告日期 {ctx.get('report_date', 'unknown')}，"
            f"总收入 {fmt_money(revenue)}，DAU {fmt_int(dau)}，"
            f"收入环比 {fmt_pct(change.get('revenue'))}。"
        ),
        "整体表现": (
            f"今日 DAU {fmt_int(dau)}，新增用户 {fmt_int(new_users)}；"
            f"总收入 {fmt_money(revenue)}，其中广告收入 {fmt_money(ad_revenue)}，"
            f"IAP 收入 {fmt_money(iap_revenue)}。"
            f"ARPDAU {fmt_money(current.get('arpdau', 0))}，"
            f"展示量 {fmt_int(current.get('impressions', 0))}。"
        ),
        "收入与用户分析": (
            f"收入结构上，广告收入占比 "
            f"{(float(ad_revenue) / float(revenue) * 100) if float(revenue or 0) else 0:.1f}%，"
            f"IAP 收入占比 "
            f"{(float(iap_revenue) / float(revenue) * 100) if float(revenue or 0) else 0:.1f}%。"
            f"{top_country_text}"
        ),
        "广告位与平台分析": (
            f"{platform_text} {ad_text}"
        ),
        "今日建议": (
            "建议继续在 Tableau 中查看国家、平台、广告位三个维度的明细趋势；"
            "如收入或 DAU 连续两天回落，应优先排查投放、版本更新和广告填充率。"
        ),
    }


def build_deepseek_prompt(ctx: dict[str, Any]) -> str:
    """构造 DeepSeek 提示词，要求返回稳定 JSON。"""
    compact_context = json.dumps(ctx, ensure_ascii=False, indent=2)
    section_names = [name for name, _ in SECTION_DEFS]
    return (
        "你是游戏运营数据分析师。请根据下面的日报上下文生成中文运营日报分析。\n"
        "要求：\n"
        "1. 只返回 JSON 对象，不要 Markdown 代码块。\n"
        "2. JSON key 必须严格为："
        f"{', '.join(section_names)}。\n"
        "3. 每个 value 是一段简洁、可放入日报的中文分析文字。\n"
        "4. 不要编造上下文中没有的数据。\n\n"
        f"日报上下文：\n{compact_context}"
    )


def parse_deepseek_sections(content: str) -> dict[str, str]:
    """解析 DeepSeek 返回的 JSON；解析失败时抛出异常供上层回退。"""
    text = content.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("DeepSeek 返回内容不是 JSON 对象。")

    sections: dict[str, str] = {}
    for section_name, _ in SECTION_DEFS:
        value = data.get(section_name)
        if not value:
            raise ValueError(f"DeepSeek 返回缺少 section: {section_name}")
        sections[section_name] = str(value)
    return sections


def generate_with_deepseek(ctx: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    """调用 DeepSeek API 生成日报 sections。"""
    load_dotenv(ENV_PATH)
    import os

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY。")

    payload = {
        "model": config["model"],
        "temperature": float(config["temperature"]),
        "max_tokens": int(config["max_tokens"]),
        "messages": [
            {"role": "system", "content": "你是资深游戏运营数据分析师。"},
            {"role": "user", "content": build_deepseek_prompt(ctx)},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        str(config["base_url"]),
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return parse_deepseek_sections(content)


def write_markdown_report(sections: dict[str, str], ctx: dict[str, Any]) -> None:
    """写出 Markdown 日报草稿。"""
    MARKDOWN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {ctx.get('project', '项目A')} 运营日报草稿 - {ctx.get('report_date', 'unknown')}",
        "",
        f"> 自动生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 对比日期：{ctx.get('previous_date', 'N/A')}",
        "",
    ]
    for section_name, _ in SECTION_DEFS:
        lines.extend([f"## {section_name}", "", sections[section_name], ""])

    with open(MARKDOWN_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_tableau_text_csv(sections: dict[str, str], ctx: dict[str, Any]) -> None:
    """写出 Tableau 可读取的 AI 文本 CSV，字段保持不变。"""
    TABLEAU_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(TABLEAU_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for section_name, display_order in SECTION_DEFS:
            writer.writerow({
                "report_date": ctx.get("report_date", ""),
                "project": ctx.get("project", "项目A"),
                "section": section_name,
                "display_order": display_order,
                "analysis_text": sections[section_name],
            })


def main() -> None:
    """主入口：生成 AI 日报草稿和 Tableau 文本 CSV。"""
    print("开始生成日报草稿...")
    print("  [1/3] 加载 daily_ai_context.json ...")
    ctx = load_context()
    print(f"        报告日期: {ctx.get('report_date', 'unknown')}")

    print("  [2/3] 生成分析文字...")
    config = load_config()
    sections: dict[str, str]

    if config.get("use_deepseek"):
        try:
            print("        DeepSeek 已开启，尝试调用 API ...")
            sections = generate_with_deepseek(ctx, config)
            print("        DeepSeek 生成成功。")
        except Exception as exc:
            if config.get("fallback_to_rule_template", True):
                print(f"WARNING: DeepSeek 调用失败，回退到规则模板。原因: {exc}")
                sections = build_rule_sections(ctx)
            else:
                raise
    else:
        print("        DeepSeek 未开启，使用规则模板。")
        sections = build_rule_sections(ctx)

    print("  [3/3] 写入输出文件...")
    write_markdown_report(sections, ctx)
    write_tableau_text_csv(sections, ctx)

    print("")
    print("日报草稿生成完成。")
    print(f"Markdown 草稿: {MARKDOWN_OUTPUT}")
    print(f"Tableau CSV:   {TABLEAU_CSV}")


if __name__ == "__main__":
    main()
