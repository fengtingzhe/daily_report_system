"""
多项目路径解析工具。

所有真实流程脚本都应通过这里获取项目目录，避免把路径写死在仓库根目录。
旧的根目录 data/ai/reports 结构仍保留给测试流程和兼容用途。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECT_ID = "default"


def normalize_project_id(project_id: str | None) -> str:
    """把空项目 ID 统一为 default。"""
    if project_id is None:
        return DEFAULT_PROJECT_ID
    project_id = project_id.strip()
    return project_id or DEFAULT_PROJECT_ID


def get_project_root(project_id: str | None) -> Path:
    """返回 projects/<project_id> 的绝对路径。"""
    project_id = normalize_project_id(project_id)
    return PROJECT_ROOT / "projects" / project_id


def get_project_paths(project_id: str | None) -> dict[str, Any]:
    """返回某个项目的常用路径。"""
    project_id = normalize_project_id(project_id)
    project_root = get_project_root(project_id)

    return {
        "project_id": project_id,
        "project_root": project_root,
        "project_config": project_root / "project.yaml",
        "raw_dir": project_root / "data" / "raw",
        "raw_unity_dir": project_root / "data" / "raw" / "unity",
        "raw_applovin_dir": project_root / "data" / "raw" / "applovin",
        "raw_ga4_dir": project_root / "data" / "raw" / "ga4",
        "clean_dir": project_root / "data" / "clean",
        "clean_unity_dir": project_root / "data" / "clean" / "unity",
        "clean_applovin_dir": project_root / "data" / "clean" / "applovin",
        "clean_ga4_dir": project_root / "data" / "clean" / "ga4",
        "mart_dir": project_root / "data" / "mart",
        "tableau_datasource_dir": project_root / "data" / "tableau_datasource",
        "ai_context_dir": project_root / "ai" / "context",
        "ai_draft_dir": project_root / "ai" / "draft",
        "reports_dir": project_root / "reports",
        "pdf_dir": project_root / "reports" / "pdf",
        "email_dir": project_root / "reports" / "email",
        "tableau_dir": project_root / "tableau",
        "logs_dir": project_root / "logs",
    }


def ensure_project_dirs(project_id: str | None) -> dict[str, Any]:
    """创建项目运行所需目录，并返回路径字典。"""
    paths = get_project_paths(project_id)
    for key in [
        "raw_unity_dir",
        "raw_applovin_dir",
        "raw_ga4_dir",
        "clean_unity_dir",
        "clean_applovin_dir",
        "clean_ga4_dir",
        "mart_dir",
        "tableau_datasource_dir",
        "ai_context_dir",
        "ai_draft_dir",
        "pdf_dir",
        "email_dir",
        "tableau_dir",
        "logs_dir",
    ]:
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths


def default_project_config(project_id: str | None) -> dict[str, Any]:
    """生成默认项目配置。"""
    project_id = normalize_project_id(project_id)
    return {
        "project_id": project_id,
        "project_name": "项目A",
        "timezone": "Asia/Shanghai",
        "currency": "USD",
        "tableau_workbook": "",
    }


def load_project_config(project_id: str | None) -> dict[str, Any]:
    """读取 projects/<project_id>/project.yaml；不存在时返回默认配置。"""
    project_id = normalize_project_id(project_id)
    paths = get_project_paths(project_id)
    config = default_project_config(project_id)

    config_path = paths["project_config"]
    if not config_path.exists():
        return config

    with open(config_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    if isinstance(loaded, dict):
        config.update(loaded)
    config["project_id"] = project_id
    return config


def add_project_arg(parser: argparse.ArgumentParser) -> None:
    """给 argparse parser 增加统一的 --project 参数。"""
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT_ID,
        help="Project ID under projects/. Default: default",
    )
