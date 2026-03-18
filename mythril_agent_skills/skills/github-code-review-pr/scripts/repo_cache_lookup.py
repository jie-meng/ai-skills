#!/usr/bin/env python3
"""Look up a git repo in the shared skill cache (git-repo-cache).

Read-only lookup into the cache maintained by git-repo-reader's
repo_manager.py. Prints the cached repo's local path if found, or
exits with code 1 if not cached. Never clones or modifies the cache.

Usage:
    python3 scripts/repo_cache_lookup.py "https://github.com/owner/repo"

Exit codes:
    0 — cache hit, local path printed to stdout
    1 — cache miss (repo not cached or directory missing)

Uses only Python 3.10+ standard library (zero dependencies).
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

CACHE_DIR_NAME = "git-repo-cache"


def get_cache_root() -> Path:
    """Return the shared repo cache root (symlink-resolved)."""
    return (
        Path(tempfile.gettempdir()).resolve()
        / "mythril-skills-cache"
        / CACHE_DIR_NAME
    )


def parse_repo_url(url: str) -> tuple[str, str, str]:
    """Parse a git URL into (host, owner, repo)."""
    url = url.strip()

    ssh_match = re.match(r"^git@([^:]+):(.+?)(?:\.git)?$", url)
    if ssh_match:
        host = ssh_match.group(1)
        parts = ssh_match.group(2).strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        return host, "/".join(parts[:-1]), parts[-1]

    https_match = re.match(r"^https?://([^/]+)/(.+?)(?:\.git)?/?$", url)
    if https_match:
        host = https_match.group(1)
        parts = https_match.group(2).strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        return host, "/".join(parts[:-1]), parts[-1]

    raise ValueError(f"Unrecognized git URL format: {url}")


def normalize_key(url: str) -> str:
    """Normalized cache key — matches repo_manager.py's format."""
    host, owner, repo = parse_repo_url(url)
    return f"{host}/{owner}/{repo}"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: repo_cache_lookup.py <repo-url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]

    try:
        key = normalize_key(url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    map_path = get_cache_root() / "repo_map.json"
    if not map_path.exists():
        sys.exit(1)

    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        sys.exit(1)

    path_str = data.get(key) if isinstance(data, dict) else None
    if not path_str:
        sys.exit(1)

    local_path = Path(path_str)
    if not local_path.exists() or not (local_path / ".git").is_dir():
        sys.exit(1)

    print(str(local_path))


if __name__ == "__main__":
    main()
