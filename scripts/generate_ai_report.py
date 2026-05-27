"""
日报草稿生成脚本（规则模板版）。
读取 daily_ai_context.json，基于规则模板生成运营日报文字，
输出 Markdown 草稿和 Tableau 可读取的 ai_report_text.csv。
暂时不接 DeepSeek API，使用规则模板模拟 AI 分析。
"""

import json
import csv
from pathlib import Path

# ============================================================
# 路径常量
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTEXT_PATH = PROJECT_ROOT / "ai" / "context" / "daily_ai_context.json"
MARKDOWN_OUTPUT = PROJECT_ROOT / "ai" / "draft" / "daily_report_draft.md"
TABLEAU_CSV = PROJECT_ROOT / "data" / "tableau_datasource" / "ai_report_text.csv"

# CSV 表头
CSV_HEADER = ["report_date", "project", "section", "display_order", "analysis_text"]

# 5 个固定 section
SECTION_DEFS = [
    ("核心结论", 1),
    ("整体表现", 2),
    ("收入与用户分析", 3),
    ("广告位与平台分析", 4),
    ("今日建议", 5),
]


# ============================================================
# 格式化工具函数
# ============================================================
def fmt_money(value: float) -> str:
    """格式化金额：$1,234.56。"""
    return f"${value:,.2f}"


def fmt_int(value: int) -> str:
    """格式化整数：58,899。"""
    return f"{value:,}"


def fmt_pct(value: float | None) -> str:
    """
    格式化相对变化率（已是小数，如 0.029 → +2.9%）。
    值为 None 时返回 "N/A"。
    """
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f}%"


def fmt_retention(value: float) -> str:
    """格式化留存率：0.3516 → 35.2%。"""
    return f"{value * 100:.1f}%"


def describe_change(metric_label: str, value: float | None, is_point_change: bool = False) -> str:
    """
    用自然语言描述一个指标的环比变化。
    - is_point_change=False: 相对变化率，如 +3.2%
    - is_point_change=True: 百分点变化，如 +0.96pp
    """
    if value is None:
        return f"{metric_label}无对比数据"
    if is_point_change:
        sign = "+" if value >= 0 else ""
        amt = f"{sign}{value * 100:.2f}pp"
    else:
        sign = "+" if value >= 0 else ""
        amt = f"{sign}{value * 100:.1f}%"
    direction = "上升" if value > 0 else "下降" if value < 0 else "持平"
    return f"{metric_label}{direction} {amt}"


def _direction_word(value: float | None) -> str:
    """根据变化值返回上升/下降/持平的形容词。"""
    if value is None:
        return "无法判断"
    return "增长" if value > 0 else "下降" if value < 0 else "持平"


def _trend_word(value: float | None) -> str:
    """根据变化值返回向好/需关注/平稳。"""
    if value is None:
        return "无法判断"
    if value > 0.03:
        return "向好"
    elif value < -0.03:
        return "需关注"
    return "平稳"


# ============================================================
# 5 个 section 构建函数
# ============================================================
def build_core_summary(ctx: dict) -> str:
    """生成'核心结论'section 文字。"""
    ov = ctx["overview"]
    cur = ov["current"]
    chg = ov["change"]
    alerts = ctx.get("alerts", [])

    # 营收判断
    rev_dir = _direction_word(chg.get("revenue"))
    rev_trend = _trend_word(chg.get("revenue"))

    # 用户判断
    dau_dir = _direction_word(chg.get("dau"))

    # 综合评级
    if rev_trend == "向好" and dau_dir == "增长":
        overall = "今日整体表现良好，用户规模和收入双增长。"
    elif rev_trend == "需关注":
        overall = "今日需重点关注收入侧变化，已触发异常阈值。"
    elif dau_dir == "下降" and chg.get("dau", 0) is not None and chg["dau"] < -0.03:
        overall = "今日用户活跃度有所回落，需关注 DAU 变化趋势。"
    else:
        overall = "今日整体表现平稳，各项指标波动在正常范围内。"

    lines = [
        f"**一句话总结**：{overall}",
        "",
        f"关键数据：DAU {fmt_int(cur['dau'])}（环比{fmt_pct(chg.get('dau'))}），"
        f"营收 {fmt_money(cur['revenue'])}（广告 {fmt_money(cur['ad_revenue'])} + IAP {fmt_money(cur['iap_revenue'])}，"
        f"环比{fmt_pct(chg.get('revenue'))}），"
        f"ARPDAU ${cur['arpdau']:.4f}，eCPM ${cur['ecpm']:.2f}。",
    ]

    if alerts:
        lines.append("")
        lines.append("**异常提醒**：")
        for a in alerts:
            lines.append(f"- [{a['level']}] {a['message']}（{a.get('change', 'N/A')}）")
    else:
        lines.append("")
        lines.append("今日未触发严重异常阈值，整体运行平稳。")

    return "\n".join(lines)


def build_overall_performance(ctx: dict) -> str:
    """生成'整体表现'section 文字。"""
    ov = ctx["overview"]
    cur = ov["current"]
    chg = ov["change"]

    lines = [
        "| 指标 | 今日值 | 环比变化 |",
        "|---|---|---|",
        f"| DAU | {fmt_int(cur['dau'])} | {fmt_pct(chg.get('dau'))} |",
        f"| 新增用户 | {fmt_int(cur['new_users'])} | {fmt_pct(chg.get('new_users'))} |",
        f"| 总营收 | {fmt_money(cur['revenue'])} | {fmt_pct(chg.get('revenue'))} |",
        f"| 广告收入 | {fmt_money(cur['ad_revenue'])} | {fmt_pct(chg.get('ad_revenue'))} |",
        f"| IAP 收入 | {fmt_money(cur['iap_revenue'])} | {fmt_pct(chg.get('iap_revenue'))} |",
        f"| ARPDAU | ${cur['arpdau']:.4f} | {fmt_pct(chg.get('arpdau'))} |",
        f"| eCPM | ${cur['ecpm']:.2f} | {fmt_pct(chg.get('ecpm'))} |",
        f"| 总展示 | {fmt_int(cur['impressions'])} | {fmt_pct(chg.get('impressions'))} |",
        f"| 人均展示 | {cur['impressions_per_dau']:.2f} | {fmt_pct(chg.get('impressions_per_dau'))} |",
        f"| 首日留存 | {fmt_retention(cur['d1_retention'])} | {describe_change('', chg.get('d1_retention'), is_point_change=True).strip()} |",
        f"| 7日留存 | {fmt_retention(cur['d7_retention'])} | {describe_change('', chg.get('d7_retention'), is_point_change=True).strip()} |",
    ]

    # 解读部分
    dau_desc = describe_change("DAU", chg.get("dau"))
    rev_desc = describe_change("营收", chg.get("revenue"))
    ecpm_desc = describe_change("eCPM", chg.get("ecpm"))

    lines.append("")
    lines.append(f"**解读**：{dau_desc}，{rev_desc}。广告 eCPM {ecpm_desc}。")

    d1_chg = chg.get("d1_retention")
    d7_chg = chg.get("d7_retention")
    if d1_chg is not None and d7_chg is not None:
        d1_desc = describe_change("首日留存", d1_chg, is_point_change=True)
        d7_desc = describe_change("7日留存", d7_chg, is_point_change=True)
        lines.append(f"留存方面，{d1_desc}，{d7_desc}。")

    return "\n".join(lines)


def build_revenue_user_analysis(ctx: dict) -> str:
    """生成'收入与用户分析'section 文字。"""
    ov = ctx["overview"]
    cur = ov["current"]
    chg = ov["change"]
    country_top = ctx.get("country_top", [])

    # IAP vs 广告收入占比
    total_rev = cur["revenue"]
    iap_ratio = cur["iap_revenue"] / total_rev * 100 if total_rev > 0 else 0
    ad_ratio = cur["ad_revenue"] / total_rev * 100 if total_rev > 0 else 0

    lines = [
        f"收入结构方面，IAP 收入占比 {iap_ratio:.1f}%（{fmt_money(cur['iap_revenue'])}），"
        f"广告收入占比 {ad_ratio:.1f}%（{fmt_money(cur['ad_revenue'])}）。",
    ]

    rev_chg = chg.get("revenue")
    iap_chg = chg.get("iap_revenue")
    ad_chg = chg.get("ad_revenue")
    if rev_chg is not None:
        lines.append(f"总营收{_direction_word(rev_chg)}{fmt_pct(rev_chg)}，"
                     f"其中 IAP{_direction_word(iap_chg)}{fmt_pct(iap_chg)}，"
                     f"广告收入{_direction_word(ad_chg)}{fmt_pct(ad_chg)}。")

    # 用户数据
    lines.append("")
    lines.append(f"用户侧，DAU 为 {fmt_int(cur['dau'])}，"
                 f"新增用户 {fmt_int(cur['new_users'])}，"
                 f"首日留存 {fmt_retention(cur['d1_retention'])}，"
                 f"7日留存 {fmt_retention(cur['d7_retention'])}。")

    # 国家表现
    if country_top:
        lines.append("")
        lines.append("**国家维度 TOP 表现**：")
        top = country_top[0]
        lines.append(f"收入最高的国家/平台组合为 **{top['country']} / {top['platform']}**，"
                     f"DAU {fmt_int(top['dau'])}，营收 {fmt_money(top['revenue'])}，"
                     f"ARPDAU ${top['arpdau']:.4f}，eCPM ${top['ecpm']:.2f}。")

        if len(country_top) >= 2:
            lines.append("前 5 名依次为：")
            for i, item in enumerate(country_top, 1):
                lines.append(f"  {i}. {item['country']} / {item['platform']} "
                             f"— DAU {fmt_int(item['dau'])}，营收 {fmt_money(item['revenue'])}")

    return "\n".join(lines)


def build_ad_platform_analysis(ctx: dict) -> str:
    """生成'广告位与平台分析'section 文字。"""
    platform_summary = ctx.get("platform_summary", [])
    ad_top = ctx.get("ad_placement_top", [])
    ov = ctx["overview"]
    cur = ov["current"]
    chg = ov["change"]

    lines = []

    # 平台对比
    if len(platform_summary) >= 2:
        android = next((p for p in platform_summary if p["platform"] == "android"), None)
        ios = next((p for p in platform_summary if p["platform"] == "ios"), None)
        if android and ios:
            total_dau = android["dau"] + ios["dau"]
            android_dau_pct = android["dau"] / total_dau * 100 if total_dau > 0 else 0
            ios_dau_pct = ios["dau"] / total_dau * 100 if total_dau > 0 else 0

            total_rev_plt = android["revenue"] + ios["revenue"]
            android_rev_pct = android["revenue"] / total_rev_plt * 100 if total_rev_plt > 0 else 0
            ios_rev_pct = ios["revenue"] / total_rev_plt * 100 if total_rev_plt > 0 else 0

            lines.append("**平台对比**：")
            lines.append(f"- Android：DAU {fmt_int(android['dau'])}（占比 {android_dau_pct:.1f}%），"
                         f"营收 {fmt_money(android['revenue'])}（占比 {android_rev_pct:.1f}%），"
                         f"eCPM ${android['ecpm']:.2f}")
            lines.append(f"- iOS：DAU {fmt_int(ios['dau'])}（占比 {ios_dau_pct:.1f}%），"
                         f"营收 {fmt_money(ios['revenue'])}（占比 {ios_rev_pct:.1f}%），"
                         f"eCPM ${ios['ecpm']:.2f}")

            if ios["arpdau"] > android["arpdau"]:
                lines.append(f"iOS 端 ARPDAU（${ios['arpdau']:.4f}）高于 Android（${android['arpdau']:.4f}），"
                             f"iOS 用户付费价值更优。")
            else:
                lines.append(f"Android 端 ARPDAU（${android['arpdau']:.4f}）高于 iOS（${ios['arpdau']:.4f}）。")

    # 广告位 TOP
    if ad_top:
        lines.append("")
        lines.append("**广告位 TOP 收入**：")
        top1 = ad_top[0]
        lines.append(f"收入最高为 **{top1['ad_placement']}**（{top1['ad_type']}），"
                     f"来自 {top1['ad_network']} / {top1['country']} / {top1['platform']}，"
                     f"收入 {fmt_money(top1['revenue'])}，"
                     f"展示 {fmt_int(top1['impressions'])} 次，eCPM ${top1['ecpm']:.2f}。")

        if len(ad_top) >= 3:
            lines.append("前 3 名：")
            for i, item in enumerate(ad_top[:3], 1):
                lines.append(f"  {i}. {item['ad_placement']}（{item['ad_network']} / {item['country']}）"
                             f" — {fmt_money(item['revenue'])}，eCPM ${item['ecpm']:.2f}")

    # eCPM 变化
    ecpm_chg = chg.get("ecpm")
    lines.append("")
    if ecpm_chg is not None:
        lines.append(f"整体 eCPM 为 ${cur['ecpm']:.2f}，{describe_change('', ecpm_chg)}。")

    return "\n".join(lines)


def build_action_suggestions(ctx: dict) -> str:
    """生成'今日建议'section 文字。"""
    ov = ctx["overview"]
    cur = ov["current"]
    chg = ov["change"]
    alerts = ctx.get("alerts", [])
    country_top = ctx.get("country_top", [])

    suggestions = []

    # 从数据中自动生成建议
    # 检查各项指标方向
    if chg.get("revenue") is not None and chg["revenue"] < -0.03:
        suggestions.append(f"营收环比下降 {abs(chg['revenue']) * 100:.1f}%，建议排查 IAP 转化链路是否正常，"
                           f"并确认主要付费国家（{country_top[0]['country'] if country_top else 'US'}）是否有异常。")

    if chg.get("dau") is not None and chg["dau"] < -0.03:
        suggestions.append(f"DAU 环比下降 {abs(chg['dau']) * 100:.1f}%，建议检查是否有新版本闪退、"
                           f"投放暂停或竞品活动影响。")

    if chg.get("ecpm") is not None and chg["ecpm"] < -0.03:
        suggestions.append(f"eCPM 环比下降 {abs(chg['ecpm']) * 100:.1f}%，建议检查广告填充率和主要广告位的 bid 价格。")

    if chg.get("d7_retention") is not None and chg["d7_retention"] < -0.01:
        suggestions.append(f"7日留存下降 {abs(chg['d7_retention']) * 100:.2f}pp，建议对比不同版本和新用户的留存曲线，"
                           f"定位是版本问题还是用户质量下降。")

    # 来自 alerts 的建议
    for a in alerts:
        suggestions.append(f"[告警] {a['message']}，请优先排查相关数据源。")

    # 兜底建议
    if not suggestions:
        suggestions.append("今日各项核心指标在正常波动范围内，无需特别干预。建议保持当前投放和运营节奏。")
        top_country = country_top[0]["country"] if country_top else "US"
        suggestions.append(f"持续关注 {top_country} 市场的收入趋势和用户留存变化。")
        suggestions.append("建议打开 Tableau Dashboard，重点关注 eCPM 趋势和广告位收入分布。")

    # 编号输出
    lines = []
    for i, s in enumerate(suggestions, 1):
        lines.append(f"{i}. {s}")

    return "\n".join(lines)


# ============================================================
# 输出函数
# ============================================================
def write_markdown_report(sections: dict, ctx: dict) -> None:
    """将 5 个 section 拼接为完整 Markdown 草稿并写入文件。"""
    project = ctx["project"]
    report_date = ctx["report_date"]

    md_lines = [
        f"# {project} 运营日报草稿 - {report_date}",
        "",
        f"> 自动生成时间：{ctx.get('_generated_at', 'N/A')}",
        f"> 对比基准：{ctx.get('previous_date', 'N/A')}",
        "",
        "---",
        "",
        "## 一、核心结论",
        "",
        sections["核心结论"],
        "",
        "---",
        "",
        "## 二、整体表现",
        "",
        sections["整体表现"],
        "",
        "---",
        "",
        "## 三、收入与用户分析",
        "",
        sections["收入与用户分析"],
        "",
        "---",
        "",
        "## 四、广告位与平台分析",
        "",
        sections["广告位与平台分析"],
        "",
        "---",
        "",
        "## 五、今日建议",
        "",
        sections["今日建议"],
        "",
    ]

    MARKDOWN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MARKDOWN_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))


def write_tableau_text_csv(sections: dict, ctx: dict) -> None:
    """将 5 个 section 写入 Tableau 数据源 CSV。"""
    report_date = ctx["report_date"]
    project = ctx["project"]

    TABLEAU_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(TABLEAU_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for section_name, display_order in SECTION_DEFS:
            writer.writerow({
                "report_date": report_date,
                "project": project,
                "section": section_name,
                "display_order": str(display_order),
                "analysis_text": sections[section_name],
            })


# ============================================================
# 上下文加载
# ============================================================
def load_context() -> dict:
    """加载 daily_ai_context.json，文件不存在时抛出明确错误。"""
    if not CONTEXT_PATH.exists():
        raise FileNotFoundError(f"找不到 AI 上下文文件: {CONTEXT_PATH}\n"
                                f"请先运行 scripts/generate_ai_context.py 生成该文件。")
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 主入口
# ============================================================
def main() -> None:
    """主入口：读取上下文 → 生成 5 段文字 → 输出 Markdown 和 CSV。"""
    from datetime import datetime

    print("开始生成日报草稿...")

    # 1. 加载上下文
    print("  [1/3] 加载 daily_ai_context.json ...")
    ctx = load_context()
    ctx["_generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"        报告日期: {ctx['report_date']}")

    # 2. 构建 5 个 section
    print("  [2/3] 生成分析文字...")
    sections = {
        "核心结论": build_core_summary(ctx),
        "整体表现": build_overall_performance(ctx),
        "收入与用户分析": build_revenue_user_analysis(ctx),
        "广告位与平台分析": build_ad_platform_analysis(ctx),
        "今日建议": build_action_suggestions(ctx),
    }

    # 3. 输出 Markdown 和 CSV
    print("  [3/3] 写入输出文件...")
    write_markdown_report(sections, ctx)
    write_tableau_text_csv(sections, ctx)

    print(f"")
    print(f"日报草稿生成完成。")
    print(f"Markdown 草稿: {MARKDOWN_OUTPUT}")
    print(f"Tableau CSV:   {TABLEAU_CSV}")


if __name__ == "__main__":
    main()
