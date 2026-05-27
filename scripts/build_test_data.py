"""
生成 Tableau 测试数据脚本。
自动生成最近 14 天的模拟运营数据，写入 data/tableau_datasource/ 下的固定 CSV 文件，
方便在 Tableau 中搭建第一个 Dashboard。
"""

import csv
import random
import math
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================
# 项目根目录与输出目录
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TABLEAU_DIR = PROJECT_ROOT / "data" / "tableau_datasource"

# ============================================================
# 业务常量
# ============================================================
PROJECT_NAME = "项目A"
PLATFORMS = ["android", "ios"]
COUNTRIES = ["US", "BR", "IN", "PH", "VN"]
AD_NETWORKS = ["UnityAds", "AppLovin", "AdMob"]
AD_PLACEMENTS = {
    "banner_home": "banner",
    "interstitial_level_complete": "interstitial",
    "rewarded_daily_bonus": "rewarded",
}
AI_SECTIONS = [
    ("核心指标总览", 1),
    ("关键变化解读", 2),
    ("今日行动建议", 3),
]

# 各国流量占比（总和 ≈ 1.0）
COUNTRY_WEIGHTS = {"US": 0.35, "BR": 0.20, "IN": 0.18, "PH": 0.15, "VN": 0.12}

# 平台流量占比
PLATFORM_WEIGHTS = {"android": 0.65, "ios": 0.35}

# 广告位收入占比
PLACEMENT_REVENUE_WEIGHTS = {
    "rewarded_daily_bonus": 0.50,
    "interstitial_level_complete": 0.35,
    "banner_home": 0.15,
}


def write_csv(file_path: Path, header: list[str], rows: list[dict]) -> None:
    """将表头和行数据写入 CSV 文件，自动创建父目录。"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def build_dates(days: int = 14) -> list[str]:
    """生成最近 N 天的日期列表（YYYY-MM-DD），从过去到今天。"""
    today = datetime.now().date()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]


def _base_dau(day_index: int) -> float:
    """根据日期索引生成基础 DAU 数值（带周末效应和微趋势）。"""
    base = 55000 + day_index * 400  # 轻微上升趋势
    # 周六/日 偏低 8-12%
    date = datetime.now().date() - timedelta(days=13 - day_index)
    if date.weekday() >= 5:
        base *= random.uniform(0.88, 0.92)
    # 随机 ±5% 噪声
    return round(base * random.uniform(0.95, 1.05))


def _base_revenue(day_index: int) -> float:
    """根据日期索引生成基础营收（美元）。"""
    base = 4200 + day_index * 80
    date = datetime.now().date() - timedelta(days=13 - day_index)
    if date.weekday() >= 5:
        base *= random.uniform(0.90, 0.95)
    return round(base * random.uniform(0.92, 1.08), 2)


def build_daily_overview(dates: list[str]) -> tuple[list[str], list[dict]]:
    """生成每日概览宽表测试数据。"""
    header = [
        "date", "project", "dau", "new_users", "revenue",
        "ad_revenue", "iap_revenue", "arpdau", "ecpm",
        "impressions", "impressions_per_dau", "d1_retention", "d7_retention",
    ]
    rows = []
    for i, d in enumerate(dates):
        dau = int(_base_dau(i))
        new_users = int(dau * random.uniform(0.10, 0.18))
        revenue = _base_revenue(i)
        iap_revenue = round(revenue * random.uniform(0.55, 0.65), 2)
        ad_revenue = round(revenue - iap_revenue, 2)
        arpdau = round(revenue / dau, 4) if dau > 0 else 0
        impressions = int(dau * random.uniform(3.2, 5.5))
        impressions_per_dau = round(impressions / dau, 2) if dau > 0 else 0
        ecpm = round((ad_revenue / impressions) * 1000, 2) if impressions > 0 else 0
        d1_ret = round(random.uniform(0.32, 0.38), 4)
        d7_ret = round(random.uniform(0.10, 0.15), 4)

        rows.append({
            "date": d,
            "project": PROJECT_NAME,
            "dau": dau,
            "new_users": new_users,
            "revenue": revenue,
            "ad_revenue": ad_revenue,
            "iap_revenue": iap_revenue,
            "arpdau": arpdau,
            "ecpm": ecpm,
            "impressions": impressions,
            "impressions_per_dau": impressions_per_dau,
            "d1_retention": d1_ret,
            "d7_retention": d7_ret,
        })
    return header, rows


def build_country_daily(dates: list[str]) -> tuple[list[str], list[dict]]:
    """生成国家×平台日维度宽表测试数据。"""
    header = [
        "date", "project", "country", "platform",
        "dau", "new_users", "revenue", "ad_revenue",
        "arpdau", "ecpm", "impressions", "impressions_per_dau",
    ]
    rows = []
    for i, d in enumerate(dates):
        for country in COUNTRIES:
            for platform in PLATFORMS:
                cw = COUNTRY_WEIGHTS[country]
                pw = PLATFORM_WEIGHTS[platform]

                dau = int(_base_dau(i) * cw * pw * random.uniform(0.90, 1.10))
                new_users = int(dau * random.uniform(0.10, 0.18))
                revenue = round(_base_revenue(i) * cw * pw * random.uniform(0.85, 1.15), 2)
                ad_revenue = round(revenue * random.uniform(0.35, 0.48), 2)
                arpdau = round(revenue / dau, 4) if dau > 0 else 0
                impressions = int(dau * random.uniform(3.0, 5.5))
                impressions_per_dau = round(impressions / dau, 2) if dau > 0 else 0
                ecpm = round((ad_revenue / impressions) * 1000, 2) if impressions > 0 else 0

                rows.append({
                    "date": d,
                    "project": PROJECT_NAME,
                    "country": country,
                    "platform": platform,
                    "dau": dau,
                    "new_users": new_users,
                    "revenue": revenue,
                    "ad_revenue": ad_revenue,
                    "arpdau": arpdau,
                    "ecpm": ecpm,
                    "impressions": impressions,
                    "impressions_per_dau": impressions_per_dau,
                })
    return header, rows


def build_platform_daily(dates: list[str]) -> tuple[list[str], list[dict]]:
    """生成平台日维度宽表测试数据。"""
    header = [
        "date", "project", "platform",
        "dau", "new_users", "revenue", "ad_revenue",
        "arpdau", "ecpm", "impressions",
    ]
    rows = []
    for i, d in enumerate(dates):
        for platform in PLATFORMS:
            pw = PLATFORM_WEIGHTS[platform]

            dau = int(_base_dau(i) * pw * random.uniform(0.93, 1.07))
            new_users = int(dau * random.uniform(0.10, 0.18))
            revenue = round(_base_revenue(i) * pw * random.uniform(0.88, 1.12), 2)
            ad_revenue = round(revenue * random.uniform(0.35, 0.48), 2)
            arpdau = round(revenue / dau, 4) if dau > 0 else 0
            impressions = int(dau * random.uniform(3.2, 5.5))
            ecpm = round((ad_revenue / impressions) * 1000, 2) if impressions > 0 else 0

            rows.append({
                "date": d,
                "project": PROJECT_NAME,
                "platform": platform,
                "dau": dau,
                "new_users": new_users,
                "revenue": revenue,
                "ad_revenue": ad_revenue,
                "arpdau": arpdau,
                "ecpm": ecpm,
                "impressions": impressions,
            })
    return header, rows


def build_ad_placement_daily(dates: list[str]) -> tuple[list[str], list[dict]]:
    """生成广告位×广告网络×国家日维度宽表测试数据。"""
    header = [
        "date", "project", "platform", "country",
        "ad_network", "ad_placement", "ad_type",
        "revenue", "impressions", "ecpm",
    ]
    rows = []
    for i, d in enumerate(dates):
        for platform in PLATFORMS:
            for country in COUNTRIES:
                cw = COUNTRY_WEIGHTS[country]
                pw = PLATFORM_WEIGHTS[platform]

                total_ad_rev = _base_revenue(i) * 0.40 * cw * pw
                total_impressions = int(_base_dau(i) * cw * pw * random.uniform(3.0, 5.5))

                # 为每个广告位生成数据
                remaining_rev = total_ad_rev
                remaining_imp = total_impressions
                placements = list(AD_PLACEMENTS.keys())
                for pi, placement in enumerate(placements):
                    ad_type = AD_PLACEMENTS[placement]
                    ad_network = AD_NETWORKS[pi % len(AD_NETWORKS)]

                    is_last = (pi == len(placements) - 1)
                    if is_last:
                        placement_imp = max(1, remaining_imp)
                        placement_rev = round(max(0.01, remaining_rev), 2)
                    else:
                        rev_w = PLACEMENT_REVENUE_WEIGHTS[placement]
                        placement_rev = round(total_ad_rev * rev_w * random.uniform(0.85, 1.15), 2)
                        placement_imp = int(total_impressions * rev_w * random.uniform(0.85, 1.15))
                        remaining_rev -= placement_rev
                        remaining_imp -= placement_imp

                    ecpm = round((placement_rev / placement_imp) * 1000, 2) if placement_imp > 0 else 0

                    rows.append({
                        "date": d,
                        "project": PROJECT_NAME,
                        "platform": platform,
                        "country": country,
                        "ad_network": ad_network,
                        "ad_placement": placement,
                        "ad_type": ad_type,
                        "revenue": placement_rev,
                        "impressions": placement_imp,
                        "ecpm": ecpm,
                    })
    return header, rows


def build_ai_report_text(dates: list[str]) -> tuple[list[str], list[dict]]:
    """生成 AI 分析文本测试数据（每日 3 段分析文字）。"""
    header = [
        "report_date", "project", "section", "display_order", "analysis_text",
    ]

    template_texts = {
        "核心指标总览": (
            "今日 DAU {dau:,}，环比{dau_change}；"
            "营收 ${revenue:,.2f}（广告 ${ad_rev:,.2f} + IAP ${iap_rev:,.2f}），环比{rev_change}；"
            "ARPDAU ${arpdau:.4f}；eCPM ${ecpm:.2f}；"
            "首日留存 {d1_ret:.1%}，7日留存 {d7_ret:.1%}。"
        ),
        "关键变化解读": (
            "今日主要变化：{highlight}。"
            "建议重点关注 {focus_country} 市场的 {focus_metric} 变化，"
            "可能与 {possible_cause} 有关。"
            "整体趋势{trend}，{action_suggestion}。"
        ),
        "今日行动建议": (
            "1. 检查 {check_country} 的 {check_metric} 是否持续下降；"
            "2. 确认 {check_platform} 端最新版本 {check_version} 的留存数据；"
            "3. 评估 {check_campaign} 投放渠道的 ROI 是否需要调整出价。"
        ),
    }

    highlights = [
        "eCPM 连续第3天上升，激励视频位表现突出",
        "美国市场 IAP 收入环比增长 8%",
        "印度市场新增用户量持续放大但 ARPDAU 偏低",
        "巴西市场广告收入环比下降 5%，需关注填充率",
    ]
    causes = ["周末效应", "新版本上线", "投放预算调整", "竞品活动影响"]
    check_countries = ["US", "BR", "IN"]
    check_metrics = ["D7 留存", "eCPM", "ARPU"]
    check_platforms = ["android", "ios"]
    check_campaigns = ["Google Ads US", "Facebook BR", "TikTok IN"]

    rows = []
    for i, d in enumerate(dates):
        for section, order in AI_SECTIONS:
            if section == "核心指标总览":
                dau = int(_base_dau(i))
                revenue = _base_revenue(i)
                ad_rev = round(revenue * 0.40, 2)
                iap_rev = round(revenue - ad_rev, 2)
                arpdau = round(revenue / dau, 4) if dau > 0 else 0
                ecpm = round(random.uniform(9, 14), 2)
                d1_ret = round(random.uniform(0.32, 0.38), 4)
                d7_ret = round(random.uniform(0.10, 0.15), 4)
                dau_change = f"{random.choice(['+', '-'])}{random.uniform(1, 5):.1f}%"
                rev_change = f"{random.choice(['+', '-'])}{random.uniform(1, 4):.1f}%"
                text = template_texts[section].format(
                    dau=dau, dau_change=dau_change,
                    revenue=revenue, ad_rev=ad_rev, iap_rev=iap_rev,
                    rev_change=rev_change, arpdau=arpdau, ecpm=ecpm,
                    d1_ret=d1_ret, d7_ret=d7_ret,
                )
            elif section == "关键变化解读":
                highlight = highlights[i % len(highlights)]
                focus_country = random.choice(COUNTRIES)
                focus_metric = random.choice(["eCPM", "ARPDAU", "留存率", "新增用户"])
                possible_cause = random.choice(causes)
                trend = random.choice(["向好", "平稳", "需关注"])
                action_suggestion = (
                    "建议继续保持当前投放节奏" if trend == "向好"
                    else "暂不需要特别干预" if trend == "平稳"
                    else "建议明天重点排查数据波动原因"
                )
                text = template_texts[section].format(
                    highlight=highlight, focus_country=focus_country,
                    focus_metric=focus_metric, possible_cause=possible_cause,
                    trend=trend, action_suggestion=action_suggestion,
                )
            else:  # 今日行动建议
                text = template_texts[section].format(
                    check_country=check_countries[i % len(check_countries)],
                    check_metric=check_metrics[i % len(check_metrics)],
                    check_platform=check_platforms[i % len(check_platforms)],
                    check_version=f"v{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,99)}",
                    check_campaign=check_campaigns[i % len(check_campaigns)],
                )

            rows.append({
                "report_date": d,
                "project": PROJECT_NAME,
                "section": section,
                "display_order": str(order),
                "analysis_text": text,
            })
    return header, rows


def main() -> None:
    """主入口：生成所有 Tableau 固定数据源的测试数据。"""
    print("开始生成 Tableau 测试数据...")

    dates = build_dates(days=14)

    # 定义所有需要构建的数据集
    builders = [
        ("mart_daily_overview.csv", build_daily_overview),
        ("mart_country_daily.csv", build_country_daily),
        ("mart_platform_daily.csv", build_platform_daily),
        ("mart_ad_placement_daily.csv", build_ad_placement_daily),
        ("ai_report_text.csv", build_ai_report_text),
    ]

    for filename, builder in builders:
        header, rows = builder(dates)
        file_path = TABLEAU_DIR / filename
        write_csv(file_path, header, rows)
        print(f"  [OK] {filename} -- {len(rows)} rows")

    print(f"")
    print(f"Done. Test data generated.")
    print(f"Output: {TABLEAU_DIR}")


if __name__ == "__main__":
    main()
