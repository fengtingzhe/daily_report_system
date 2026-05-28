"""
列出 projects/ 下的所有项目。
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = PROJECT_ROOT / "projects"


def load_project_name(project_yaml: Path) -> str:
    """读取项目显示名。"""
    try:
        with open(project_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return str(data.get("project_name", ""))
    except Exception:
        return ""


def main() -> None:
    """扫描 projects/*/project.yaml 并打印表格。"""
    print(f"{'Project ID':<16} {'Project Name':<18} Path")
    if not PROJECTS_DIR.exists():
        print("(no projects directory found)")
        return

    project_files = sorted(PROJECTS_DIR.glob("*/project.yaml"))
    if not project_files:
        print("(no projects found)")
        return

    for project_yaml in project_files:
        project_id = project_yaml.parent.name
        project_name = load_project_name(project_yaml)
        rel_path = project_yaml.parent.relative_to(PROJECT_ROOT)
        print(f"{project_id:<16} {project_name:<18} {rel_path}")


if __name__ == "__main__":
    main()
