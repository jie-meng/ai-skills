#!/usr/bin/env python3
"""Build a deterministic review template from session manifest.

This script generates a fixed 6-section review skeleton with required fields so
the final review is less likely to drift or contradict itself.

Usage:
    python3 scripts/review_template_builder.py \
      --manifest /path/to/manifest.json \
      --output /path/to/review_draft.md \
      --language en

Notes:
- This script does not evaluate code quality by itself.
- It only creates a structured draft with placeholders to fill.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_manifest(path: Path) -> dict:
    """Load manifest JSON and return dict."""
    return json.loads(path.read_text(encoding="utf-8"))


def render_english(manifest: dict) -> str:
    """Render English review draft with required structure."""
    pr_number = manifest.get("pr_number", "")
    pr_url = manifest.get("pr_url", "")
    pr_state = str(manifest.get("pr_state", "")).upper()
    context_mode = manifest.get("context_mode", "full_repo")
    context_limitation = manifest.get("context_limitation", "")

    default_verdict = "Comment" if pr_state in {"MERGED", "CLOSED"} else "Approve"

    limitation_block = ""
    if context_mode == "diff_only":
        limitation_block = (
            "- Context limitation: diff-only review mode was used.\n"
            f"- Reason: {context_limitation or '[fill reason]'}\n"
        )

    return f"""PR Review Draft

PR: #{pr_number}
URL: {pr_url}
State: {pr_state or "[fill state]"}

1. PR Overview
- Purpose and motivation: [fill]
- Change scope: [fill files/lines]
- Primary modules affected: [fill]
{limitation_block}
2. Repository Context Analysis
- Tech stack and toolchain: [fill]
- Coding conventions and architecture patterns: [fill]
- Alignment with project conventions: [fill]

3. Code Quality & Clean Code Evaluation
- Strengths: [fill]
- Confirmed findings with file/line evidence: [fill]
- Potential risks with validation steps: [fill]

4. Major Issues and Risks
Confirmed Findings:
- none

Potential Risks:
- none

5. Incremental Suggestions
- [fill suggestion 1]
- [fill suggestion 2]

6. Summary Verdict
- Verdict: {default_verdict}
- Rationale: [fill concise rationale consistent with findings]

Pre-send consistency checks:
- No platform speculation text before gh execution.
- No contradictory statements (remove disproven suspicions).
- Exactly one verdict keyword used in final output.
"""


def render_chinese(manifest: dict) -> str:
    """Render Chinese review draft with required structure."""
    pr_number = manifest.get("pr_number", "")
    pr_url = manifest.get("pr_url", "")
    pr_state = str(manifest.get("pr_state", "")).upper()
    context_mode = manifest.get("context_mode", "full_repo")
    context_limitation = manifest.get("context_limitation", "")

    default_verdict = "Comment" if pr_state in {"MERGED", "CLOSED"} else "Approve"

    limitation_block = ""
    if context_mode == "diff_only":
        limitation_block = (
            "- 上下文限制：本次仅基于 diff 进行评审。\n"
            f"- 原因：{context_limitation or '[请补充]'}\n"
        )

    return f"""PR 评审草稿

PR: #{pr_number}
URL: {pr_url}
状态: {pr_state or "[请补充]"}

1. PR 概览
- 目的与动机：[请补充]
- 变更规模：[请补充文件数/行数]
- 主要影响模块：[请补充]
{limitation_block}
2. 仓库上下文分析
- 技术栈与工具链：[请补充]
- 编码规范与架构模式：[请补充]
- 与现有约定一致性：[请补充]

3. 代码质量 & Clean Code 评价
- 优点：[请补充]
- 已确认问题（含文件/行证据）：[请补充]
- 潜在风险（含验证步骤）：[请补充]

4. 潜在的重大问题和风险
Confirmed Findings:
- none

Potential Risks:
- none

5. 增量建议
- [建议 1]
- [建议 2]

6. 总结评价
- Verdict: {default_verdict}
- 结论依据：[请补充，且与上文问题等级保持一致]

发送前一致性检查：
- 不出现平台猜测表述。
- 不保留自我矛盾描述（已排除的问题要删除）。
- 最终仅保留一个 verdict 关键词。
"""


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Build PR review template draft")
    parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    parser.add_argument("--output", required=True, help="Path to write draft file")
    parser.add_argument(
        "--language",
        default="en",
        choices=["en", "zh"],
        help="Draft language",
    )
    return parser


def main() -> None:
    """Entry point."""
    args = build_parser().parse_args()
    manifest = load_manifest(Path(args.manifest))
    if args.language == "zh":
        content = render_chinese(manifest)
    else:
        content = render_english(manifest)
    Path(args.output).write_text(content, encoding="utf-8")
    print(f"REVIEW_DRAFT_PATH={args.output}")


if __name__ == "__main__":
    main()
