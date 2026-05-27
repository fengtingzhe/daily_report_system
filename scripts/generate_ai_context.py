"""
AI 上下文生成脚本。
从 Tableau 固定数据源 CSV 中读取数据，提取最新一天的核心指标、环比变化、
国家/平台/广告位表现、AI 测试文字，生成结构化 JSON 供 AI 分析日报使用。
输出文件：ai/context/daily_ai_context.json
"""

import json
from pathlib import Path

import pandas as pd

# ============================================================
# 项目根目录与路径常量
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TABLEAU_DIR = PROJECT_ROOT / "data" / "tableau_datasource"
OUTPUT_PATH = PROJECT_ROOT / "ai" / "context" / "daily_ai_context.json"

# 参与环比计算的核心指标列表
OVERVIEW_METRICS = [
    "dau", "new_users", "revenue", "ad_revenue", "iap_revenue",
    "arpdau", "ecpm", "impressions", "impressions_per_dau",
    "d1_retention", "d7_retention",
]

# 保留率类指标（变化以百分点为单位，而非比例）
RETENTION_METRICS = {"d1_retention", "d7_retention"}


def read_csv(filename: str) -> pd.DataFrame:
    """读取 Tableau 数据源 CSV 文件，文件不存在时抛出清晰错误。"""
    file_path = TABLEAU_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"找不到数据文件: {file_path}")
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    if df.empty:
        raise ValueError(f"数据文件为空: {file_path}")
    return df


def safe_pct_change(current: float, previous: float) -> float | None:
    """计算相对变化率 (current - previous) / previous，分母为 0 时返回 None。"""
    if previous == 0:
        return None
    return round((current - previous) / previous, 6)


def safe_point_change(current: float, previous: float) -> float | None:
    """计算百分点变化 current - previous。"""
    return round(current - previous, 6)


def build_overview(df: pd.DataFrame) -> dict:
    """从日概览宽表构建 overview 部分，含 current、previous、change。"""
    # 按日期排序，取最新两天
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    if len(df) < 2:
        raise ValueError(f"日概览数据不足两天（仅有 {len(df)} 行），无法计算环比。")

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    report_date = latest["date"].strftime("%Y-%m-%d")
    previous_date = prev["date"].strftime("%Y-%m-%d")

    def _row(row) -> dict:
        return {
            "dau": int(row["dau"]),
            "new_users": int(row["new_users"]),
            "revenue": float(row["revenue"]),
            "ad_revenue": float(row["ad_revenue"]),
            "iap_revenue": float(row["iap_revenue"]),
            "arpdau": float(row["arpdau"]),
            "ecpm": float(row["ecpm"]),
            "impressions": int(row["impressions"]),
            "impressions_per_dau": float(row["impressions_per_dau"]),
            "d1_retention": float(row["d1_retention"]),
            "d7_retention": float(row["d7_retention"]),
        }

    current = _row(latest)
    previous = _row(prev)

    change = {}
    for metric in OVERVIEW_METRICS:
        cur_val = current[metric]
        prev_val = previous[metric]
        if metric in RETENTION_METRICS:
            change[metric] = safe_point_change(cur_val, prev_val)
        else:
            change[metric] = safe_pct_change(cur_val, prev_val)

    return {
        "report_date": report_date,
        "previous_date": previous_date,
        "current": current,
        "previous": previous,
        "change": change,
    }


def build_alerts(change: dict) -> list[dict]:
    """根据环比变化和阈值规则生成告警列表。"""
    alerts = []
    rules = [
        ("revenue", "revenue", "收入环比下降超过 10%", lambda v: v is not None and v <= -0.10),
        ("dau", "dau", "DAU 环比下降超过 10%", lambda v: v is not None and v <= -0.10),
        ("ecpm", "ecpm", "eCPM 环比下降超过 15%", lambda v: v is not None and v <= -0.15),
        ("d1_retention", "d1_retention", "D1 留存环比下降超过 3 个百分点", lambda v: v is not None and v <= -0.03),
        ("d7_retention", "d7_retention", "D7 留存环比下降超过 3 个百分点", lambda v: v is not None and v <= -0.03),
    ]
    for metric_key, label, message, condition in rules:
        val = change.get(metric_key)
        if condition(val):
            alerts.append({
                "level": "warning",
                "metric": label,
                "message": message,
                "change": val,
            })
    return alerts


def build_country_top(df: pd.DataFrame, report_date: str) -> list[dict]:
    """提取最新日期的国家×平台 TOP5（按 revenue 降序）。"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    latest_df = df[df["date"] == pd.to_datetime(report_date)]
    if latest_df.empty:
        return []

    top = latest_df.sort_values("revenue", ascending=False).head(5)
    return [
        {
            "country": str(row["country"]),
            "platform": str(row["platform"]),
            "dau": int(row["dau"]),
            "revenue": float(row["revenue"]),
            "ad_revenue": float(row["ad_revenue"]),
            "arpdau": float(row["arpdau"]),
            "ecpm": float(row["ecpm"]),
            "impressions_per_dau": float(row["impressions_per_dau"]),
        }
        for _, row in top.iterrows()
    ]


def build_platform_summary(df: pd.DataFrame, report_date: str) -> list[dict]:
    """提取最新日期的平台汇总（android / ios）。"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    latest_df = df[df["date"] == pd.to_datetime(report_date)]
    if latest_df.empty:
        return []

    result = []
    for _, row in latest_df.iterrows():
        result.append({
            "platform": str(row["platform"]),
            "dau": int(row["dau"]),
            "revenue": float(row["revenue"]),
            "ad_revenue": float(row["ad_revenue"]),
            "arpdau": float(row["arpdau"]),
            "ecpm": float(row["ecpm"]),
            "impressions": int(row["impressions"]),
        })
    return result


def build_ad_placement_top(df: pd.DataFrame, report_date: str) -> list[dict]:
    """提取最新日期的广告位 TOP10（按 revenue 降序）。"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    latest_df = df[df["date"] == pd.to_datetime(report_date)]
    if latest_df.empty:
        return []

    top = latest_df.sort_values("revenue", ascending=False).head(10)
    return [
        {
            "platform": str(row["platform"]),
            "country": str(row["country"]),
            "ad_network": str(row["ad_network"]),
            "ad_placement": str(row["ad_placement"]),
            "ad_type": str(row["ad_type"]),
            "revenue": float(row["revenue"]),
            "impressions": int(row["impressions"]),
            "ecpm": float(row["ecpm"]),
        }
        for _, row in top.iterrows()
    ]


def build_existing_ai_text(df: pd.DataFrame, report_date: str) -> list[dict]:
    """提取最新日期的 AI 测试分析文字，按 display_order 排序。"""
    df = df.copy()
    df["report_date"] = pd.to_datetime(df["report_date"])
    latest_df = df[df["report_date"] == pd.to_datetime(report_date)]
    if latest_df.empty:
        return []

    sorted_df = latest_df.sort_values("display_order")
    return [
        {
            "section": str(row["section"]),
            "display_order": int(row["display_order"]),
            "analysis_text": str(row["analysis_text"]),
        }
        for _, row in sorted_df.iterrows()
    ]


def main() -> None:
    """主入口：读取 CSV，生成 daily_ai_context.json。"""
    print("开始生成 AI 上下文...")

    # ---- 1. 读取日概览数据 ----
    print("  [1/5] 读取 mart_daily_overview.csv ...")
    df_overview = read_csv("mart_daily_overview.csv")

    # ---- 2. 构建 overview 和 alerts ----
    overview = build_overview(df_overview)
    report_date = overview["report_date"]
    print(f"        报告日期: {report_date}")
    print(f"        前一日:   {overview['previous_date']}")

    alerts = build_alerts(overview["change"])
    if alerts:
        print(f"        发现 {len(alerts)} 条异常告警")
    else:
        print(f"        无异常告警")

    # ---- 3. 读取国家/平台/广告位数据 ----
    print("  [2/5] 读取 mart_country_daily.csv ...")
    df_country = read_csv("mart_country_daily.csv")
    country_top = build_country_top(df_country, report_date)

    print("  [3/5] 读取 mart_platform_daily.csv ...")
    df_platform = read_csv("mart_platform_daily.csv")
    platform_summary = build_platform_summary(df_platform, report_date)

    print("  [4/5] 读取 mart_ad_placement_daily.csv ...")
    df_ad = read_csv("mart_ad_placement_daily.csv")
    ad_placement_top = build_ad_placement_top(df_ad, report_date)

    # ---- 4. 读取 AI 测试文字 ----
    print("  [5/5] 读取 ai_report_text.csv ...")
    df_ai_text = read_csv("ai_report_text.csv")
    existing_ai_text = build_existing_ai_text(df_ai_text, report_date)

    # ---- 5. 组装并输出 JSON ----
    output = {
        "project": "项目A",
        "report_date": report_date,
        "previous_date": overview["previous_date"],
        "overview": {
            "current": overview["current"],
            "previous": overview["previous"],
            "change": overview["change"],
        },
        "alerts": alerts,
        "country_top": country_top,
        "platform_summary": platform_summary,
        "ad_placement_top": ad_placement_top,
        "existing_ai_text": existing_ai_text,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"")
    print(f"AI 上下文生成完成。")
    print(f"输出文件: {OUTPUT_PATH}")
    print(f"告警数量: {len(alerts)}")
    print(f"国家 TOP: {len(country_top)} 条")
    print(f"平台汇总: {len(platform_summary)} 条")
    print(f"广告位 TOP: {len(ad_placement_top)} 条")
    print(f"AI 测试文字: {len(existing_ai_text)} 段")


if __name__ == "__main__":
    main()
