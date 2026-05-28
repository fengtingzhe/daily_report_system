"""
GA4 Data API 拉数脚本。

本脚本只负责 GA4 API -> raw CSV，不会进入 clean/mart/Tableau 正式流程。
配置读取 config/api_sources.yaml；真实密钥和服务账号 JSON 不应提交到 Git。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs


CONFIG_PATH = PROJECT_ROOT / "config" / "api_sources.yaml"
MAX_ROWS = 100_000


@dataclass(frozen=True)
class ReportSpec:
    """描述一张 GA4 报表的请求和输出结构。"""

    name: str
    dimensions: list[str]
    metrics: list[str]
    output_fields: list[str]
    field_map: dict[str, str]


REPORTS = [
    ReportSpec(
        name="daily_overview",
        dimensions=["date"],
        metrics=[
            "activeUsers",
            "newUsers",
            "sessions",
            "eventCount",
            "screenPageViews",
            "engagedSessions",
        ],
        output_fields=[
            "date",
            "active_users",
            "new_users",
            "sessions",
            "event_count",
            "screen_page_views",
            "engaged_sessions",
        ],
        field_map={
            "date": "date",
            "activeUsers": "active_users",
            "newUsers": "new_users",
            "sessions": "sessions",
            "eventCount": "event_count",
            "screenPageViews": "screen_page_views",
            "engagedSessions": "engaged_sessions",
        },
    ),
    ReportSpec(
        name="country_platform_daily",
        dimensions=["date", "country", "operatingSystem"],
        metrics=["activeUsers", "newUsers", "sessions", "eventCount"],
        output_fields=[
            "date",
            "country",
            "platform",
            "active_users",
            "new_users",
            "sessions",
            "event_count",
        ],
        field_map={
            "date": "date",
            "country": "country",
            "operatingSystem": "platform",
            "activeUsers": "active_users",
            "newUsers": "new_users",
            "sessions": "sessions",
            "eventCount": "event_count",
        },
    ),
    ReportSpec(
        name="event_daily",
        dimensions=["date", "eventName"],
        metrics=["eventCount", "activeUsers"],
        output_fields=["date", "event_name", "event_count", "active_users"],
        field_map={
            "date": "date",
            "eventName": "event_name",
            "eventCount": "event_count",
            "activeUsers": "active_users",
        },
    ),
]


def relative_path(path: Path) -> str:
    """把仓库内路径显示为相对路径，日志更短也更易读。"""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_config() -> dict[str, Any] | None:
    """读取真实 API 配置；不存在时返回 None，由 main 安全跳过。"""
    if not CONFIG_PATH.exists():
        print("config/api_sources.yaml not found. Copy config/api_sources.example.yaml first.")
        return None

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    if not isinstance(loaded, dict):
        print("ERROR: config/api_sources.yaml must be a YAML mapping.")
        return None
    return loaded


def resolve_local_path(raw_path: str) -> Path:
    """支持绝对路径、~ 路径，以及相对仓库根目录的路径。"""
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def safe_date_for_filename(date_text: str) -> str:
    """把 7daysAgo/yesterday/YYYY-MM-DD 等日期文本转成文件名安全片段。"""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(date_text).strip())
    return cleaned.strip("-") or "unknown"


def build_output_path(output_dir: Path, report_name: str, start_date: str, end_date: str) -> Path:
    """生成带日期范围的 raw CSV 文件名。"""
    safe_start = safe_date_for_filename(start_date)
    safe_end = safe_date_for_filename(end_date)
    return output_dir / f"ga4_{report_name}_{safe_start}_to_{safe_end}.csv"


def normalize_ga4_date(value: str) -> str:
    """GA4 date 通常是 YYYYMMDD，写 CSV 前转成 YYYY-MM-DD。"""
    value = str(value or "").strip()
    if re.fullmatch(r"\d{8}", value):
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    if value:
        print(f"WARNING: Could not parse GA4 date: {value}")
    return value


def write_csv(output_path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    """用 utf-8-sig 输出 CSV；无数据时也写表头。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def response_to_rows(response: Any, spec: ReportSpec) -> list[dict[str, Any]]:
    """把 GA4 API response 转成固定字段的 dict 列表。"""
    rows: list[dict[str, Any]] = []

    for row in response.rows:
        output_row = {field: "" for field in spec.output_fields}

        for index, dimension_name in enumerate(spec.dimensions):
            output_field = spec.field_map[dimension_name]
            value = row.dimension_values[index].value if index < len(row.dimension_values) else ""
            if output_field == "date":
                value = normalize_ga4_date(value)
            output_row[output_field] = value

        for index, metric_name in enumerate(spec.metrics):
            output_field = spec.field_map[metric_name]
            value = row.metric_values[index].value if index < len(row.metric_values) else "0"
            output_row[output_field] = value or "0"

        rows.append(output_row)

    return rows


def fetch_report(
    client: Any,
    property_id: str,
    spec: ReportSpec,
    start_date: str,
    end_date: str,
) -> Any:
    """执行单张 GA4 报表请求。"""
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=name) for name in spec.dimensions],
        metrics=[Metric(name=name) for name in spec.metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        limit=MAX_ROWS,
    )
    return client.run_report(request)


def print_report_plan(output_dir: Path, start_date: str, end_date: str, enabled_reports: set[str]) -> None:
    """dry-run 输出请求计划，不调用 API，不写 CSV。"""
    for index, spec in enumerate(REPORTS, start=1):
        if spec.name not in enabled_reports:
            print(f"[{index}/3] SKIP {spec.name}: disabled in config.")
            continue

        output_path = build_output_path(output_dir, spec.name, start_date, end_date)
        print(f"[{index}/3] Plan {spec.name}")
        print(f"  Dimensions: {', '.join(spec.dimensions)}")
        print(f"  Metrics: {', '.join(spec.metrics)}")
        print(f"  Output: {relative_path(output_path)}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Fetch GA4 Data API reports to raw CSV.")
    add_project_arg(parser)
    parser.add_argument("--dry-run", action="store_true", help="Validate config and print request plan only.")
    return parser.parse_args()


def main() -> None:
    """GA4 API 拉数入口。"""
    args = parse_args()
    paths = ensure_project_dirs(args.project)
    project_id = paths["project_id"]
    output_dir = paths["raw_ga4_dir"]

    print("GA4 API fetch")
    print(f"Project: {project_id}")
    print(f"Output dir: {relative_path(output_dir)}")

    loaded_config = load_config()
    if loaded_config is None:
        return

    ga4_config = loaded_config.get("ga4", {})
    if not isinstance(ga4_config, dict) or not ga4_config.get("enabled", False):
        print("GA4 API is disabled. Skipped.")
        return

    property_id = str(ga4_config.get("property_id", "")).strip()
    credentials_path_text = str(ga4_config.get("credentials_path", "")).strip()
    start_date = str(ga4_config.get("start_date", "7daysAgo")).strip() or "7daysAgo"
    end_date = str(ga4_config.get("end_date", "yesterday")).strip() or "yesterday"
    report_flags = ga4_config.get("reports", {}) or {}

    enabled_reports = {
        spec.name
        for spec in REPORTS
        if bool(report_flags.get(spec.name, True))
    }

    print(f"Property ID: {property_id or '(missing)'}")
    print(f"Date range: {start_date} to {end_date}")
    print("")

    if not property_id:
        print("ERROR: ga4.property_id is required. Use the numeric GA4 Property ID without properties/.")
        return

    if not credentials_path_text:
        print("ERROR: ga4.credentials_path is required.")
        return

    credentials_path = resolve_local_path(credentials_path_text)
    if not credentials_path.exists():
        print(f"ERROR: GA4 credentials file does not exist: {credentials_path}")
        return

    if args.dry_run:
        print("Dry run mode: no API request will be sent and no CSV will be generated.")
        print(f"Credentials file: {credentials_path}")
        print_report_plan(output_dir, start_date, end_date, enabled_reports)
        print("")
        print("GA4 dry-run completed.")
        return

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account
    except ImportError as exc:
        print("ERROR: Missing Google API dependency.")
        print("Please run: py -m pip install -r requirements.txt")
        print(f"Detail: {exc}")
        return

    try:
        credentials = service_account.Credentials.from_service_account_file(str(credentials_path))
        client = BetaAnalyticsDataClient(credentials=credentials)
    except Exception as exc:
        print(f"ERROR: Failed to initialize GA4 client: {exc}")
        return

    success_count = 0
    failed_count = 0

    for index, spec in enumerate(REPORTS, start=1):
        if spec.name not in enabled_reports:
            print(f"[{index}/3] SKIP {spec.name}: disabled in config.")
            continue

        print(f"[{index}/3] Fetch {spec.name}...")
        output_path = build_output_path(output_dir, spec.name, start_date, end_date)

        try:
            response = fetch_report(client, property_id, spec, start_date, end_date)
            rows = response_to_rows(response, spec)
            write_csv(output_path, spec.output_fields, rows)

            returned_rows = len(rows)
            row_count = int(getattr(response, "row_count", returned_rows) or returned_rows)
            if row_count > returned_rows:
                print(
                    "WARNING: GA4 response row_count is larger than returned rows. "
                    "Pagination may be needed in the future."
                )

            print(f"OK: {output_path.name}, {returned_rows} rows")
            success_count += 1
        except Exception as exc:
            print(f"ERROR: {spec.name} failed: {exc}")
            failed_count += 1

        print("")

    print(f"GA4 fetch completed. Success: {success_count}, failed: {failed_count}.")


if __name__ == "__main__":
    main()
