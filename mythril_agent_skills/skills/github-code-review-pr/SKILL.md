---
name: github-code-review-pr
description: >
  Comprehensive structured code review for GitHub Pull Requests with deep repository context awareness.
  GitHub ONLY (including GitHub Enterprise) — does NOT support GitLab, Gitee, Bitbucket, or other platforms.
  Trigger when user requests: 'review PR', 'review this PR', 'PR review', 'PR CR', '审查PR', '看这个PR',
  'review pull request', 'help me review', or provides a PR URL and asks for review.
  When triggered, reject known non-GitHub platforms (GitLab, Gitee, Bitbucket) immediately; for unknown
  domains, proceed optimistically since GitHub Enterprise domains can be anything — let `gh` CLI determine
  whether the host is a valid GitHub instance. Fetches PR metadata, diff, full file contents of modified
  files, project structure, and coding conventions to deliver high-quality, context-aware reviews.
  Requires GitHub CLI (`gh`).
license: Apache-2.0
---

# When to Use This Skill

**ALWAYS invoke this skill when user wants to review a GitHub Pull Request:**
- "review this PR" / "review PR" / "PR review" / "PR code review"
- "审查这个PR" / "帮我看这个PR" / "PR审查" / "review pull request"
- "review https://github.com/owner/repo/pull/123"
- User provides a PR URL or PR number and asks for review/feedback
- "help me review this pull request"
- "use github-code-review-pr skill"

**This skill reviews remote GitHub PRs (not local staged changes).**
For local staged changes, use `code-review-staged` instead.

**GitHub ONLY.** This skill does NOT support GitLab, Gitee, Bitbucket, or other git hosting platforms. If the user provides a non-GitHub URL, inform them immediately and stop.

# Requirements

- **GitHub CLI (`gh`)** must be installed and authenticated
- Run `skills-check github-code-review-pr` to verify dependencies

# Requirements for Outputs

## Code Review Quality

### Review Standards
- Code review MUST be comprehensive, identifying all potential issues
- Review MUST be thorough and rigorous, highlighting suspicious code
- Review MUST provide actionable, concrete suggestions with file paths and line references
- Review MUST consider the project's existing conventions, patterns, and style
- Review language MUST match the user's input language (Chinese or English)

### Language Detection
- Detect user's input language automatically
- If user input contains Chinese characters (Unicode U+4E00-U+9FFF), output review in Chinese
- If user input contains only English, output review in English

# Implementation

The skill executes these steps:

## Step 1: Parse PR Reference and Validate Platform

Accept PR input in any of these formats:
- Full URL: `https://github.com/owner/repo/pull/123`
- GitHub Enterprise URL: `https://git.mycompany.com/owner/repo/pull/123` (domain can be anything — GHE domains vary widely)
- PR number (when inside a repo): `123`
- PR number with repo: `owner/repo#123`

**Platform validation (do this FIRST if a URL is provided):**

1. **Quick reject known non-GitHub platforms:** If the URL host matches any of these, **stop immediately** and inform the user:
   - `gitlab.com` or any `gitlab.*` domain
   - `gitee.com`
   - `bitbucket.org`

2. **For all other URLs (including unknown domains):** Do NOT reject based on the domain name alone. GitHub Enterprise (GHE) domains can be anything — `git.mycompany.com`, `github.corp.example.com`, `code.company.io`, etc. There is no reliable way to tell from the URL alone whether a host is GitHub.

   Instead, **proceed optimistically** — attempt the `gh` commands in Step 2. The `gh` CLI only works with GitHub (github.com and authenticated GHE instances). If `gh pr view` fails with an authentication or host error, report that the host may not be a GitHub instance (or the user needs to run `gh auth login --hostname <host>` for GHE) and stop.

Extract: **owner**, **repo**, **PR number**, and optionally **hostname** (for GHE).

## Step 2: Fetch PR Metadata and Diff

Fetch PR metadata and diff via `gh`. Run these commands concurrently:

### 2a. PR metadata
```bash
gh pr view <URL_or_NUMBER> --json number,title,body,state,author,baseRefName,headRefName,labels,reviewDecision,additions,deletions,changedFiles,commits,files,comments,reviews,url
```

Key fields:
- `title`, `body` — PR description and intent
- `baseRefName`, `headRefName` — branches involved
- `files` — list of changed files with `path`, `additions`, `deletions`
- `commits` — commit history in the PR
- `comments`, `reviews` — existing discussion context
- `url` — used to extract `owner/repo`

### 2b. PR diff
```bash
gh pr diff <URL_or_NUMBER>
```

## Step 3: Get Local Access to the Repository

The goal is to have the codebase available locally so all context gathering is just file reads — no per-file API requests. Choose one of two paths depending on whether we're already in the target repo.

### Path A: Already inside the target repo

Check: `gh repo view --json nameWithOwner -q .nameWithOwner` — if it matches the PR's repo, we're already here.

```bash
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
gh pr checkout <PR_NUMBER>
```

After review, restore the original branch:
```bash
git checkout "$ORIGINAL_BRANCH"
```

### Path B: Not inside the target repo — partial clone

Use **partial clone + sparse checkout** to avoid downloading the entire repo. This downloads only git metadata (commits and tree objects) on clone — **file contents are NOT downloaded until explicitly checked out**. Even for a multi-GB monorepo, the initial clone is typically just a few MB.

```bash
TMPDIR=$(mktemp -d)
gh repo clone <owner/repo> "$TMPDIR" -- --filter=blob:none --depth=1 --single-branch --sparse
cd "$TMPDIR"
```

Now the repo is cloned but the working directory is nearly empty (only root-level files). Next, selectively populate **only the files we need** using sparse-checkout:

```bash
git sparse-checkout init --cone
```

Then determine which files/directories to check out based on the PR metadata from Step 2:

**1. Config & convention files at the repo root** — always check out:
```bash
git sparse-checkout set /
```
This checks out root-level files only (README.md, AGENTS.md, CLAUDE.md, pyproject.toml, package.json, etc.) without pulling any subdirectories.

**2. Directories containing PR-modified files** — extract from the `files` list in Step 2a:
```bash
git sparse-checkout add src/components src/utils tests/unit
```
Only add the directories that contain files changed in the PR. This pulls just those directory trees.

**3. Directories for related files** — if the diff references imports or base classes from other paths, add those too:
```bash
git sparse-checkout add src/types src/shared
```

Now checkout the PR branch to get the PR's version of those files:
```bash
gh pr checkout <PR_NUMBER>
```

After review, clean up:
```bash
rm -rf "$TMPDIR"
```

**Size comparison for a large repo (e.g., 50K files, 2GB full clone):**

| Method | Download size | Network requests |
|---|---|---|
| Full clone | ~2 GB | 1 |
| `--depth=1` shallow clone | ~500 MB (all blobs) | 1 |
| `--filter=blob:none --sparse` + selective checkout | ~5-50 MB (metadata + needed files only) | 1 clone + on-demand blob fetches |
| Per-file `gh api` calls | ~same total bytes | 10-20 HTTP requests |

## Step 4: Gather Repository Context (All Local Reads)

Now that the needed files are checked out locally, gather context by reading them directly.

### 4a. Project structure overview

Even with sparse checkout, the **tree objects are fully available** — we can list the entire project structure without downloading any file content:

```bash
git ls-tree -r --name-only HEAD | head -200
```

This reveals the project's module organization, naming conventions, and architecture — without downloading a single blob.

### 4b. Coding conventions and config files

Read key project files (already checked out at repo root) to understand coding standards. Prioritize by relevance to the changed files' languages.

**AI agent instruction files** (highest priority — these define project conventions explicitly):

| File | Tool |
|---|---|
| `AGENTS.md` | Cross-tool standard (Codex, Cursor, Copilot, Amp, Windsurf, Devin) |
| `CLAUDE.md` | Claude Code |
| `GEMINI.md` | Gemini CLI |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.cursorrules` / `.cursor/rules/` | Cursor |
| `.windsurfrules` / `.windsurf/rules/` | Windsurf |

**Project and build config files**:

| File | Purpose |
|---|---|
| `README.md` | Project overview, setup instructions |
| `CONTRIBUTING.md` | Development guidelines, contribution rules |
| `pyproject.toml` / `setup.cfg` | Python project config, linting rules |
| `package.json` | Node.js project config, scripts, lint config |
| `.editorconfig` | Editor formatting rules |
| `.eslintrc.*` / `biome.json` | JS/TS linting rules |
| `Makefile` / `Justfile` | Build conventions |
| `Cargo.toml` | Rust project config |
| `go.mod` | Go module config |
| `.clang-format` / `.clang-tidy` | C/C++ formatting rules |

**Constraints:**
- Read at most 3-5 config files — prioritize the ones most relevant to the changed files' languages
- Skim only; skip files larger than ~50KB

### 4c. Full content of modified files

Read the **full current content** of PR-modified files to understand complete context around changes:
- All modified files are already checked out locally via sparse-checkout — just read them
- **Prioritize**: Read the top 5-8 most important modified files (by relevance, not just size)
- **Skip binary files** and **very large files** (>100KB) — only use the diff for those
- **For files with few changes** (< 5 lines added/deleted): The diff alone may suffice; skip full read
- **Focus on**: Files with substantive logic changes, new files, and files with the most additions

### 4d. Related files not in the diff (targeted)

If the diff references imports, base classes, interfaces, or function calls from files NOT in the PR:
- These should already be available if their directories were added in Step 3
- If not, on a partial clone git will **auto-fetch the blob on demand** when you read the file — no manual API calls needed
- Read **at most 2-3** related files for understanding correctness

## Step 5: Detect Language

Analyze user's input to determine review output language:
- Contains Chinese characters → Chinese review
- Only English → English review

## Step 6: Perform Code Review

Structure the review into these sections:

### If Chinese review requested:

#### 1. PR 概览
- PR 的目的和动机（基于标题、描述、分支名）
- 变更规模：X 个文件，+Y / -Z 行
- 涉及的主要模块和功能领域

#### 2. 仓库上下文分析
- 项目技术栈（语言、框架、工具链）
- 项目的编码规范和风格（基于 config 文件和已有代码推断）
- 此 PR 是否符合项目整体风格和架构模式

#### 3. 代码质量 & Clean Code 评价
- 全面评估变更的代码风格、命名、注释、可读性、可维护性、设计架构、模块解耦、重复代码等
- 特别关注：变更是否与项目现有代码风格一致
- 发现任何易错写法、不安全代码、低效实现、反模式或不符合最佳实践的地方要具体列出
- 指出被修改的具体位置与问题描述（文件名、代码片段，或足够明确的定位描述）
- 提出详细的修复/重构/优化建议，并解释理由

#### 4. 潜在的重大问题和风险
- 检查代码逻辑是否存在难以发现的 bug、异常未处理、未校验边界条件、性能瓶颈、安全隐患等
- 检查是否有遗漏的修改（如：改了接口但没改调用方，改了 schema 但没改迁移）
- 指出这些疑点，并简单说明为何值得关注

#### 5. 增量建议
- 给出进一步增强代码质量、工程可维护性、测试覆盖的建议
- 建议是否需要补充测试、文档、类型声明等
- 如果 PR 描述缺失或不清晰，建议改进 PR 描述

#### 6. 总结评价
- 给出整体评价：**Approve** / **Request Changes** / **Comment**
- 简要总结关键发现和建议优先级

### If English review requested:

#### 1. PR Overview
- Purpose and motivation of the PR (based on title, description, branch names)
- Change scope: X files changed, +Y / -Z lines
- Primary modules and functional areas affected

#### 2. Repository Context Analysis
- Project tech stack (languages, frameworks, toolchain)
- Project coding conventions and style (inferred from config files and existing code)
- Whether this PR aligns with the project's overall style and architectural patterns

#### 3. Code Quality & Clean Code Evaluation
- Thoroughly assess code style, naming conventions, comments, readability, maintainability, architecture, modularity, code duplication, etc.
- Pay special attention to: whether changes are consistent with existing project code style
- Identify error-prone code, unsafe patterns, inefficient implementations, anti-patterns, or violations of best practices
- Clearly specify the exact location and nature of each problem (filename, code snippet, or sufficiently precise description)
- Provide actionable suggestions for fixes/refactoring/optimization with explanatory reasoning

#### 4. Major Issues and Risks
- Evaluate hard-to-detect logic bugs, unhandled exceptions, missing boundary checks, performance bottlenecks, security vulnerabilities
- Check for missed changes (e.g., changed an interface but not its callers, changed a schema but not its migration)
- Point out suspicious areas and explain their potential impact

#### 5. Incremental Suggestions
- Suggestions for improving code quality, maintainability, and test coverage
- Whether additional tests, documentation, or type annotations are needed
- If PR description is missing or unclear, suggest improvements

#### 6. Summary Verdict
- Overall assessment: **Approve** / **Request Changes** / **Comment**
- Brief summary of key findings and suggestion priorities

## Step 7: Clean Up

After the review is complete:
- **Path B** (partial clone): Delete the temporary directory: `rm -rf "$TMPDIR"`
- **Path A** (existing repo): Restore the original branch: `git checkout "$ORIGINAL_BRANCH"`

## Error Handling

- **Known non-GitHub platform**: If URL matches GitLab, Gitee, or Bitbucket, stop immediately and inform the user this skill only supports GitHub PRs.
- **Unknown host / GHE auth failure**: If `gh pr view` fails with a host or auth error on an unknown domain, inform the user that the host may not be GitHub, or they need to authenticate with `gh auth login --hostname <host>` for GitHub Enterprise.
- **`gh` not installed**: Report error and suggest running `skills-check github-code-review-pr`
- **`gh` not authenticated**: Report error and suggest `gh auth login` (or `gh auth login --hostname <host>` for GHE)
- **PR not found**: Verify URL/number and repo access
- **Clone failure**: If partial clone fails (e.g., private repo without access), fall back to reviewing with diff-only context and report the limitation
- **Large PR (>50 files)**: Warn the user that review may be less thorough; focus on the most critical files
- **Binary files**: Skip binary files in review, note them as present
- **Private repo access**: If unauthorized, report clearly

## Examples

### Example 1: Review by URL (Chinese)
**User input**: "帮我审查一下这个 PR https://github.com/owner/repo/pull/42"
**Action**: Fetch PR metadata + diff → partial clone with sparse checkout → read context locally → review in Chinese
**Output**: 6-section Chinese review with repo-aware analysis

### Example 2: Review by URL (English)
**User input**: "Review this PR: https://github.com/owner/repo/pull/99"
**Action**: Fetch PR metadata + diff → partial clone with sparse checkout → read context locally → review in English
**Output**: 6-section English review with verdict

### Example 3: Review in current repo context
**User input**: "Review PR #15"
**Action**: Already in repo — just `gh pr checkout 15`, read context locally, review
**Output**: Context-aware review, restore original branch when done
