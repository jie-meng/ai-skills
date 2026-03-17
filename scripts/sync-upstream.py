#!/usr/bin/env python3
"""Sync upstream mythril-agent-skills changes into a forked repository.

Fetches the latest upstream code and selectively copies updated skills,
CLI scripts, and project files — skipping any skills listed in the
exclude_skills section of .sync-upstream.json.

Usage:
    python3 scripts/sync-upstream.py              # Interactive (confirm before applying)
    python3 scripts/sync-upstream.py --dry-run     # Preview only, no changes
    python3 scripts/sync-upstream.py --force        # Apply without confirmation
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / ".sync-upstream.json"
DEFAULT_UPSTREAM = "https://github.com/jie-meng/mythril-agent-skills.git"
DEFAULT_BRANCH = "main"
REMOTE_NAME = "_mythril_upstream"

UPSTREAM_IDENTIFIERS = [
    "jie-meng/mythril-agent-skills",
    "jie-meng/mythril-agent-skills.git",
]

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

SYNC_PATHS = [
    "mythril_agent_skills/cli/",
    "mythril_agent_skills/__init__.py",
    "scripts/sync-upstream.py",
    "docs/",
    "AGENTS.md",
]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def parse_config(path: Path) -> dict[str, str | list[str]]:
    """Parse .sync-upstream.json, returning an empty dict if missing."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def run_git(*args: str, capture: bool = True, check: bool = True) -> str:
    """Run a git command and return stdout."""
    cmd = ["git", "-C", str(REPO_ROOT), *args]
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )
    return result.stdout.strip() if capture else ""


def ensure_remote(url: str) -> None:
    """Add or update the upstream remote."""
    try:
        existing = run_git("remote", "get-url", REMOTE_NAME)
        if existing != url:
            run_git("remote", "set-url", REMOTE_NAME, url)
            print(f"  Updated remote {REMOTE_NAME} → {url}")
    except subprocess.CalledProcessError:
        run_git("remote", "add", REMOTE_NAME, url)
        print(f"  Added remote {REMOTE_NAME} → {url}")


def fetch_upstream(branch: str) -> None:
    """Fetch the upstream branch."""
    print(f"  Fetching {REMOTE_NAME}/{branch} ...")
    run_git("fetch", REMOTE_NAME, branch, capture=False)


def remove_remote() -> None:
    """Remove the temporary upstream remote."""
    try:
        run_git("remote", "remove", REMOTE_NAME)
    except subprocess.CalledProcessError:
        pass


def has_uncommitted_changes() -> bool:
    """Check if working tree has uncommitted changes."""
    status = run_git("status", "--porcelain")
    return bool(status)


def is_upstream_repo() -> bool:
    """Detect if the current repo IS the upstream (not a fork)."""
    try:
        remotes = run_git("remote", "-v")
    except subprocess.CalledProcessError:
        return False

    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, url = parts[0], parts[1]
        if name != "origin":
            continue
        for ident in UPSTREAM_IDENTIFIERS:
            if ident in url:
                return True
    return False


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------


def extract_upstream(branch: str, dest: Path) -> None:
    """Export upstream branch content to a temp directory via git archive."""
    run_git(
        "archive",
        f"{REMOTE_NAME}/{branch}",
        "--format=tar",
        f"--output={dest / 'upstream.tar'}",
    )
    subprocess.run(
        ["tar", "xf", str(dest / "upstream.tar"), "-C", str(dest)],
        check=True,
        capture_output=True,
    )
    (dest / "upstream.tar").unlink()


def collect_changes(
    upstream_dir: Path,
    exclude_skills: list[str],
) -> tuple[list[tuple[Path, Path]], list[Path], list[str]]:
    """Compare upstream with local and return (to_copy, to_delete, skipped).

    Returns:
        to_copy: list of (src, dst) pairs to copy
        to_delete: list of local paths to delete (upstream removed them)
        skipped: list of excluded skill names that had upstream changes
    """
    to_copy: list[tuple[Path, Path]] = []
    to_delete: list[Path] = []
    skipped: list[str] = []

    skills_src = upstream_dir / "mythril_agent_skills" / "skills"
    skills_dst = REPO_ROOT / "mythril_agent_skills" / "skills"

    if skills_src.is_dir():
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            if skill_dir.name in exclude_skills:
                local_skill = skills_dst / skill_dir.name
                if local_skill.is_dir() and _trees_differ(skill_dir, local_skill):
                    skipped.append(skill_dir.name)
                continue
            local_skill = skills_dst / skill_dir.name
            if not local_skill.is_dir() or _trees_differ(skill_dir, local_skill):
                to_copy.append((skill_dir, local_skill))

    for rel_path in SYNC_PATHS:
        src = upstream_dir / rel_path
        dst = REPO_ROOT / rel_path

        if not src.exists():
            continue

        if src.is_file():
            if not dst.exists() or src.read_bytes() != dst.read_bytes():
                to_copy.append((src, dst))
        elif src.is_dir():
            for src_file in sorted(src.rglob("*")):
                if src_file.is_dir():
                    continue
                dst_file = dst / src_file.relative_to(src)
                if not dst_file.exists() or src_file.read_bytes() != dst_file.read_bytes():
                    to_copy.append((src_file, dst_file))

    return to_copy, to_delete, skipped


def _trees_differ(src: Path, dst: Path) -> bool:
    """Return True if two directory trees have different contents."""
    src_files = {f.relative_to(src): f for f in src.rglob("*") if f.is_file()}
    dst_files = {f.relative_to(dst): f for f in dst.rglob("*") if f.is_file()}

    if set(src_files.keys()) != set(dst_files.keys()):
        return True

    for rel, src_f in src_files.items():
        if src_f.read_bytes() != dst_files[rel].read_bytes():
            return True
    return False


def apply_changes(to_copy: list[tuple[Path, Path]], to_delete: list[Path]) -> None:
    """Apply file changes: copy updated files, delete removed files."""
    for src, dst in to_copy:
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for path in to_delete:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def classify_changes(
    to_copy: list[tuple[Path, Path]],
) -> tuple[list[str], list[str], list[str]]:
    """Classify changes into (skills_added, skills_updated, files_updated)."""
    skills_added: list[str] = []
    skills_updated: list[str] = []
    files_updated: list[str] = []

    for _, dst in to_copy:
        rel = dst.relative_to(REPO_ROOT)
        rel_str = str(rel)

        if rel_str.startswith("mythril_agent_skills/skills/"):
            parts = rel.parts
            if len(parts) >= 3:
                skill_name = parts[2]
                if (REPO_ROOT / "mythril_agent_skills" / "skills" / skill_name).is_dir():
                    if skill_name not in skills_updated:
                        skills_updated.append(skill_name)
                else:
                    if skill_name not in skills_added:
                        skills_added.append(skill_name)
        else:
            files_updated.append(rel_str)

    return (
        sorted(set(skills_added)),
        sorted(set(skills_updated)),
        sorted(set(files_updated)),
    )


def print_summary(
    to_copy: list[tuple[Path, Path]],
    to_delete: list[Path],
    skipped: list[str],
) -> None:
    """Print a human-readable preview of pending changes."""
    if not to_copy and not to_delete and not skipped:
        print(f"\n{GREEN}Already up to date. No changes needed.{NC}")
        return

    skills_added, skills_updated, files_updated = classify_changes(to_copy)

    print(f"\n{BOLD}=== Upstream Sync Preview ==={NC}\n")

    if skills_added:
        print(f"  {GREEN}New skills:{NC}")
        for s in skills_added:
            print(f"    + {s}")
    if skills_updated:
        print(f"  {YELLOW}Updated skills:{NC}")
        for s in skills_updated:
            print(f"    ~ {s}")
    if files_updated:
        print(f"  {YELLOW}Updated files:{NC}")
        for f in files_updated:
            print(f"    ~ {f}")

    if to_delete:
        print(f"  {RED}Removed:{NC}")
        for p in to_delete:
            print(f"    - {p.relative_to(REPO_ROOT)}")

    if skipped:
        print(f"\n  {DIM}Excluded (in exclude_skills):{NC}")
        for s in skipped:
            print(f"    {DIM}⊘ {s} (upstream has changes, skipped){NC}")

    total = len(to_copy) + len(to_delete)
    print(f"\n  {BOLD}Total: {total} file(s) to sync{NC}")


def print_report(
    to_copy: list[tuple[Path, Path]],
    to_delete: list[Path],
    skipped: list[str],
) -> None:
    """Print a post-sync report showing exactly what was changed."""
    skills_added, skills_updated, files_updated = classify_changes(to_copy)
    removed = [str(p.relative_to(REPO_ROOT)) for p in to_delete]

    print(f"\n{BOLD}{'=' * 50}{NC}")
    print(f"{BOLD}  Upstream Sync Report{NC}")
    print(f"{BOLD}{'=' * 50}{NC}\n")

    if skills_added:
        print(f"  {GREEN}{BOLD}New skills ({len(skills_added)}):{NC}")
        for s in skills_added:
            print(f"    {GREEN}+{NC} {s}")
        print()

    if skills_updated:
        print(f"  {YELLOW}{BOLD}Updated skills ({len(skills_updated)}):{NC}")
        for s in skills_updated:
            print(f"    {YELLOW}~{NC} {s}")
        print()

    if files_updated:
        print(f"  {YELLOW}{BOLD}Updated files ({len(files_updated)}):{NC}")
        for f in files_updated:
            print(f"    {YELLOW}~{NC} {f}")
        print()

    if removed:
        print(f"  {RED}{BOLD}Removed ({len(removed)}):{NC}")
        for r in removed:
            print(f"    {RED}-{NC} {r}")
        print()

    if skipped:
        print(f"  {DIM}Excluded skills ({len(skipped)}) — upstream has changes, skipped:{NC}")
        for s in skipped:
            print(f"    {DIM}⊘ {s}{NC}")
        print()

    total_changes = len(to_copy) + len(to_delete)
    print(f"  {BOLD}Total: {total_changes} file(s) synced{NC}")
    print(f"{BOLD}{'=' * 50}{NC}")

    print(
        f"\n  Changes are in your working tree (not committed).\n"
        f"  Review with: {DIM}git diff{NC}\n"
        f"  Then commit: {DIM}git add -A && git commit -m \"Sync upstream changes\"{NC}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    print(f"{BOLD}mythril-agent-skills upstream sync{NC}\n")

    if is_upstream_repo():
        print(
            f"{RED}Error: This appears to be the upstream repository "
            f"(origin points to jie-meng/mythril-agent-skills).{NC}\n\n"
            f"  This sync script is designed for forks only.\n"
            f"  There is nothing to sync — you already have the upstream code.\n"
        )
        sys.exit(1)

    config = parse_config(CONFIG_FILE)
    upstream_url = str(config.get("upstream_repo", DEFAULT_UPSTREAM))
    upstream_branch = str(config.get("upstream_branch", DEFAULT_BRANCH))
    exclude_skills_raw = config.get("exclude_skills", [])
    exclude_skills = (
        exclude_skills_raw if isinstance(exclude_skills_raw, list) else []
    )

    if exclude_skills:
        print(f"  Excluded skills: {', '.join(exclude_skills)}")

    if not dry_run and has_uncommitted_changes():
        print(
            f"\n{YELLOW}Warning: You have uncommitted changes.{NC}\n"
            f"Consider committing or stashing them before syncing.\n"
        )
        if not force:
            try:
                answer = input("Continue anyway? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(1)
            if answer != "y":
                print("Aborted.")
                sys.exit(0)

    ensure_remote(upstream_url)
    try:
        fetch_upstream(upstream_branch)

        with tempfile.TemporaryDirectory(prefix="mythril-sync-") as tmp:
            tmp_path = Path(tmp)
            print("  Extracting upstream content ...")
            extract_upstream(upstream_branch, tmp_path)

            to_copy, to_delete, skipped = collect_changes(tmp_path, exclude_skills)
            print_summary(to_copy, to_delete, skipped)

            if not to_copy and not to_delete:
                return

            if dry_run:
                print(f"\n{DIM}Dry run — no changes applied.{NC}")
                return

            if not force:
                try:
                    answer = input(
                        f"\n{YELLOW}Apply these changes?{NC} [y/N] "
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted.")
                    sys.exit(1)
                if answer != "y":
                    print("Aborted.")
                    return

            apply_changes(to_copy, to_delete)
            print(f"\n{GREEN}✓ Sync complete!{NC}")
            print_report(to_copy, to_delete, skipped)
    finally:
        remove_remote()


if __name__ == "__main__":
    main()
