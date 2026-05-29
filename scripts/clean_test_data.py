"""
Clean test/temporary data from the daily_report_system project.
Safely removes: raw/clean/mart CSVs, AI context/drafts, PDFs, logs.
Preserves: .gitkeep files, scripts, configs, web_console, tableau templates, secrets.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(str(PROJECT_ROOT))

# ------------------------------
# Phase 1: Collect files to delete
# ------------------------------

DELETE_TARGETS = []

def add_glob(pattern, excludes=None):
    """Collect files matching a glob pattern, excluding listed names."""
    excludes = excludes or []
    for p in Path().glob(pattern):
        if p.is_file() and p.name not in excludes:
            DELETE_TARGETS.append(p)

def add_rglob(directory, glob_pattern, excludes=None):
    """Recursively collect files in directory matching pattern."""
    excludes = excludes or []
    d = Path(directory)
    if not d.exists():
        return
    for p in d.rglob(glob_pattern):
        if p.is_file() and p.name not in excludes:
            DELETE_TARGETS.append(p)

# 1. Raw data CSVs (keep .gitkeep)
add_rglob("projects/default/data/raw", "*.csv")

# 2. Clean data CSVs (keep .gitkeep)
add_rglob("projects/default/data/clean", "*.csv")

# 3. Mart data CSVs (keep .gitkeep)
add_rglob("projects/default/data/mart", "*.csv")

# 4. AI context JSON files (keep .gitkeep)
add_rglob("ai/context", "*.json")

# 5. AI draft MD files (keep .gitkeep)
add_rglob("ai/draft", "*.md")

# 6. PDF reports (keep .gitkeep)
add_rglob("reports", "*.pdf")

# 7. Log files (keep .gitkeep)
add_rglob("logs", "*.log")

# 8. temp directory — nothing beyond .gitkeep, skip
# 9. archive directory — only .gitkeep, skip (user said optional)

# ------------------------------
# Phase 2: Safety check
# ------------------------------

print("=" * 60)
print("  Daily Report System — Clean Test Data")
print("=" * 60)
print(f"  Project root: {PROJECT_ROOT}")
print(f"  Files to delete: {len(DELETE_TARGETS)}")
print("=" * 60)

if not DELETE_TARGETS:
    print("\nNo test/temp files found. Project is already clean.")
    exit(0)

print("\nFiles to be deleted:")
for i, f in enumerate(sorted(DELETE_TARGETS), 1):
    print(f"  [{i:02d}] {f}")

# Security: ensure all paths are within the project root
for f in DELETE_TARGETS:
    abs_path = f.resolve()
    if not str(abs_path).startswith(str(PROJECT_ROOT.resolve())):
        print(f"\nERROR: Path outside project root — {abs_path}")
        exit(1)

# ------------------------------
# Phase 3: Confirm and delete
# ------------------------------

print(f"\nProceed with deletion? (y/n): ", end="")
answer = input().strip().lower()
if answer not in ("y", "yes"):
    print("Aborted.")
    exit(0)

deleted = []
errors = []

for f in DELETE_TARGETS:
    try:
        f.unlink()
        deleted.append(f)
        print(f"  DELETED: {f}")
    except Exception as e:
        errors.append((f, e))
        print(f"  ERROR: {f} — {e}")

# ------------------------------
# Phase 4: Summary
# ------------------------------

print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
print(f"  Deleted: {len(deleted)} files")
print(f"  Errors:  {len(errors)}")

if errors:
    print("\nErrors:")
    for f, e in errors:
        print(f"  {f} — {e}")

# Verify project cleanliness
remaining = []
for pattern in ["projects/default/data/raw/**/*.csv",
                "projects/default/data/clean/**/*.csv",
                "projects/default/data/mart/**/*.csv",
                "ai/context/*.json",
                "ai/draft/*.md",
                "reports/**/*.pdf",
                "logs/*.log"]:
    for p in Path().glob(pattern):
        if p.is_file():
            remaining.append(p)

if remaining:
    print(f"\nRemaining test files ({len(remaining)}):")
    for f in remaining:
        print(f"  {f}")
else:
    print(f"\n{'=' * 60}")
    print("  Project is CLEAN — all test data removed.")
    print(f"{'=' * 60}")
