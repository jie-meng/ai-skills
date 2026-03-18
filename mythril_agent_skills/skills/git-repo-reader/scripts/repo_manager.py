#!/usr/bin/env python3
"""Git repository cache manager for the git-repo-reader skill.

Clones, caches, and manages git repositories under the unified skill cache
directory. Maintains a repo_map.json mapping file so repos can be reused
across conversation sessions.

Cache layout:
    <cache-root>/
    ├── repo_map.json           # URL → local path mapping
    └── repos/
        └── <host>/<owner>/<repo>/   # deterministic path per repo

Uses only Python 3.10+ standard library (zero dependencies).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def get_cache_root() -> Path:
    """Return the cache root for this skill (symlink-resolved)."""
    return Path(tempfile.gettempdir()).resolve() / "mythril-skills-cache" / "git-repo-reader"


def get_map_path() -> Path:
    """Return path to the repo mapping file."""
    return get_cache_root() / "repo_map.json"


def get_repos_dir() -> Path:
    """Return the directory where repos are cloned."""
    return get_cache_root() / "repos"


# --- URL parsing and normalization ---


def parse_repo_url(url: str) -> tuple[str, str, str, str]:
    """Parse a git URL into (host, owner, repo, clone_url).

    Supports:
      - https://host/owner/repo[.git]
      - git@host:owner/repo[.git]

    Returns the clone URL as HTTPS unless the original was SSH.
    """
    url = url.strip()

    ssh_match = re.match(r"^git@([^:]+):(.+?)(?:\.git)?$", url)
    if ssh_match:
        host = ssh_match.group(1)
        path_part = ssh_match.group(2)
        parts = path_part.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from SSH URL: {url}")
        owner = "/".join(parts[:-1])
        repo = parts[-1]
        clone_url = url
        return host, owner, repo, clone_url

    https_match = re.match(r"^https?://([^/]+)/(.+?)(?:\.git)?/?$", url)
    if https_match:
        host = https_match.group(1)
        path_part = https_match.group(2)
        parts = path_part.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from HTTPS URL: {url}")
        owner = "/".join(parts[:-1])
        repo = parts[-1]
        clone_url = f"https://{host}/{path_part}.git"
        return host, owner, repo, clone_url

    raise ValueError(f"Unrecognized git URL format: {url}")


def normalize_key(url: str) -> str:
    """Create a normalized key for the mapping file.

    Both SSH and HTTPS URLs for the same repo produce the same key:
    e.g., 'github.com/owner/repo'
    """
    host, owner, repo, _ = parse_repo_url(url)
    return f"{host}/{owner}/{repo}"


def get_local_path(url: str) -> Path:
    """Return the deterministic local path for a repo URL."""
    host, owner, repo, _ = parse_repo_url(url)
    return get_repos_dir() / host / owner / repo


# --- Mapping file operations ---


def load_map() -> dict[str, str]:
    """Load repo_map.json. Returns empty dict if missing or corrupt."""
    map_path = get_map_path()
    if not map_path.exists():
        return {}
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_map(mapping: dict[str, str]) -> None:
    """Save repo_map.json atomically."""
    map_path = get_map_path()
    map_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = map_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(map_path)


def add_entry(url: str, local_path: Path) -> None:
    """Add or update a mapping entry."""
    mapping = load_map()
    mapping[normalize_key(url)] = str(local_path)
    save_map(mapping)


def remove_entry(url: str) -> None:
    """Remove a mapping entry if it exists."""
    mapping = load_map()
    key = normalize_key(url)
    if key in mapping:
        del mapping[key]
        save_map(mapping)


def lookup_entry(url: str) -> Path | None:
    """Look up local path for a URL. Returns None if not found."""
    mapping = load_map()
    key = normalize_key(url)
    path_str = mapping.get(key)
    if path_str:
        return Path(path_str)
    return None


# --- Git operations ---


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def git_clone(clone_url: str, target: Path, branch: str | None = None) -> None:
    """Clone a repository to the target path."""
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["clone", "--single-branch"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [clone_url, str(target)]

    result = run_git(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed:\n{result.stderr.strip()}")


def git_pull(repo_path: Path) -> None:
    """Pull latest changes in the repo."""
    result = run_git(["pull", "--ff-only"], cwd=repo_path)
    if result.returncode != 0:
        err = result.stderr.strip()
        if "Not a git repository" in err:
            raise RuntimeError(f"Not a git repository: {repo_path}")
        raise RuntimeError(f"git pull failed:\n{err}")


def git_checkout_branch(repo_path: Path, branch: str) -> None:
    """Checkout a specific branch, fetching it first if needed."""
    result = run_git(["checkout", branch], cwd=repo_path)
    if result.returncode != 0:
        fetch = run_git(["fetch", "origin", branch], cwd=repo_path)
        if fetch.returncode != 0:
            raise RuntimeError(f"Branch '{branch}' not found:\n{fetch.stderr.strip()}")
        result = run_git(["checkout", branch], cwd=repo_path)
        if result.returncode != 0:
            result = run_git(["checkout", "-b", branch, f"origin/{branch}"], cwd=repo_path)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to checkout branch '{branch}':\n{result.stderr.strip()}")


# --- Subcommands ---


def log(msg: str) -> None:
    """Print a status message to stderr so the AI and user can see what's happening."""
    print(msg, file=sys.stderr)


def cmd_clone(url: str, branch: str | None = None) -> None:
    """Clone a repo or reuse from cache. Prints the local path on success."""
    if not shutil.which("git"):
        print("ERROR: git is not installed. Run 'skills-check git-repo-reader'.", file=sys.stderr)
        sys.exit(1)

    _, _, _, clone_url = parse_repo_url(url)
    local_path = get_local_path(url)
    key = normalize_key(url)

    cached = lookup_entry(url)
    if cached and cached.exists() and (cached / ".git").is_dir():
        log(f"[cache hit] Found cached repo: {key}")
        log(f"[pull] Updating to latest...")
        try:
            git_pull(cached)
            log("[pull] Done.")
        except RuntimeError as e:
            log(f"[pull] Failed: {e}")
            log("[re-clone] Removing stale cache and cloning fresh...")
            shutil.rmtree(cached, ignore_errors=True)
            remove_entry(url)
            git_clone(clone_url, local_path, branch)
            add_entry(url, local_path)
            log(f"[re-clone] Done.")
            if branch:
                log(f"[branch] Checking out '{branch}'...")
                git_checkout_branch(local_path, branch)
                log(f"[branch] Done.")
            print(str(local_path))
            return

        if branch:
            log(f"[branch] Checking out '{branch}'...")
            git_checkout_branch(cached, branch)
            log(f"[branch] Done.")
        print(str(cached))
        return

    if cached:
        log(f"[cache stale] Mapping exists but directory missing for: {key}")
        remove_entry(url)

    if local_path.exists():
        log(f"[cleanup] Removing leftover directory: {local_path}")
        shutil.rmtree(local_path, ignore_errors=True)

    log(f"[clone] Cloning {clone_url} ...")
    git_clone(clone_url, local_path, branch)
    add_entry(url, local_path)
    log(f"[clone] Done.")
    if branch:
        log(f"[branch] On branch '{branch}'.")
    print(str(local_path))


def cmd_lookup(url: str) -> None:
    """Look up cached path for a URL. Exits 1 if not found."""
    cached = lookup_entry(url)
    if cached and cached.exists():
        print(str(cached))
    else:
        if cached:
            remove_entry(url)
        sys.exit(1)


def cmd_remove(url: str) -> None:
    """Delete a cached repo and its mapping entry."""
    key = normalize_key(url)
    local_path = get_local_path(url)
    if local_path.exists():
        log(f"[remove] Deleting {key} at {local_path} ...")
        shutil.rmtree(local_path, ignore_errors=True)
        log(f"[remove] Deleted.")
    else:
        log(f"[remove] Directory not found (already deleted?): {local_path}")

    remove_entry(url)
    print("OK")


def cmd_list() -> None:
    """List all cached repos."""
    mapping = load_map()
    if not mapping:
        print("No cached repositories.")
        return

    for key, path_str in sorted(mapping.items()):
        exists = "OK" if Path(path_str).exists() else "MISSING"
        print(f"  [{exists}] {key} → {path_str}")


def cmd_pull(url: str) -> None:
    """Pull latest changes for a cached repo."""
    cached = lookup_entry(url)
    if not cached or not cached.exists():
        print("ERROR: repo not cached. Clone it first.", file=sys.stderr)
        sys.exit(1)

    key = normalize_key(url)
    log(f"[pull] Updating {key} ...")
    git_pull(cached)
    log(f"[pull] Done.")
    print(f"Updated: {cached}")


# --- Main ---


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Git repository cache manager for git-repo-reader skill."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_clone = sub.add_parser("clone", help="Clone or reuse a cached repo")
    p_clone.add_argument("url", help="Git repository URL (HTTPS or SSH)")
    p_clone.add_argument("--branch", "-b", help="Branch to checkout")

    p_lookup = sub.add_parser("lookup", help="Look up cached path for a URL")
    p_lookup.add_argument("url", help="Git repository URL")

    p_remove = sub.add_parser("remove", help="Delete a cached repo")
    p_remove.add_argument("url", help="Git repository URL")

    sub.add_parser("list", help="List all cached repos")

    p_pull = sub.add_parser("pull", help="Pull latest changes for a cached repo")
    p_pull.add_argument("url", help="Git repository URL")

    args = parser.parse_args()

    try:
        if args.command == "clone":
            cmd_clone(args.url, args.branch)
        elif args.command == "lookup":
            cmd_lookup(args.url)
        elif args.command == "remove":
            cmd_remove(args.url)
        elif args.command == "list":
            cmd_list()
        elif args.command == "pull":
            cmd_pull(args.url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
