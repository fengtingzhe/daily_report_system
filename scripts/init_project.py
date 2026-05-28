"""
初始化一个新的日报项目目录。

运行示例：
    py scripts/init_project.py --project cash_game_a --name "网赚游戏 A"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import ensure_project_dirs, get_project_paths, normalize_project_id


def touch_gitkeep(directory: Path) -> None:
    """在目录中创建 .gitkeep，用于 Git 保留空目录。"""
    directory.mkdir(parents=True, exist_ok=True)
    gitkeep = directory / ".gitkeep"
    gitkeep.touch(exist_ok=True)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Initialize a new report project.")
    parser.add_argument("--project", required=True, help="Project ID, for example cash_game_a.")
    parser.add_argument("--name", default=None, help="Project display name.")
    parser.add_argument("--force", action="store_true", help="Overwrite project.yaml if it exists.")
    return parser.parse_args()


def main() -> None:
    """创建项目目录和 project.yaml。"""
    args = parse_args()
    project_id = normalize_project_id(args.project)
    project_name = args.name or project_id

    paths = ensure_project_dirs(project_id)
    keep_dirs = [
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
    ]
    for key in keep_dirs:
        touch_gitkeep(paths[key])

    config_path = paths["project_config"]
    if config_path.exists() and not args.force:
        print(f"Project already exists, project.yaml kept: {config_path}")
    else:
        config = {
            "project_id": project_id,
            "project_name": project_name,
            "timezone": "Asia/Shanghai",
            "currency": "USD",
            "tableau_workbook": "",
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        print(f"Written project config: {config_path}")

    print(f"Project initialized: {project_id}")
    print(f"Path: {get_project_paths(project_id)['project_root']}")


if __name__ == "__main__":
    main()
