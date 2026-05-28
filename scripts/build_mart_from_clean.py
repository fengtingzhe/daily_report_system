"""
从 clean 层构建 mart 层数据。

当前脚本读取 data/clean/*/*.csv，使用 config/field_mappings.yaml 中维护的字段别名，
宽松识别不同平台导出的字段，并输出 Tableau 固定数据源对应的 mart CSV。

运行方式：
    python scripts/build_mart_from_clean.py
    py scripts/build_mart_from_clean.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs


# ============================================================
# 路径常量
# ============================================================
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
MART_DIR = PROJECT_ROOT / "data" / "mart"
FIELD_MAPPING_PATH = PROJECT_ROOT / "config" / "field_mappings.yaml"


# ============================================================
# Tableau 固定数据源表头
# ============================================================
MART_SCHEMAS: dict[str, list[str]] = {
    "mart_daily_overview.csv": [
        "date", "project", "dau", "new_users", "revenue", "ad_revenue",
        "iap_revenue", "arpdau", "ecpm", "impressions",
        "impressions_per_dau", "d1_retention", "d7_retention",
    ],
    "mart_country_daily.csv": [
        "date", "project", "country", "platform", "dau", "new_users",
        "revenue", "ad_revenue", "arpdau", "ecpm", "impressions",
        "impressions_per_dau",
    ],
    "mart_platform_daily.csv": [
        "date", "project", "platform", "dau", "new_users", "revenue",
        "ad_revenue", "arpdau", "ecpm", "impressions",
    ],
    "mart_ad_placement_daily.csv": [
        "date", "project", "platform", "country", "ad_network",
        "ad_placement", "ad_type", "revenue", "impressions", "ecpm",
    ],
    "mart_campaign_daily.csv": [
        "date", "project", "platform", "country", "channel", "campaign",
        "spend", "installs", "cpi", "revenue", "d0_roas", "d1_roas",
        "d7_roas",
    ],
    "mart_retention_daily.csv": [
        "date", "project", "install_date", "platform", "country", "channel",
        "new_users", "d1_retention", "d3_retention", "d7_retention",
        "d14_retention", "d30_retention",
    ],
    "mart_version_daily.csv": [
        "date", "project", "version", "platform", "dau", "new_users",
        "revenue", "d1_retention", "d7_retention",
    ],
}


NUMERIC_FIELDS = {
    "dau", "new_users", "revenue", "ad_revenue", "iap_revenue",
    "impressions", "ecpm", "spend", "installs", "d1_retention",
    "d3_retention", "d7_retention", "d14_retention", "d30_retention",
}

INTEGER_FIELDS = {"dau", "new_users", "impressions", "installs"}
MONEY_FIELDS = {"revenue", "ad_revenue", "iap_revenue", "spend", "ecpm"}
RATIO_FIELDS = {
    "arpdau", "impressions_per_dau", "cpi", "d0_roas", "d1_roas", "d7_roas",
    "d1_retention", "d3_retention", "d7_retention", "d14_retention", "d30_retention",
}

TEXT_DEFAULTS = {
    "project": "项目A",
    "country": "unknown",
    "platform": "unknown",
    "campaign": "unknown",
    "channel": "unknown",
    "version": "unknown",
    "ad_network": "unknown",
    "ad_placement": "unknown",
    "ad_type": "unknown",
}


def relative(path: Path) -> str:
    """输出相对项目根目录的路径，方便日志阅读。"""
    return str(path.relative_to(PROJECT_ROOT))


def normalize_name(name: object) -> str:
    """把字段名标准化，提升不同 CSV 表头的匹配容错性。"""
    text = str(name).replace("\ufeff", "").strip().lower()
    text = re.sub(r"[^\w]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def load_field_mappings() -> dict[str, list[str]]:
    """加载字段别名配置；配置缺失时也能使用标准字段名继续运行。"""
    if not FIELD_MAPPING_PATH.exists():
        print(f"WARNING: 找不到字段映射配置 {relative(FIELD_MAPPING_PATH)}，将只使用标准字段名。")
        return {}

    with open(FIELD_MAPPING_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    mappings: dict[str, list[str]] = {}
    for canonical, aliases in raw.items():
        alias_list = aliases if isinstance(aliases, list) else []
        mappings[canonical] = [canonical, *[str(alias) for alias in alias_list]]
    return mappings


def find_column(df: pd.DataFrame, canonical: str, mappings: dict[str, list[str]]) -> str | None:
    """根据标准字段名和别名配置，在 DataFrame 中找到对应的原始列名。"""
    normalized_to_original = {normalize_name(column): column for column in df.columns}
    aliases = mappings.get(canonical, [canonical])
    for alias in aliases:
        normalized_alias = normalize_name(alias)
        if normalized_alias in normalized_to_original:
            return normalized_to_original[normalized_alias]
    return None


def clean_number(value: object, *, percent: bool = False) -> float:
    """清洗数值字段，兼容金额、千分位、百分号和空值。"""
    if value is None or pd.isna(value):
        return 0.0

    text = str(value).strip()
    if not text:
        return 0.0

    has_percent = "%" in text
    is_parenthesized_negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace(",", "")
    text = re.sub(r"[^0-9.+-]", "", text)
    if text in {"", "+", "-", ".", "+.", "-."}:
        return 0.0

    try:
        number = float(text)
    except ValueError:
        return 0.0

    if is_parenthesized_negative:
        number = -number
    if percent and has_percent:
        number = number / 100
    return number


def get_text_series(
    df: pd.DataFrame,
    canonical: str,
    mappings: dict[str, list[str]],
    *,
    default: str,
    file_name: str,
) -> pd.Series:
    """读取文本字段；字段缺失时使用默认值并打印 warning。"""
    column = find_column(df, canonical, mappings)
    if column is None:
        print(f"WARNING: {file_name} 缺少 {canonical} 字段，默认填 {default}。")
        return pd.Series([default] * len(df), index=df.index)

    series = df[column].astype(str).str.strip()
    series = series.replace({"": default, "nan": default, "None": default})
    return series


def get_number_series(
    df: pd.DataFrame,
    canonical: str,
    mappings: dict[str, list[str]],
    *,
    file_name: str,
    percent: bool = False,
) -> pd.Series:
    """读取数值字段；字段缺失或解析失败时填 0。"""
    column = find_column(df, canonical, mappings)
    if column is None:
        print(f"WARNING: {file_name} 缺少 {canonical} 字段，默认填 0。")
        return pd.Series([0.0] * len(df), index=df.index)
    return df[column].map(lambda value: clean_number(value, percent=percent))


def get_optional_number_series(
    df: pd.DataFrame,
    canonical: str,
    mappings: dict[str, list[str]],
    *,
    percent: bool = False,
) -> pd.Series | None:
    """读取可选数值字段；字段不存在时返回 None，不打印 warning。"""
    column = find_column(df, canonical, mappings)
    if column is None:
        return None
    return df[column].map(lambda value: clean_number(value, percent=percent))


def read_clean_csv(csv_path: Path) -> pd.DataFrame | None:
    """读取单个 clean CSV，失败时跳过，不中断整个流程。"""
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(csv_path, dtype=str, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            print(f"WARNING: 读取 {csv_path.name} 失败，已跳过。原因: {exc}")
            return None

    print(f"WARNING: {csv_path.name} 编码无法识别，已跳过。")
    return None


def prepare_standard_frame(
    df: pd.DataFrame,
    csv_path: Path,
    mappings: dict[str, list[str]],
) -> pd.DataFrame:
    """把任意 clean CSV 转成统一字段集，供各 mart 表复用。"""
    file_name = csv_path.name
    df = df.copy()
    df.columns = [normalize_name(column) for column in df.columns]

    date_column = find_column(df, "date", mappings)
    if date_column is None:
        print(f"WARNING: {file_name} 缺少 date 字段，已跳过该文件。")
        return pd.DataFrame()

    parsed_dates = pd.to_datetime(df[date_column], errors="coerce")
    bad_date_count = int(parsed_dates.isna().sum())
    if bad_date_count:
        print(f"WARNING: {file_name} 有 {bad_date_count} 行 date 解析失败，已丢弃。")

    output = pd.DataFrame(index=df.index)
    output["date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    for field, default in TEXT_DEFAULTS.items():
        output[field] = get_text_series(
            df,
            field,
            mappings,
            default=default,
            file_name=file_name,
        )

    # 如果没有业务平台字段，用 clean 子目录名兜底，方便追踪来源。
    if "platform" in output.columns and (output["platform"] == "unknown").all():
        source_platform = csv_path.parent.name
        output["platform"] = source_platform

    output["install_date"] = output["date"]
    install_date_column = find_column(df, "install_date", mappings)
    if install_date_column is not None:
        install_dates = pd.to_datetime(df[install_date_column], errors="coerce")
        output["install_date"] = install_dates.dt.strftime("%Y-%m-%d").fillna(output["date"])

    for field in NUMERIC_FIELDS:
        output[field] = get_number_series(
            df,
            field,
            mappings,
            file_name=file_name,
            percent=field.endswith("_retention"),
        )

    # 收入字段兼容：如果没有总收入，但有广告收入/IAP 收入，则合成为总收入。
    revenue_column = find_column(df, "revenue", mappings)
    if revenue_column is None:
        output["revenue"] = output["ad_revenue"] + output["iap_revenue"]

    # IAP 收入第一版按 revenue - ad_revenue 计算，保留负数并 warning。
    output["iap_revenue"] = output["revenue"] - output["ad_revenue"]
    negative_iap = output[output["iap_revenue"] < 0]
    if not negative_iap.empty:
        print(f"WARNING: {file_name} 有 {len(negative_iap)} 行 iap_revenue 小于 0。")

    output = output.dropna(subset=["date"]).reset_index(drop=True)
    return output


def safe_divide(numerator: pd.Series, denominator: pd.Series, scale: float = 1.0) -> pd.Series:
    """安全除法，分母为 0 时返回 0。"""
    result = pd.Series([0.0] * len(numerator), index=numerator.index)
    mask = denominator != 0
    result.loc[mask] = numerator.loc[mask] / denominator.loc[mask] * scale
    return result.round(4)


def weighted_or_mean(grouped: pd.core.groupby.DataFrameGroupBy, column: str) -> pd.Series:
    """留存等比例字段先取均值；未来可扩展为按 new_users 加权。"""
    return grouped[column].mean().fillna(0)


def aggregate_base(df: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    """通用聚合：按维度汇总常见数值字段。"""
    grouped = df.groupby(dimensions, as_index=False, dropna=False)
    agg = grouped.agg({
        "dau": "sum",
        "new_users": "sum",
        "revenue": "sum",
        "ad_revenue": "sum",
        "iap_revenue": "sum",
        "impressions": "sum",
        "spend": "sum",
        "installs": "sum",
        "d1_retention": "mean",
        "d3_retention": "mean",
        "d7_retention": "mean",
        "d14_retention": "mean",
        "d30_retention": "mean",
    })
    return agg


def build_daily_overview(df: pd.DataFrame) -> pd.DataFrame:
    """构建日概览 mart。"""
    mart = aggregate_base(df, ["date", "project"])
    mart["iap_revenue"] = mart["revenue"] - mart["ad_revenue"]
    mart["arpdau"] = safe_divide(mart["revenue"], mart["dau"])
    mart["ecpm"] = safe_divide(mart["ad_revenue"], mart["impressions"], scale=1000)
    mart["impressions_per_dau"] = safe_divide(mart["impressions"], mart["dau"])
    return mart[MART_SCHEMAS["mart_daily_overview.csv"]]


def build_country_daily(df: pd.DataFrame) -> pd.DataFrame:
    """构建国家×平台日 mart。"""
    mart = aggregate_base(df, ["date", "project", "country", "platform"])
    mart["arpdau"] = safe_divide(mart["revenue"], mart["dau"])
    mart["ecpm"] = safe_divide(mart["ad_revenue"], mart["impressions"], scale=1000)
    mart["impressions_per_dau"] = safe_divide(mart["impressions"], mart["dau"])
    return mart[MART_SCHEMAS["mart_country_daily.csv"]]


def build_platform_daily(df: pd.DataFrame) -> pd.DataFrame:
    """构建平台日 mart。"""
    mart = aggregate_base(df, ["date", "project", "platform"])
    mart["arpdau"] = safe_divide(mart["revenue"], mart["dau"])
    mart["ecpm"] = safe_divide(mart["ad_revenue"], mart["impressions"], scale=1000)
    return mart[MART_SCHEMAS["mart_platform_daily.csv"]]


def build_ad_placement_daily(df: pd.DataFrame) -> pd.DataFrame:
    """构建广告位日 mart。"""
    dimensions = ["date", "project", "platform", "country", "ad_network", "ad_placement", "ad_type"]
    mart = df.groupby(dimensions, as_index=False, dropna=False).agg({
        "ad_revenue": "sum",
        "impressions": "sum",
    })
    mart = mart.rename(columns={"ad_revenue": "revenue"})
    mart["ecpm"] = safe_divide(mart["revenue"], mart["impressions"], scale=1000)
    return mart[MART_SCHEMAS["mart_ad_placement_daily.csv"]]


def build_campaign_daily(df: pd.DataFrame) -> pd.DataFrame:
    """构建投放活动日 mart。"""
    dimensions = ["date", "project", "platform", "country", "channel", "campaign"]
    mart = df.groupby(dimensions, as_index=False, dropna=False).agg({
        "spend": "sum",
        "installs": "sum",
        "revenue": "sum",
    })
    mart["cpi"] = safe_divide(mart["spend"], mart["installs"])
    mart["d0_roas"] = safe_divide(mart["revenue"], mart["spend"])
    mart["d1_roas"] = mart["d0_roas"]
    mart["d7_roas"] = mart["d0_roas"]
    return mart[MART_SCHEMAS["mart_campaign_daily.csv"]]


def build_retention_daily(df: pd.DataFrame) -> pd.DataFrame:
    """构建留存 cohort mart。"""
    dimensions = ["date", "project", "install_date", "platform", "country", "channel"]
    mart = df.groupby(dimensions, as_index=False, dropna=False).agg({
        "new_users": "sum",
        "d1_retention": "mean",
        "d3_retention": "mean",
        "d7_retention": "mean",
        "d14_retention": "mean",
        "d30_retention": "mean",
    })
    return mart[MART_SCHEMAS["mart_retention_daily.csv"]]


def build_version_daily(df: pd.DataFrame) -> pd.DataFrame:
    """构建版本日 mart。"""
    dimensions = ["date", "project", "version", "platform"]
    mart = df.groupby(dimensions, as_index=False, dropna=False).agg({
        "dau": "sum",
        "new_users": "sum",
        "revenue": "sum",
        "d1_retention": "mean",
        "d7_retention": "mean",
    })
    return mart[MART_SCHEMAS["mart_version_daily.csv"]]


def write_mart(filename: str, df: pd.DataFrame) -> None:
    """按固定字段顺序写出 mart CSV。"""
    output_path = MART_DIR / filename
    columns = MART_SCHEMAS[filename]
    MART_DIR.mkdir(parents=True, exist_ok=True)

    if df.empty:
        df = pd.DataFrame(columns=columns)
    else:
        df = df[columns].copy()
        df = df.sort_values([column for column in ["date", "project", "country", "platform"] if column in df.columns])
        for column in df.columns:
            if column in INTEGER_FIELDS:
                df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).round(0).astype(int)
            elif column in MONEY_FIELDS:
                df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).round(2)
            elif column in RATIO_FIELDS:
                df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).round(4)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"输出: {relative(output_path)}，{len(df)} rows")


def write_empty_marts() -> None:
    """没有 clean 数据时，生成所有空 mart 表头文件。"""
    for filename, columns in MART_SCHEMAS.items():
        write_mart(filename, pd.DataFrame(columns=columns))


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Build mart CSV files from clean CSV files.")
    add_project_arg(parser)
    return parser.parse_args()


def configure_paths(project_id: str | None) -> None:
    """根据项目 ID 配置 clean/mart 路径。"""
    global CLEAN_DIR, MART_DIR
    paths = ensure_project_dirs(project_id)
    CLEAN_DIR = paths["clean_dir"]
    MART_DIR = paths["mart_dir"]
    print(f"Project: {paths['project_id']}")
    print(f"Clean dir: {CLEAN_DIR}")
    print(f"Mart dir: {MART_DIR}")


def main() -> None:
    """主入口：读取 clean CSV 并生成所有 mart 表。"""
    args = parse_args()
    configure_paths(args.project)

    print("开始构建 mart 数据...")

    mappings = load_field_mappings()
    print("[1/3] 扫描 data/clean/*/*.csv")
    csv_files = sorted(CLEAN_DIR.glob("*/*.csv"))
    if not csv_files:
        write_empty_marts()
        print("未发现 clean CSV，已生成空 mart CSV。")
        return

    print(f"发现 {len(csv_files)} 个 clean CSV")

    print("[2/3] 读取并合并 clean 数据")
    frames: list[pd.DataFrame] = []
    for csv_path in csv_files:
        raw_df = read_clean_csv(csv_path)
        if raw_df is None:
            continue

        print(f"读取 {relative(csv_path)}，{len(raw_df)} rows")
        prepared = prepare_standard_frame(raw_df, csv_path, mappings)
        if prepared.empty:
            continue
        frames.append(prepared)

    if not frames:
        write_empty_marts()
        print("clean CSV 均无有效数据，已生成空 mart CSV。")
        return

    all_clean = pd.concat(frames, ignore_index=True)

    print("[3/3] 聚合生成 mart CSV")
    builders = {
        "mart_daily_overview.csv": build_daily_overview,
        "mart_country_daily.csv": build_country_daily,
        "mart_platform_daily.csv": build_platform_daily,
        "mart_ad_placement_daily.csv": build_ad_placement_daily,
        "mart_campaign_daily.csv": build_campaign_daily,
        "mart_retention_daily.csv": build_retention_daily,
        "mart_version_daily.csv": build_version_daily,
    }

    for filename, builder in builders.items():
        mart_df = builder(all_clean)
        write_mart(filename, mart_df)

    print("完成。")


if __name__ == "__main__":
    main()
