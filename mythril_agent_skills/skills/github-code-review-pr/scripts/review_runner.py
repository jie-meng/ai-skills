#!/usr/bin/env python3
"""Prepare and clean a guarded PR review session.

This script standardizes high-risk operational steps for github-code-review-pr:

1. Fetch PR metadata and diff exactly once (non-interactive pager disabled)
2. Run path selection (A/B/C) via path_select.py
3. Prepare local repo context with Path B fallback (pull/<PR>/head)
4. Persist all session state in a manifest JSON
5. Perform deterministic cleanup with required [PATH-CLEANUP] markers

Usage:
    python3 scripts/review_runner.py prepare <PR_URL_OR_NUMBER>
    python3 scripts/review_runner.py cleanup <manifest-path>

Output (prepare):
    [PATH-CHECK] ... lines (from path_select)
    [PATH-SELECTED] ... line (from path_select)
    RUN_MANIFEST=<path>
    PR_VIEW_JSON_PATH=<path>
    PR_DIFF_PATH=<path>
    SELECTED_PATH=A|B|C
    REPO_PATH=<path-or-empty>
    REPO_WORKDIR=<path-or-empty>
    PR_STATE=<OPEN|CLOSED|MERGED>
    CONTEXT_MODE=<full_repo|diff_only>
    CONTEXT_LIMITATION=<message-or-empty>

Output (cleanup):
    [PATH-CLEANUP] ... line(s)

Uses Python 3.10+ standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


PR_VIEW_FIELDS = (
    "number,title,body,state,author,baseRefName,headRefName,labels,reviewDecision,"
    "additions,deletions,changedFiles,commits,files,comments,reviews,url"
)


COMMAND_LOG: list[str] = []


@dataclass
class SessionManifest:
    """Serializable review session state for deterministic cleanup."""

    run_dir: str
    pr_ref: str
    pr_url: str
    repo_url: str
    host: str
    owner: str
    repo: str
    pr_number: int
    base_ref_name: str
    head_ref_name: str
    pr_state: str
    selected_path: str
    repo_path: str
    repo_workdir: str
    original_branch: str
    checkout_ref: str
    context_mode: str
    context_limitation: str
    pr_view_json_path: str
    pr_diff_path: str
    command_log_path: str
    path_select_log_path: str
    review_dir: str
    created_at_utc: str


def get_skill_cache_dir() -> Path:
    """Return github-code-review-pr cache directory for this OS user."""
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        base = home / "Library" / "Caches"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
    else:
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg_cache_home) if xdg_cache_home else home / ".cache"
    cache_dir = base / "mythril-skills-cache" / "github-code-review-pr"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def run_cmd(
    cmd: list[str],
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with non-interactive pager settings."""
    env = dict(os.environ)
    env.setdefault("GH_PAGER", "cat")
    env.setdefault("GIT_PAGER", "cat")
    env.setdefault("PAGER", "cat")
    if extra_env:
        env.update(extra_env)
    COMMAND_LOG.append(
        json.dumps(
            {
                "cmd": cmd,
                "cwd": str(cwd) if cwd else "",
                "ts_utc": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=True,
        )
    )
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=env,
    )


def parse_pr_repo_url(pr_url: str) -> tuple[str, str, str, str]:
    """Parse PR URL and return (repo_url, host, owner, repo)."""
    match = re.match(r"^(https?://[^/]+)/(.+)/pull/(\d+)(?:/.*)?$", pr_url.strip())
    if not match:
        raise ValueError(f"Cannot parse repo URL from PR URL: {pr_url}")
    root = match.group(1)
    repo_path = match.group(2).strip("/")
    path_parts = repo_path.split("/")
    if len(path_parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from PR URL: {pr_url}")
    host = root.split("//", 1)[1]
    owner = "/".join(path_parts[:-1])
    repo = path_parts[-1]
    return f"{root}/{repo_path}", host, owner, repo


def parse_key_value_output(stdout_text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines from command output."""
    result: dict[str, str] = {}
    for line in stdout_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() and key.strip().isupper():
            result[key.strip()] = value.strip()
    return result


def locate_path_select_script() -> Path:
    """Locate sibling path_select.py script from this file location."""
    script = Path(__file__).resolve().parent / "path_select.py"
    if not script.exists():
        raise FileNotFoundError(f"path_select.py not found at {script}")
    return script


def current_repo_name_with_owner() -> str:
    """Return current repo nameWithOwner via gh, or empty if unavailable."""
    cp = run_cmd(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
    )
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def current_repo_top_level() -> str:
    """Return current repo top-level path, or empty if unavailable."""
    cp = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def current_branch(repo_dir: Path) -> str:
    """Return current branch name in repo_dir, or empty when detached/unknown."""
    cp = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def ensure_checkout(
    repo_dir: Path,
    base_ref_name: str,
    head_ref_name: str,
    pr_number: int,
) -> tuple[str, str]:
    """Try branch fetch/checkout; fallback to pull/<PR>/head when needed.

    Returns:
        (checkout_ref, limitation)
        checkout_ref is empty when checkout failed and diff-only mode is required.
        limitation contains an explanation when checkout_ref is empty.
    """
    errors: list[str] = []

    fetch_cp = run_cmd(
        ["git", "fetch", "origin", base_ref_name, head_ref_name],
        cwd=repo_dir,
    )
    if fetch_cp.returncode != 0:
        errors.append(
            fetch_cp.stderr.strip() or fetch_cp.stdout.strip() or "git fetch failed"
        )

    head_ref_check = run_cmd(
        ["git", "rev-parse", "--verify", "--quiet", f"origin/{head_ref_name}"],
        cwd=repo_dir,
    )
    if head_ref_check.returncode == 0:
        checkout_cp = run_cmd(["git", "checkout", head_ref_name], cwd=repo_dir)
        if checkout_cp.returncode == 0:
            return head_ref_name, ""
        errors.append(
            checkout_cp.stderr.strip()
            or checkout_cp.stdout.strip()
            or f"git checkout {head_ref_name} failed"
        )

    fallback_ref = f"pr-{pr_number}-head"
    fallback_fetch_cp = run_cmd(
        ["git", "fetch", "origin", f"pull/{pr_number}/head:{fallback_ref}"],
        cwd=repo_dir,
    )
    if fallback_fetch_cp.returncode != 0:
        errors.append(
            fallback_fetch_cp.stderr.strip()
            or fallback_fetch_cp.stdout.strip()
            or "fallback fetch pull/<PR>/head failed"
        )
    else:
        fallback_checkout_cp = run_cmd(["git", "checkout", fallback_ref], cwd=repo_dir)
        if fallback_checkout_cp.returncode == 0:
            return fallback_ref, ""
        errors.append(
            fallback_checkout_cp.stderr.strip()
            or fallback_checkout_cp.stdout.strip()
            or f"git checkout {fallback_ref} failed"
        )

    limitation = " | ".join(e for e in errors if e)
    limitation = limitation[:4000] if limitation else "Path checkout failed"
    return "", f"Path checkout failed: {limitation}"


def prepare_session(pr_ref: str) -> int:
    """Prepare a review session and emit machine-readable outputs."""
    cache_dir = get_skill_cache_dir()
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=str(cache_dir)))

    pr_view_path = run_dir / "pr_view.json"
    pr_diff_path = run_dir / "pr.diff"
    command_log_path = run_dir / "commands.log"
    path_select_log_path = run_dir / "path_select.log"
    manifest_path = run_dir / "manifest.json"

    # Step 2: fetch metadata and diff exactly once.
    pr_view_cp = run_cmd(["gh", "pr", "view", pr_ref, "--json", PR_VIEW_FIELDS])
    if pr_view_cp.returncode != 0:
        print(pr_view_cp.stderr.strip() or pr_view_cp.stdout.strip())
        return 2
    pr_view_path.write_text(pr_view_cp.stdout, encoding="utf-8")

    pr_diff_cp = run_cmd(["gh", "pr", "diff", pr_ref])
    if pr_diff_cp.returncode != 0:
        print(pr_diff_cp.stderr.strip() or pr_diff_cp.stdout.strip())
        return 2
    pr_diff_path.write_text(pr_diff_cp.stdout, encoding="utf-8")

    try:
        metadata = json.loads(pr_view_cp.stdout)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse gh pr view JSON: {exc}")
        return 2

    pr_url = str(metadata.get("url", "")).strip()
    if not pr_url:
        print("Missing .url in gh pr view response")
        return 2

    try:
        repo_url, host, owner, repo = parse_pr_repo_url(pr_url)
    except ValueError as exc:
        print(str(exc))
        return 2

    current_repo = current_repo_name_with_owner()
    path_select_script = locate_path_select_script()
    path_select_cp = run_cmd(
        ["python3", str(path_select_script), repo_url, current_repo],
    )
    combined_path_output = (path_select_cp.stdout or "") + (path_select_cp.stderr or "")
    path_select_log_path.write_text(combined_path_output, encoding="utf-8")

    # Emit path selection trace lines directly (required by skill instructions).
    if combined_path_output:
        print(combined_path_output.rstrip())

    if path_select_cp.returncode != 0:
        return 2

    kv = parse_key_value_output(path_select_cp.stdout)
    selected_path = kv.get("SELECTED_PATH", "")
    repo_path = kv.get("REPO_PATH", "")
    if selected_path not in {"A", "B", "C"}:
        print("Invalid SELECTED_PATH from path_select.py")
        return 2

    pr_number = int(metadata.get("number", 0) or 0)
    base_ref_name = str(metadata.get("baseRefName", "")).strip()
    head_ref_name = str(metadata.get("headRefName", "")).strip()
    pr_state = str(metadata.get("state", "")).strip()

    repo_workdir = ""
    original_branch = ""
    checkout_ref = ""
    context_mode = "full_repo"
    context_limitation = ""
    review_dir = ""

    if selected_path == "A":
        top_level = current_repo_top_level()
        if top_level:
            repo_workdir = top_level
            original_branch = current_branch(Path(repo_workdir))
            checkout_ref, context_limitation = ensure_checkout(
                Path(repo_workdir),
                base_ref_name,
                head_ref_name,
                pr_number,
            )
        else:
            context_limitation = "Path A selected but current repo top-level not found"

    elif selected_path == "B":
        if repo_path:
            repo_workdir = repo_path
            checkout_ref, context_limitation = ensure_checkout(
                Path(repo_workdir),
                base_ref_name,
                head_ref_name,
                pr_number,
            )
        else:
            context_limitation = "Path B selected but REPO_PATH missing"

    else:  # Path C
        review_dir_path = Path(tempfile.mkdtemp(prefix="repo-", dir=str(cache_dir)))
        review_dir = str(review_dir_path)
        clone_cp = run_cmd(
            [
                "gh",
                "repo",
                "clone",
                repo_url,
                str(review_dir_path),
                "--",
                "--filter=blob:none",
                "--sparse",
            ]
        )
        if clone_cp.returncode != 0:
            context_limitation = (
                clone_cp.stderr.strip()
                or clone_cp.stdout.strip()
                or "Path C blobless clone failed"
            )
        else:
            repo_workdir = str(review_dir_path)
            checkout_ref, context_limitation = ensure_checkout(
                review_dir_path,
                base_ref_name,
                head_ref_name,
                pr_number,
            )

    if not checkout_ref:
        context_mode = "diff_only"

    command_log_path.write_text("\n".join(COMMAND_LOG) + "\n", encoding="utf-8")

    manifest = SessionManifest(
        run_dir=str(run_dir),
        pr_ref=pr_ref,
        pr_url=pr_url,
        repo_url=repo_url,
        host=host,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        pr_state=pr_state,
        selected_path=selected_path,
        repo_path=repo_path,
        repo_workdir=repo_workdir,
        original_branch=original_branch,
        checkout_ref=checkout_ref,
        context_mode=context_mode,
        context_limitation=context_limitation,
        pr_view_json_path=str(pr_view_path),
        pr_diff_path=str(pr_diff_path),
        command_log_path=str(command_log_path),
        path_select_log_path=str(path_select_log_path),
        review_dir=review_dir,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    manifest_path.write_text(
        json.dumps(asdict(manifest), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    print(f"RUN_MANIFEST={manifest_path}")
    print(f"PR_VIEW_JSON_PATH={manifest.pr_view_json_path}")
    print(f"PR_DIFF_PATH={manifest.pr_diff_path}")
    print(f"COMMAND_LOG_PATH={manifest.command_log_path}")
    print(f"SELECTED_PATH={manifest.selected_path}")
    print(f"REPO_PATH={manifest.repo_path}")
    print(f"REPO_WORKDIR={manifest.repo_workdir}")
    print(f"PR_STATE={manifest.pr_state}")
    print(f"CONTEXT_MODE={manifest.context_mode}")
    print(f"CONTEXT_LIMITATION={manifest.context_limitation}")
    return 0


def resolve_default_branch(repo_path: Path) -> str:
    """Resolve remote default branch name for a local repo."""
    cp = run_cmd(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
        cwd=repo_path,
    )
    if cp.returncode != 0:
        return "main"
    value = cp.stdout.strip()
    return value.replace("origin/", "", 1) if value.startswith("origin/") else value


def cleanup_session(manifest_path: Path) -> int:
    """Execute deterministic cleanup from session manifest."""
    if not manifest_path.exists():
        print(f"[PATH-CLEANUP] skipped - manifest not found: {manifest_path}")
        return 0

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[PATH-CLEANUP] skipped - invalid manifest JSON: {manifest_path}")
        return 0

    selected_path = str(data.get("selected_path", ""))
    repo_workdir = str(data.get("repo_workdir", ""))
    original_branch = str(data.get("original_branch", ""))
    run_dir = Path(str(data.get("run_dir", "")))
    review_dir = Path(str(data.get("review_dir", "")))

    if selected_path == "A":
        if repo_workdir and original_branch:
            cp = run_cmd(["git", "checkout", original_branch], cwd=Path(repo_workdir))
            if cp.returncode == 0:
                print(f"[PATH-CLEANUP] Path A - restored branch to {original_branch}")
            else:
                print(
                    "[PATH-CLEANUP] Path A - failed to restore branch: "
                    f"{cp.stderr.strip() or cp.stdout.strip()}"
                )
        else:
            print(
                "[PATH-CLEANUP] Path A - skipped (missing repo_workdir/original_branch)"
            )

    elif selected_path == "B":
        if repo_workdir and (Path(repo_workdir) / ".git").is_dir():
            repo_dir = Path(repo_workdir)
            default_branch = resolve_default_branch(repo_dir)
            run_cmd(["git", "checkout", default_branch], cwd=repo_dir)
            run_cmd(
                ["git", "reset", "--hard", f"origin/{default_branch}"], cwd=repo_dir
            )
            run_cmd(["git", "clean", "-fd"], cwd=repo_dir)
            print(
                "[PATH-CLEANUP] Path B - reset cached repo to "
                f"{default_branch}, ready for next use"
            )
        else:
            print("[PATH-CLEANUP] Path B - skipped (repo_workdir unavailable)")

    elif selected_path == "C":
        removed: list[str] = []
        for path in [review_dir]:
            if str(path) and path.exists():
                shutil.rmtree(path, ignore_errors=False)
                removed.append(str(path))
        if removed:
            print(f"[PATH-CLEANUP] Path C - deleted temp dirs: {' '.join(removed)}")
        else:
            print("[PATH-CLEANUP] Path C - no temp dirs to delete")

    else:
        print("[PATH-CLEANUP] skipped - unknown SELECTED_PATH")

    if run_dir.exists() and run_dir.is_dir():
        shutil.rmtree(run_dir, ignore_errors=True)
        print(f"[PATH-CLEANUP] Session artifacts removed: {run_dir}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for prepare/cleanup subcommands."""
    parser = argparse.ArgumentParser(description="Guarded PR review runner")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare_parser = sub.add_parser("prepare", help="Prepare review session")
    prepare_parser.add_argument("pr_ref", help="PR URL or PR number")

    cleanup_parser = sub.add_parser("cleanup", help="Cleanup review session")
    cleanup_parser.add_argument("manifest_path", help="Path to session manifest.json")
    return parser


def main() -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "prepare":
        raise SystemExit(prepare_session(args.pr_ref))
    raise SystemExit(cleanup_session(Path(args.manifest_path)))


if __name__ == "__main__":
    main()
