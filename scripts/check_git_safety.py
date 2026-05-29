"""
Check git safety — verify .gitignore covers sensitive paths and no dangerous
files are staged or unstaged.

Usage:
  python scripts/check_git_safety.py
  python scripts/check_git_safety.py --quiet   # only print warnings
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_GITIGNORE_PATTERNS = [
    "secrets/",
    "config/api_sources.yaml",
    "projects/*/data/raw/**",
    "projects/*/data/clean/**",
    "projects/*/data/mart/**",
    "projects/*/ai/context/*.json",
    "projects/*/ai/draft/*.md",
    "projects/*/reports/pdf/**",
    "projects/*/reports/email/**",
    "projects/*/logs/*.log",
    "projects/*/temp/**",
]

DANGEROUS_PATH_PATTERNS = [
    "secrets/",
    "config/api_sources.yaml",
    "/data/raw/",
    "/data/clean/",
    "/data/mart/",
    "/ai/context/",
    "/ai/draft/",
    "/reports/pdf/",
    "/reports/email/",
    "/logs/",
    "/temp/",
]

# ANSI
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def read_gitignore() -> str:
    gf = PROJECT_ROOT / ".gitignore"
    if not gf.exists():
        return ""
    return gf.read_text(encoding="utf-8")


def check_gitignore_coverage(quiet: bool) -> list[str]:
    """Return list of missing .gitignore patterns."""
    content = read_gitignore()
    missing = []
    for pat in REQUIRED_GITIGNORE_PATTERNS:
        if pat not in content:
            missing.append(pat)
    if not quiet or missing:
        print("—" * 50)
        print("[.gitignore coverage]")
        if missing:
            print(f"  {RED}MISSING patterns:{RESET}")
            for m in missing:
                print(f"    - {m}")
        else:
            print(f"  {GREEN}All {len(REQUIRED_GITIGNORE_PATTERNS)} required patterns present.{RESET}")
    return missing


def is_dangerous_path(p: str) -> bool:
    """Check if a file path matches any dangerous pattern."""
    for pat in DANGEROUS_PATH_PATTERNS:
        if pat in p:
            return True
    return False


def run_git_status() -> list[str]:
    """Run git status --short and return output lines."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception as exc:
        print(f"{RED}Failed to run git status: {exc}{RESET}")
        return []


def check_dangerous_files(quiet: bool) -> int:
    """Check git status for dangerous files. Returns count of dangerous files found."""
    lines = run_git_status()
    dangerous = []
    clean_lines = []

    for line in lines:
        # git status --short format: "XY filename" (2-char status + space + path)
        # Handle renames: "R  old -> new"
        status = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ")[-1]

        if is_dangerous_path(path):
            dangerous.append((status, path))
        else:
            clean_lines.append(line)

    if not quiet or dangerous:
        print("—" * 50)
        print("[git status --short]")
        if lines:
            for line in lines:
                print(f"  {line}")
        else:
            print(f"  {GREEN}Working tree clean.{RESET}")

    if dangerous:
        print()
        print("=" * 60)
        print(f"  {RED}DANGER: Sensitive files in git status!{RESET}")
        print("=" * 60)
        for status, path in dangerous:
            print(f"  {RED}[{status}] {path}{RESET}")
        print()
        print("  These files match sensitive paths (secrets, raw data, reports, logs, etc.).")
        print("  Review your .gitignore and ensure these are NOT committed.")
        print("=" * 60)
    elif not quiet:
        print(f"\n  {GREEN}No dangerous files in git status.{RESET}")

    return len(dangerous)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check git safety for the project")
    parser.add_argument("--quiet", action="store_true", help="Only print warnings")
    args = parser.parse_args()

    quiet = args.quiet

    if not quiet:
        print("=" * 60)
        print("  Git Safety Check")
        print(f"  Project: {PROJECT_ROOT}")
        print("=" * 60)

    missing = check_gitignore_coverage(quiet)
    dangerous_count = check_dangerous_files(quiet)

    if not quiet:
        print()
        print("=" * 60)
        if missing:
            print(f"  {YELLOW}.gitignore coverage: {len(missing)} pattern(s) missing{RESET}")
        else:
            print(f"  {GREEN}.gitignore coverage: OK{RESET}")
        if dangerous_count > 0:
            print(f"  {RED}Dangerous files: {dangerous_count} found{RESET}")
        else:
            print(f"  {GREEN}Dangerous files: 0{RESET}")
        print("=" * 60)

    if dangerous_count > 0 or missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
