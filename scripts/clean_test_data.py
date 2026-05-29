"""
Clean test/temporary data from project directories.

Usage:
  python scripts/clean_test_data.py --dry-run --project default
  python scripts/clean_test_data.py --confirm --project default
  python scripts/clean_test_data.py --dry-run --project myproj
  python scripts/clean_test_data.py --confirm --project myproj

--dry-run   Preview files that would be deleted (no deletion).
--confirm   Actually delete files. Required for any deletion.
            dry-run always wins; no files are deleted when --dry-run is present.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure scripts/utils is importable when run from repo root
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from utils.project_paths import get_project_paths, add_project_arg, PROJECT_ROOT


CLEAN_DIR_KEYS = [
    "raw_dir",
    "clean_dir",
    "mart_dir",
    "tableau_datasource_dir",
    "ai_context_dir",
    "ai_draft_dir",
    "pdf_dir",
    "email_dir",
    "logs_dir",
    "temp_dir",
]


def collect_targets(paths: dict) -> list[Path]:
    """Recursively collect all deletable files under clean-target directories.

    Skips .gitkeep files and directories that do not exist.
    """
    targets: list[Path] = []
    for key in CLEAN_DIR_KEYS:
        d = paths[key]
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.is_file() and f.name != ".gitkeep":
                targets.append(f)
    return sorted(targets)


def print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean test/temporary data from project directories"
    )
    add_project_arg(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files that would be deleted (no deletion)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete files. Required for any deletion.",
    )
    args = parser.parse_args()

    paths = get_project_paths(args.project)
    project_id = paths["project_id"]

    # --- Collect ---
    targets = collect_targets(paths)

    print_header(f"Clean Test Data — project={project_id}")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Target dirs:  {len(CLEAN_DIR_KEYS)}")
    print(f"  Files found:  {len(targets)}")

    if not targets:
        print("\nNo test/temp files found. Project is already clean.")
        return

    # --- Preview ---
    print("\nFiles that would be deleted:")
    for i, f in enumerate(targets, 1):
        try:
            rel = f.relative_to(PROJECT_ROOT)
        except ValueError:
            rel = f
        print(f"  [{i:03d}] {rel}")

    # --- Safety: require --confirm to delete ---
    if not args.confirm:
        print()
        print("-" * 60)
        print("  DRY RUN — no files were deleted.")
        if not args.dry_run:
            print("  Re-run with --confirm to delete, or --dry-run for explicit preview.")
        print("-" * 60)
        return

    if args.dry_run:
        print()
        print("-" * 60)
        print("  DRY RUN (--dry-run + --confirm) — still preview only.")
        print("  Remove --dry-run and keep --confirm to actually delete.")
        print("-" * 60)
        return

    # --- Delete ---
    print()
    print("Deleting...")

    deleted: list[Path] = []
    skipped: list[Path] = []
    errors: list[tuple[Path, str]] = []

    for f in targets:
        try:
            f.unlink()
            deleted.append(f)
            print(f"  DELETED  {f.relative_to(PROJECT_ROOT)}")
        except PermissionError:
            skipped.append(f)
            print(f"  SKIPPED  {f.relative_to(PROJECT_ROOT)} (permission)")
        except Exception as exc:
            errors.append((f, str(exc)))
            print(f"  ERROR    {f.relative_to(PROJECT_ROOT)} — {exc}")

    # --- Summary ---
    print_header("Summary")
    print(f"  Deleted: {len(deleted)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  Errors:  {len(errors)}")

    if errors:
        print("\nErrors:")
        for f, msg in errors:
            print(f"  {f.relative_to(PROJECT_ROOT)} — {msg}")

    if not errors:
        print()
        print("  Project is CLEAN — all test data removed.")


if __name__ == "__main__":
    main()
