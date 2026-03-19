#!/usr/bin/env python3
"""Skills Clean Cache - Remove cached files created by skills at runtime.

All skills store cached files under a unified per-user cache directory:
    macOS:   ~/Library/Caches/mythril-skills-cache/
    Linux:   ${XDG_CACHE_HOME:-~/.cache}/mythril-skills-cache/
    Windows: %LOCALAPPDATA%\\mythril-skills-cache\\

The cache contains two categories:
  - **Temp files** (images, exports, etc.) — ephemeral, safe to delete anytime
  - **Repo cache** (git-repo-cache/) — long-lived, shared across skills,
    reusable across sessions; deleting forces re-clone on next use

This command scans the cache, shows what's there (distinguishing the two
categories), and lets the user selectively or fully clean it up.

Usage:
    skills-clean-cache          # Interactive: list + confirm
    skills-clean-cache --force  # Delete without confirmation
    skills-clean-cache --show-repos  # Show cached repo list (name + size)
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

CACHE_DIR_NAME = "mythril-skills-cache"
REPO_CACHE_DIR = "git-repo-cache"

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def get_cache_root() -> Path:
    """Return the unified per-user skill cache root directory."""
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        base = home / "Library" / "Caches"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        else:
            base = home / "AppData" / "Local"
    else:
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            base = Path(xdg_cache_home)
        else:
            base = home / ".cache"

    return base / CACHE_DIR_NAME


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
    total = 0
    for f in path.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def count_items(path: Path) -> int:
    """Count immediate children (files + dirs) in a directory."""
    return sum(1 for _ in path.iterdir()) if path.is_dir() else 0


def count_repos(repo_cache_path: Path) -> int:
    """Count cached git repos by looking for .git directories."""
    repos_dir = repo_cache_path / "repos"
    if not repos_dir.exists():
        return 0
    return sum(1 for p in repos_dir.rglob(".git") if p.is_dir())


def list_one_level(path: Path) -> list[Path]:
    """Return immediate directory contents, files first."""
    return sorted(
        path.iterdir(),
        key=lambda p: (0 if p.is_file() else 1, p.name.lower()),
    )


def list_cached_repos(repo_cache_path: Path) -> list[tuple[str, int]]:
    """List cached repos as <host>/<owner>/<repo> with their sizes."""
    repos_root = repo_cache_path / "repos"
    if not repos_root.exists():
        return []

    repos: list[tuple[str, int]] = []
    for repo_dir in repos_root.glob("*/*/*"):
        if not repo_dir.is_dir():
            continue
        if not (repo_dir / ".git").exists():
            continue
        repo_rel = repo_dir.relative_to(repos_root).as_posix()
        repos.append((repo_rel, dir_size(repo_dir)))

    repos.sort(key=lambda item: item[0].lower())
    return repos


def main() -> None:
    force = "--force" in sys.argv
    show_repos = "--show-repos" in sys.argv

    cache_root = get_cache_root()

    if not cache_root.exists():
        print(f"No skill cache found at {cache_root}/")
        print("Nothing to clean.")
        return

    all_dirs = sorted(p for p in cache_root.iterdir() if p.is_dir())
    loose_files = sorted(p for p in cache_root.iterdir() if p.is_file())

    if not all_dirs and not loose_files:
        print(f"Cache directory is empty: {cache_root}/")
        print("Nothing to clean.")
        return

    repo_cache = cache_root / REPO_CACHE_DIR
    has_repo_cache = repo_cache.exists() and any(repo_cache.iterdir())

    temp_dirs = [d for d in all_dirs if d.name != REPO_CACHE_DIR]

    print(f"\n{BOLD}=== Skill Cache Contents ==={NC}")
    print(f"  Location: {DIM}{cache_root}/{NC}\n")

    temp_size = 0
    repo_size = 0

    if temp_dirs or loose_files:
        print(f"  {BOLD}Temp files{NC} {DIM}(ephemeral, safe to delete){NC}")
        for d in temp_dirs:
            size = dir_size(d)
            items = count_items(d)
            temp_size += size
            print(
                f"    {d.name}/"
                f"  {DIM}({items} item{'s' if items != 1 else ''},"
                f" {format_size(size)}){NC}"
            )
        for f in loose_files:
            size = f.stat().st_size
            temp_size += size
            print(f"    {f.name}  {DIM}({format_size(size)}){NC}")
        print()

    if has_repo_cache:
        repo_size = dir_size(repo_cache)
        num_repos = count_repos(repo_cache)
        print(
            f"  {BOLD}Repo cache{NC}"
            f" {DIM}(shared across skills, reusable across sessions){NC}"
        )
        print(
            f"    {REPO_CACHE_DIR}/"
            f"  {DIM}({num_repos} repo{'s' if num_repos != 1 else ''},"
            f" {format_size(repo_size)}){NC}"
        )

        if show_repos:
            repo_children = list_one_level(repo_cache)
            for child in repo_children:
                if child.is_dir():
                    if child.name == "repos":
                        cached_repos = list_cached_repos(repo_cache)
                        repo_count = len(cached_repos)
                        print(
                            f"      {child.name}/"
                            f"  {DIM}({repo_count} repo"
                            f"{'s' if repo_count != 1 else ''}){NC}"
                        )
                        for repo_rel, repo_dir_size in cached_repos:
                            print(
                                f"        {repo_rel}/"
                                f"  {DIM}({format_size(repo_dir_size)}){NC}"
                            )
                    else:
                        items = count_items(child)
                        print(
                            f"      {child.name}/"
                            f"  {DIM}({items} item{'s' if items != 1 else ''}){NC}"
                        )
                else:
                    try:
                        size = child.stat().st_size
                    except OSError:
                        size = 0
                    print(f"      {child.name}  {DIM}({format_size(size)}){NC}")
        print()

    total_size = temp_size + repo_size
    print(f"  {BOLD}Total: {format_size(total_size)}{NC}")

    if total_size == 0:
        print(f"\n{DIM}Cache is empty, nothing to delete.{NC}")
        return

    if not force:
        if has_repo_cache and temp_dirs:
            print(
                f"\n{CYAN}Tip:{NC} To remove only temp files and keep the"
                f" repo cache, answer {BOLD}t{NC}."
            )
            print(f"     To remove only the repo cache, answer {BOLD}r{NC}.")
            try:
                answer = (
                    input(
                        f"\n{YELLOW}Delete: [a]ll / [t]emp only /"
                        f" [r]epo cache only / [N]one?{NC} "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return

            if answer == "a":
                delete_temp = True
                delete_repos = True
            elif answer == "t":
                delete_temp = True
                delete_repos = False
            elif answer == "r":
                delete_temp = False
                delete_repos = True
            else:
                print("Cancelled.")
                return
        elif has_repo_cache:
            try:
                answer = (
                    input(
                        f"\n{YELLOW}Delete repo cache?"
                        f" (will need to re-clone on next use){NC} [y/N] "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return
            if answer != "y":
                print("Cancelled.")
                return
            delete_temp = False
            delete_repos = True
        else:
            try:
                answer = (
                    input(f"\n{YELLOW}Delete all cached files?{NC} [y/N] ")
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return
            if answer != "y":
                print("Cancelled.")
                return
            delete_temp = True
            delete_repos = False
    else:
        delete_temp = True
        delete_repos = True

    cleaned_size = 0

    if delete_temp:
        for d in temp_dirs:
            try:
                shutil.rmtree(d)
                cleaned_size += dir_size(d) if d.exists() else 0
            except Exception as e:
                print(
                    f"{RED}Failed to delete {d.name}/: {e}{NC}",
                    file=sys.stderr,
                )
        for f in loose_files:
            try:
                f.unlink()
            except Exception as e:
                print(
                    f"{RED}Failed to delete {f.name}: {e}{NC}",
                    file=sys.stderr,
                )
        cleaned_size += temp_size

    if delete_repos and has_repo_cache:
        try:
            shutil.rmtree(repo_cache)
            cleaned_size += repo_size
        except Exception as e:
            print(
                f"{RED}Failed to delete {REPO_CACHE_DIR}/: {e}{NC}",
                file=sys.stderr,
            )

    parts: list[str] = []
    if delete_temp and (temp_dirs or loose_files):
        parts.append("temp files")
    if delete_repos and has_repo_cache:
        parts.append("repo cache")

    what = " and ".join(parts) if parts else "cache"
    print(f"\n{GREEN}Cleaned up {format_size(cleaned_size)} ({what}).{NC}")


if __name__ == "__main__":
    main()
