"""
把旧根目录模板/测试输出复制到 projects/<project_id>。

默认 dry-run，只打印计划；加 --apply 才真正复制。
不会移动或删除旧文件，也不会复制 raw/clean/mart/reports/pdf 等运行数据。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.project_paths import add_project_arg, ensure_project_dirs


COPY_ITEMS = [
    ("data/tableau_datasource/*.csv", "tableau_datasource_dir"),
    ("ai/context/daily_ai_context.json", "ai_context_dir"),
    ("ai/draft/daily_report_draft.md", "ai_draft_dir"),
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Copy root templates into a project directory.")
    add_project_arg(parser)
    parser.add_argument("--apply", action="store_true", help="Actually copy files.")
    return parser.parse_args()


def iter_copy_plan(paths: dict) -> list[tuple[Path, Path]]:
    """生成要复制的源文件和目标文件列表。"""
    plan: list[tuple[Path, Path]] = []
    for pattern, target_key in COPY_ITEMS:
        sources = sorted(PROJECT_ROOT.glob(pattern))
        for source in sources:
            if source.is_file():
                target = paths[target_key] / source.name
                plan.append((source, target))
    return plan


def main() -> None:
    """执行 dry-run 或复制。"""
    args = parse_args()
    paths = ensure_project_dirs(args.project)
    plan = iter_copy_plan(paths)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Migrate root templates to project: {paths['project_id']}")
    print(f"Mode: {mode}")

    if not plan:
        print("No source template files found to copy.")
        return

    for source, target in plan:
        rel_source = source.relative_to(PROJECT_ROOT)
        rel_target = target.relative_to(PROJECT_ROOT)
        if args.apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            print(f"COPIED: {rel_source} -> {rel_target}")
        else:
            print(f"PLAN: {rel_source} -> {rel_target}")

    if not args.apply:
        print("Dry-run only. Add --apply to copy these files.")


if __name__ == "__main__":
    main()
