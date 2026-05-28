"""
从 clean 层构建 mart 层日概览数据。

第一版只处理 Unity clean CSV：
data/clean/unity/*.csv -> data/mart/mart_daily_overview.csv

运行方式：
    python scripts/build_mart_from_clean.py
    py scripts/build_mart_from_clean.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


# ============================================================
# 路径常量
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_UNITY_DIR = PROJECT_ROOT / "data" / "clean" / "unity"
MART_DIR = PROJECT_ROOT / "data" / "mart"
OUTPUT_PATH = MART_DIR / "mart_daily_overview.csv"


# mart_daily_overview.csv 固定字段顺序，需要和 Tableau 日概览表结构保持一致。
MART_COLUMNS = [
    "date",
    "project",
    "dau",
    "new_users",
    "revenue",
    "ad_revenue",
    "iap_revenue",
    "arpdau",
    "ecpm",
    "impressions",
    "impressions_per_dau",
    "d1_retention",
    "d7_retention",
]


def write_empty_mart() -> None:
    """没有 clean 数据时，输出只有表头的 mart 文件，保证下游文件存在。"""
    MART_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=MART_COLUMNS).to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """统一字段名，去掉 BOM 和首尾空格，避免少量异常表头影响后续处理。"""
    df = df.copy()
    df.columns = [
        str(column).replace("\ufeff", "").strip().lower()
        for column in df.columns
    ]
    return df


def clean_money_value(value: object) -> float:
    """
    将金额字段清洗成数字。

    支持常见格式：
    - $123.45
    - 1,234.56
    - 空值或无法解析的内容按 0 处理
    """
    if value is None or pd.isna(value):
        return 0.0

    text = str(value).strip()
    if not text:
        return 0.0

    # 兼容会计负数格式，例如 ($123.45)。
    is_parenthesized_negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")

    # 去掉货币符号、千分位逗号和空白字符，只保留数字、小数点和正负号。
    text = text.replace(",", "")
    text = re.sub(r"[^0-9.+-]", "", text)
    if text in {"", "+", "-", ".", "+.", "-."}:
        return 0.0

    try:
        amount = float(text)
    except ValueError:
        return 0.0

    return -amount if is_parenthesized_negative else amount


def pick_project(df: pd.DataFrame) -> pd.Series:
    """
    生成 project 字段。

    优先级：
    1. project
    2. project_name
    3. 项目A
    """
    if "project" in df.columns:
        project = df["project"].astype(str).str.strip()
    elif "project_name" in df.columns:
        project = df["project_name"].astype(str).str.strip()
    else:
        project = pd.Series(["项目A"] * len(df), index=df.index)

    project = project.replace("", "项目A")
    project = project.replace({"nan": "项目A", "None": "项目A"})
    return project


def prepare_clean_frame(df: pd.DataFrame, file_name: str) -> pd.DataFrame:
    """把单个 clean CSV 标准化为 mart 聚合前的最小字段集。"""
    df = normalize_columns(df)

    if "date" not in df.columns:
        print(f"WARNING: {file_name} 缺少 date 字段，已跳过该文件。")
        return pd.DataFrame(columns=["date", "project", "revenue", "ad_revenue"])

    prepared = pd.DataFrame(index=df.index)
    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    bad_date_count = int(parsed_dates.isna().sum())
    if bad_date_count:
        print(f"WARNING: {file_name} 有 {bad_date_count} 行 date 解析失败，已丢弃。")

    prepared["date"] = parsed_dates.dt.strftime("%Y-%m-%d")
    prepared["project"] = pick_project(df)

    if "revenue" in df.columns:
        prepared["revenue"] = df["revenue"].map(clean_money_value)
    else:
        prepared["revenue"] = 0.0

    if "ad_revenue" in df.columns:
        prepared["ad_revenue"] = df["ad_revenue"].map(clean_money_value)
    else:
        prepared["ad_revenue"] = 0.0

    return prepared.dropna(subset=["date"])


def build_mart(all_clean_data: pd.DataFrame) -> pd.DataFrame:
    """按 date + project 聚合 Unity clean 数据，并补齐 mart 指标字段。"""
    grouped = (
        all_clean_data
        .groupby(["date", "project"], as_index=False)
        .agg({"revenue": "sum", "ad_revenue": "sum"})
    )

    mart = pd.DataFrame()
    mart["date"] = grouped["date"]
    mart["project"] = grouped["project"]
    mart["dau"] = 0
    mart["new_users"] = 0
    mart["revenue"] = grouped["revenue"].round(2)
    mart["ad_revenue"] = grouped["ad_revenue"].round(2)
    mart["iap_revenue"] = (mart["revenue"] - mart["ad_revenue"]).round(2)

    negative_iap = mart[mart["iap_revenue"] < 0]
    if not negative_iap.empty:
        for _, row in negative_iap.iterrows():
            print(
                "WARNING: iap_revenue 小于 0，"
                f"date={row['date']}, project={row['project']}, "
                f"iap_revenue={row['iap_revenue']}"
            )

    mart["arpdau"] = 0
    mart["ecpm"] = 0
    mart["impressions"] = 0
    mart["impressions_per_dau"] = 0
    mart["d1_retention"] = 0
    mart["d7_retention"] = 0

    mart = mart[MART_COLUMNS]
    mart = mart.sort_values(["date", "project"]).reset_index(drop=True)
    return mart


def main() -> None:
    """主入口：扫描 Unity clean CSV，聚合并输出 mart_daily_overview.csv。"""
    print("开始构建 mart 数据...")

    print("[1/3] 扫描 data/clean/unity/*.csv")
    csv_files = sorted(CLEAN_UNITY_DIR.glob("*.csv"))
    if not csv_files:
        write_empty_mart()
        print("未发现 Unity clean CSV，已生成空 mart_daily_overview.csv。")
        return

    print(f"发现 {len(csv_files)} 个 Unity clean CSV")

    print("[2/3] 读取并合并 clean 数据")
    prepared_frames: list[pd.DataFrame] = []
    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
        except Exception as exc:
            print(f"WARNING: 读取 {csv_path.name} 失败，已跳过。原因: {exc}")
            continue

        print(f"读取 {csv_path.name}，{len(df)} rows")
        prepared = prepare_clean_frame(df, csv_path.name)
        if not prepared.empty:
            prepared_frames.append(prepared)

    if prepared_frames:
        all_clean_data = pd.concat(prepared_frames, ignore_index=True)
    else:
        all_clean_data = pd.DataFrame(columns=["date", "project", "revenue", "ad_revenue"])

    print("[3/3] 聚合生成 mart_daily_overview.csv")
    MART_DIR.mkdir(parents=True, exist_ok=True)

    if all_clean_data.empty:
        mart = pd.DataFrame(columns=MART_COLUMNS)
    else:
        mart = build_mart(all_clean_data)

    mart.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    relative_output = OUTPUT_PATH.relative_to(PROJECT_ROOT)
    print(f"输出: {relative_output}")
    print(f"完成。共 {len(mart)} 行。")


if __name__ == "__main__":
    main()
