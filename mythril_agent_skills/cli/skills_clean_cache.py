#!/usr/bin/env python3
"""Skills Clean Cache - Remove temporary files created by skills at runtime.

All skills store temp files under a unified cache directory:
    ${TMPDIR:-/tmp}/mythril-skills-cache/

This command scans the cache, shows what's there, and lets the user
selectively or fully clean it up.

Usage:
    skills-clean-cache          # Interactive: list + confirm
    skills-clean-cache --force  # Delete without confirmation
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

CACHE_DIR_NAME = "mythril-skills-cache"

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def get_cache_root() -> Path:
    """Return the unified skill cache root directory."""
    return Path(tempfile.gettempdir()) / CACHE_DIR_NAME


def format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def dir_size(path: Path) -> int:
    """Calculate total size of a directory tree."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def count_items(path: Path) -> int:
    """Count immediate children (files + dirs) in a directory."""
    return sum(1 for _ in path.iterdir()) if path.is_dir() else 0


def main() -> None:
    force = "--force" in sys.argv

    cache_root = get_cache_root()

    if not cache_root.exists():
        print(f"No skill cache found at {cache_root}/")
        print("Nothing to clean.")
        return

    skill_dirs = sorted(p for p in cache_root.iterdir() if p.is_dir())
    loose_files = sorted(p for p in cache_root.iterdir() if p.is_file())

    if not skill_dirs and not loose_files:
        print(f"Cache directory is empty: {cache_root}/")
        print("Nothing to clean.")
        return

    print(f"\n{BOLD}=== Skill Cache Contents ==={NC}")
    print(f"  Location: {DIM}{cache_root}/{NC}\n")

    total_size = 0

    for d in skill_dirs:
        size = dir_size(d)
        items = count_items(d)
        total_size += size
        print(
            f"  {BOLD}{d.name}/{NC}"
            f"  {DIM}({items} item{'s' if items != 1 else ''},"
            f" {format_size(size)}){NC}"
        )

    for f in loose_files:
        size = f.stat().st_size
        total_size += size
        print(f"  {f.name}  {DIM}({format_size(size)}){NC}")

    print(f"\n  {BOLD}Total: {format_size(total_size)}{NC}")

    if total_size == 0:
        print(f"\n{DIM}Cache is empty, nothing to delete.{NC}")
        return

    if not force:
        try:
            answer = input(
                f"\n{YELLOW}Delete all cached files?{NC} [y/N] "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if answer != "y":
            print("Cancelled.")
            return

    deleted = 0
    for d in skill_dirs:
        try:
            shutil.rmtree(d)
            deleted += 1
        except Exception as e:
            print(f"{RED}Failed to delete {d.name}/: {e}{NC}", file=sys.stderr)
    for f in loose_files:
        try:
            f.unlink()
            deleted += 1
        except Exception as e:
            print(f"{RED}Failed to delete {f.name}: {e}{NC}", file=sys.stderr)

    print(f"\n{GREEN}Cleaned up {format_size(total_size)} "
          f"from {len(skill_dirs)} skill cache{'s' if len(skill_dirs) != 1 else ''}.{NC}")


if __name__ == "__main__":
    main()
