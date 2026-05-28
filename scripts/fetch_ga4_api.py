"""
GA4 API 拉数骨架。

当前默认不真实调用 API；如果 config/api_sources.yaml 未配置或 ga4.enabled=false，
脚本会安全跳过，并提示用户可先把手工导出的 CSV 放入 data/raw/ga4/。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "api_sources.yaml"
ENV_PATH = PROJECT_ROOT / ".env"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "ga4"


def load_config() -> dict:
    """读取 API 配置；没有真实配置时返回空字典。"""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    """GA4 API 拉数入口。"""
    print("GA4 API fetch")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv(ENV_PATH)

    config = load_config().get("ga4", {})
    if not config or not config.get("enabled", False):
        print("GA4 API is not configured or disabled. Skipped.")
        print("You can place manual CSV exports under data/raw/ga4/.")
        return

    credentials_path = str(config.get("credentials_path", "")).strip()
    property_id = str(config.get("property_id", "")).strip()
    if not credentials_path or not property_id:
        print("Missing GA4 credentials_path or property_id. Skipped.")
        return

    print("GA4 API config found, but real API fetching is not implemented yet.")
    print("No files were downloaded.")


if __name__ == "__main__":
    main()
