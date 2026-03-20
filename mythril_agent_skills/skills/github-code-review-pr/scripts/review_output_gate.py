#!/usr/bin/env python3
"""Run pre-flight quality gates for PR review output.

This script enforces operational and output constraints introduced by SKILL.md:

1. NO_SPECULATION_PASS
2. SINGLE_FETCH_PASS
3. CLEANUP_EVIDENCE_PASS
4. VERDICT_STATE_PASS

Usage:
    python3 scripts/review_output_gate.py \
      --manifest /path/to/manifest.json \
      --review-text /path/to/review.md \
      --cleanup-log /path/to/cleanup.log

Exit codes:
    0 -> all checks passed
    1 -> at least one check failed
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


FORBIDDEN_PLATFORM_PHRASES = [
    "not a github url",
    "looks like gitlab",
    "looks like bitbucket",
    "possibly gitlab",
    "maybe gitlab",
    "non-github platform",
    "self-hosted gitlab",
    "similar git platform",
]


@dataclass
class GateResult:
    """Single gate result."""

    name: str
    passed: bool
    detail: str


def read_text(path: Path) -> str:
    """Read UTF-8 text file."""
    return path.read_text(encoding="utf-8")


def load_manifest(path: Path) -> dict:
    """Load manifest JSON as dict."""
    return json.loads(read_text(path))


def load_command_log(path: Path) -> list[dict]:
    """Load JSONL command log entries."""
    entries: list[dict] = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


def gate_no_speculation(text: str) -> GateResult:
    """Check forbidden platform speculation phrases."""
    lowered = text.lower()
    hits = [p for p in FORBIDDEN_PLATFORM_PHRASES if p in lowered]
    if hits:
        return GateResult(
            name="NO_SPECULATION_PASS",
            passed=False,
            detail=f"forbidden phrase(s) found: {', '.join(hits)}",
        )
    return GateResult(
        name="NO_SPECULATION_PASS",
        passed=True,
        detail="no forbidden platform speculation phrases detected",
    )


def is_gh_pr_view(cmd: list[str]) -> bool:
    """Return whether command is gh pr view."""
    return len(cmd) >= 3 and cmd[0] == "gh" and cmd[1] == "pr" and cmd[2] == "view"


def is_gh_pr_diff(cmd: list[str]) -> bool:
    """Return whether command is gh pr diff."""
    return len(cmd) >= 3 and cmd[0] == "gh" and cmd[1] == "pr" and cmd[2] == "diff"


def gate_single_fetch(command_entries: list[dict]) -> GateResult:
    """Ensure gh pr view/diff are executed exactly once."""
    view_count = 0
    diff_count = 0
    for entry in command_entries:
        cmd = entry.get("cmd")
        if not isinstance(cmd, list):
            continue
        cmd_tokens = [str(t) for t in cmd]
        if is_gh_pr_view(cmd_tokens):
            view_count += 1
        if is_gh_pr_diff(cmd_tokens):
            diff_count += 1

    if view_count == 1 and diff_count == 1:
        return GateResult(
            name="SINGLE_FETCH_PASS",
            passed=True,
            detail="gh pr view/diff each executed exactly once",
        )

    return GateResult(
        name="SINGLE_FETCH_PASS",
        passed=False,
        detail=f"gh pr view count={view_count}, gh pr diff count={diff_count}",
    )


def gate_cleanup_evidence(cleanup_log_text: str) -> GateResult:
    """Require [PATH-CLEANUP] marker in cleanup logs."""
    if "[PATH-CLEANUP]" in cleanup_log_text:
        return GateResult(
            name="CLEANUP_EVIDENCE_PASS",
            passed=True,
            detail="cleanup marker found",
        )
    return GateResult(
        name="CLEANUP_EVIDENCE_PASS",
        passed=False,
        detail="missing [PATH-CLEANUP] marker in cleanup logs",
    )


def detect_verdict(review_text: str) -> str:
    """Best-effort verdict detection from review text."""
    lines = [line.strip().lower() for line in review_text.splitlines() if line.strip()]
    focus_lines: list[str] = []
    for i, line in enumerate(lines):
        if "verdict" in line or "assessment" in line or "overall" in line:
            focus_lines.append(line)
            if i + 1 < len(lines):
                focus_lines.append(lines[i + 1])

    pool = "\n".join(focus_lines) if focus_lines else review_text.lower()
    has_request_changes = bool(re.search(r"\brequest\s+changes\b", pool))
    has_approve = bool(re.search(r"\bapprove\b", pool))
    has_comment = bool(re.search(r"\bcomment\b", pool))

    matches = [
        ("REQUEST_CHANGES", has_request_changes),
        ("APPROVE", has_approve),
        ("COMMENT", has_comment),
    ]
    found = [name for name, ok in matches if ok]
    if len(found) == 1:
        return found[0]
    if len(found) == 0:
        return "UNKNOWN"
    return "AMBIGUOUS"


def gate_verdict_state(
    pr_state: str,
    detected_verdict: str,
    allow_retrospective_request_changes: bool,
) -> GateResult:
    """Validate verdict against PR state rule."""
    normalized_state = pr_state.strip().upper()
    if normalized_state in {"MERGED", "CLOSED"}:
        if (
            detected_verdict == "REQUEST_CHANGES"
            and not allow_retrospective_request_changes
        ):
            return GateResult(
                name="VERDICT_STATE_PASS",
                passed=False,
                detail=(
                    "PR state is merged/closed but verdict is Request Changes; "
                    "default should be Comment unless explicitly overridden"
                ),
            )

    if detected_verdict in {"UNKNOWN", "AMBIGUOUS"}:
        return GateResult(
            name="VERDICT_STATE_PASS",
            passed=False,
            detail=f"unable to determine single verdict ({detected_verdict})",
        )

    return GateResult(
        name="VERDICT_STATE_PASS",
        passed=True,
        detail=f"state={normalized_state or 'UNKNOWN'}, verdict={detected_verdict}",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="PR review output quality gate")
    parser.add_argument(
        "--manifest", required=True, help="Path to review manifest.json"
    )
    parser.add_argument("--review-text", required=True, help="Path to review text file")
    parser.add_argument(
        "--cleanup-log",
        required=True,
        help="Path to cleanup command/log text containing [PATH-CLEANUP]",
    )
    parser.add_argument(
        "--transcript-text",
        default="",
        help="Optional full transcript text for speculation check",
    )
    parser.add_argument(
        "--allow-retrospective-request-changes",
        action="store_true",
        help="Allow Request Changes verdict on merged/closed PR",
    )
    return parser


def main() -> None:
    """Entry point."""
    args = build_parser().parse_args()
    manifest_path = Path(args.manifest)
    review_text_path = Path(args.review_text)
    cleanup_log_path = Path(args.cleanup_log)

    manifest = load_manifest(manifest_path)
    command_log_path = Path(str(manifest.get("command_log_path", "")))
    if not command_log_path.exists():
        print("SINGLE_FETCH_PASS: FAIL - command log path missing or does not exist")
        raise SystemExit(1)

    review_text = read_text(review_text_path)
    cleanup_text = read_text(cleanup_log_path)
    speculation_text = review_text
    if args.transcript_text:
        transcript_path = Path(args.transcript_text)
        if transcript_path.exists():
            speculation_text += "\n" + read_text(transcript_path)

    command_entries = load_command_log(command_log_path)
    detected_verdict = detect_verdict(review_text)
    pr_state = str(manifest.get("pr_state", ""))

    results = [
        gate_no_speculation(speculation_text),
        gate_single_fetch(command_entries),
        gate_cleanup_evidence(cleanup_text),
        gate_verdict_state(
            pr_state,
            detected_verdict,
            args.allow_retrospective_request_changes,
        ),
    ]

    all_passed = True
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{result.name}: {status} - {result.detail}")
        all_passed = all_passed and result.passed

    raise SystemExit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
