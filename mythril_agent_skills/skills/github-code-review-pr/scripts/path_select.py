#!/usr/bin/env python3
"""Select the local repo access path (A / B / C / D) for a PR review.

Checks paths in order:
  A — already inside the target repo (cwd matches the PR repo)
  B — repo found in shared git-repo-reader cache
  C — no local access; caller will clone into shared cache via repo_manager.py
  D — fallback if Path C clone fails; caller does blobless sparse-clone
      into the skill's own temp cache

Prints one [PATH-CHECK] line per path and a final [PATH-SELECTED] line,
then prints machine-readable key-value lines for the caller:

    SELECTED_PATH=A|B|C|D
    REPO_PATH=<absolute-path-or-empty>

Exit codes:
    0 — always (path selection always produces a result)

Usage:
    python3 scripts/path_select.py <repo-url> [<current-repo-nameWithOwner>]

    <repo-url>                   Full repo URL, e.g.
                                 https://git.example.com/owner/repo
    <current-repo-nameWithOwner> Optional: output of
                                 `gh repo view --json nameWithOwner -q .nameWithOwner`
                                 Pass empty string "" if not inside any repo.

Output (to stdout):
    [PATH-CHECK] A: HIT|MISS - <reason>
    [PATH-CHECK] B: HIT|MISS - <reason>
    [PATH-CHECK] C: SELECTED|SKIPPED - <reason>
    [PATH-CHECK] D: SELECTED|SKIPPED - <reason>
    [PATH-SELECTED] Path A|B|C|D
    SELECTED_PATH=A|B|C|D
    REPO_PATH=<absolute-path>          # only for Path B; empty for A, C, and D

Uses only Python 3.10+ standard library (zero dependencies).
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys
from pathlib import Path


# ── cache helpers (mirrors repo_cache_lookup.py) ──────────────────────────────


def get_cache_root() -> Path:
    """Return the shared repo cache root under per-user cache."""
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        base = home / "Library" / "Caches"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else home / ".cache"
    return base / "mythril-skills-cache" / "git-repo-cache"


def parse_repo_url(url: str) -> tuple[str, str, str]:
    """Parse a git URL into (host, owner, repo)."""
    url = url.strip()
    ssh = re.match(r"^git@([^:]+):(.+?)(?:\.git)?$", url)
    if ssh:
        host = ssh.group(1)
        parts = ssh.group(2).strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        return host, "/".join(parts[:-1]), parts[-1]
    https = re.match(r"^https?://([^/]+)/(.+?)(?:\.git)?/?$", url)
    if https:
        host = https.group(1)
        parts = https.group(2).strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        return host, "/".join(parts[:-1]), parts[-1]
    raise ValueError(f"Unrecognized git URL format: {url}")


def cache_lookup(repo_url: str) -> str | None:
    """Return local path if repo is in shared cache, else None."""
    try:
        host, owner, repo = parse_repo_url(repo_url)
    except ValueError:
        return None
    key = f"{host}/{owner}/{repo}"
    map_path = get_cache_root() / "repo_map.json"
    if not map_path.exists():
        return None
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    path_str = data.get(key) if isinstance(data, dict) else None
    if not path_str:
        return None
    local = Path(path_str)
    if not local.exists() or not (local / ".git").is_dir():
        return None
    return str(local)


# ── main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: path_select.py <repo-url> [<current-repo-nameWithOwner>]",
            file=sys.stderr,
        )
        sys.exit(1)

    repo_url = sys.argv[1].strip()
    current_repo = sys.argv[2].strip() if len(sys.argv) >= 3 else ""

    # Derive owner/repo from URL for Path A comparison
    try:
        host, owner, repo_name = parse_repo_url(repo_url)
        target_name_with_owner = f"{owner}/{repo_name}"
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # ── Path A ────────────────────────────────────────────────────────────────
    if current_repo and current_repo == target_name_with_owner:
        print(
            f"[PATH-CHECK] A: HIT - cwd repo matches target ({target_name_with_owner})"
        )
        print("[PATH-CHECK] B: SKIPPED - Path A matched")
        print("[PATH-CHECK] C: SKIPPED - Path A matched")
        print("[PATH-CHECK] D: SKIPPED - Path A matched")
        print("[PATH-SELECTED] Path A")
        print("SELECTED_PATH=A")
        print("REPO_PATH=")
        return

    if current_repo:
        print(
            f"[PATH-CHECK] A: MISS - cwd repo is '{current_repo}', not '{target_name_with_owner}'"
        )
    else:
        print(
            "[PATH-CHECK] A: MISS - not inside any git repo (or gh not authenticated for cwd)"
        )

    # ── Path B ────────────────────────────────────────────────────────────────
    cached_path = cache_lookup(repo_url)
    if cached_path:
        print(f"[PATH-CHECK] B: HIT - cached at {cached_path}")
        print("[PATH-CHECK] C: SKIPPED - Path B matched")
        print("[PATH-CHECK] D: SKIPPED - Path B matched")
        print("[PATH-SELECTED] Path B")
        print("SELECTED_PATH=B")
        print(f"REPO_PATH={cached_path}")
        return

    print("[PATH-CHECK] B: MISS - repo not found in shared git-repo-cache")

    # ── Path C ────────────────────────────────────────────────────────────────
    # Clone to shared git-repo-cache via repo_manager.py sync (reusable across
    # sessions and skills). Path D is the fallback if C fails at runtime.
    cache_root = get_cache_root()
    shared_cache_dir = cache_root / "repos" / host / owner / repo_name

    print(
        f"[PATH-CHECK] C: SELECTED - will clone into shared cache at {shared_cache_dir}"
    )
    print("[PATH-CHECK] D: SKIPPED - Path C selected (D is fallback if C fails)")
    print("[PATH-SELECTED] Path C")
    print("SELECTED_PATH=C")
    print("REPO_PATH=")


if __name__ == "__main__":
    main()
