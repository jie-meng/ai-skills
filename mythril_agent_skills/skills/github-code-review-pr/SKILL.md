---
name: github-code-review-pr
description: >
  Comprehensive structured code review for Pull Requests via GitHub CLI (`gh`).
  TRIGGER THIS SKILL whenever the user asks to review a PR — regardless of the URL domain.
  Trigger phrases: 'review PR', 'review this PR', 'PR review', 'PR CR', '审查PR', '看这个PR',
  '看看这个PR', '帮我看PR', '帮我看这个PR', '帮我看一下这个PR',
  'review pull request', 'help me review', or ANY URL containing '/pull/' with a review request.
  This skill handles github.com AND GitHub Enterprise (any domain — GHE domains are arbitrary:
  git.company.com, git.corp.au, code.org.io, dev.internal.net, etc.).
  CRITICAL — ZERO SPECULATION RULE: When you see a /pull/ URL, run `gh` commands IMMEDIATELY.
  NEVER guess the platform from the domain name. Domains like `git.xxx.com`, `git.xxx.com.au`,
  `git.company.io` are NOT GitLab — they are commonly GitHub Enterprise. NEVER say "this looks like
  GitLab" or "this might not be GitHub". Just run `gh` and let it succeed or fail.
  Only reject URLs whose host literally contains the substring 'gitlab', or exactly matches
  'gitee.com' or 'bitbucket.org'. Every other domain MUST be attempted with `gh` first.
license: Apache-2.0
---

# When to Use This Skill

**ALWAYS invoke this skill when user wants to review a Pull Request:**
- "review this PR" / "review PR" / "PR review" / "PR code review"
- "审查这个PR" / "帮我看这个PR" / "PR审查" / "review pull request"
- "review https://github.com/owner/repo/pull/123"
- "帮我看一下这个 PR https://git.company.com/org/repo/pull/456"
- User provides ANY URL containing `/pull/` and asks for review/feedback
- User provides a PR number and asks for review/feedback
- "help me review this pull request"
- "use github-code-review-pr skill"

**CRITICAL — ZERO SPECULATION RULE**: Do NOT pre-filter by URL domain. Do NOT ask the user what platform a URL belongs to. GitHub Enterprise domains can be literally anything — `git.company.com`, `git.acmecorp.com`, `git.realestate.com.au`, `github.corp.example.com`, `code.org.io`, `dev.internal.net`, etc. A `git.xxx.com` or `git.xxx.com.au` domain is **NOT** an indicator of GitLab — these are extremely common GHE patterns. If the URL contains `/pull/`, trigger this skill, run `gh` commands immediately, and let `gh` CLI sort out platform compatibility. NEVER hesitate, speculate, or ask clarifying questions about the platform.

**This skill reviews remote PRs via `gh` CLI (not local staged changes).**
For local staged changes, use `code-review-staged` instead.

# Requirements

- **GitHub CLI (`gh`)** must be installed and authenticated
- **`curl`** must be available for downloading PR screenshots/assets
- **Optional for enterprise SSO**: `curl --negotiate -u :` support for SPNEGO/Kerberos-protected asset URLs
- Run `skills-check github-code-review-pr` to verify dependencies

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the values of any environment variable containing credentials (`GH_TOKEN`, `GITHUB_TOKEN`, etc.). Do NOT run commands like `echo $GH_TOKEN` or `printenv GITHUB_TOKEN` — even for debugging.
2. **NEVER pass token/credential values as inline CLI arguments or env-var overrides.** `gh` reads credentials from its own config — just run `gh` commands directly.
3. **When debugging auth errors**, rely solely on `gh auth status` output and `gh` error messages. Do NOT attempt to verify tokens by reading or printing them.

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

## Step 1: Parse PR Reference — Act First, Ask Never

Accept PR input in any of these formats:
- Full URL: `https://github.com/owner/repo/pull/123`
- GitHub Enterprise URL: `https://git.mycompany.com/owner/repo/pull/123` (domain can be literally anything)
- PR number (when inside a repo): `123`
- PR number with repo: `owner/repo#123`

**Platform handling — ZERO hesitation rule:**

**NEVER ask the user what platform a URL is.** NEVER speculate about whether a domain is "GitLab", "Bitbucket", or anything else based on the domain name. NEVER say things like "this looks like a GitLab instance" or "is this GitHub Enterprise?" — just run the `gh` command and let it succeed or fail.

**Common misconception**: Domains starting with `git.` (e.g., `git.company.com`, `git.realestate.com.au`, `git.corp.io`) are NOT indicators of GitLab. These are the most common GitHub Enterprise domain patterns. Do NOT let domain prefixes influence your judgment.

1. **Only reject URLs whose host literally contains the substring `gitlab`, or exactly matches `gitee.com` or `bitbucket.org`.** These are the only platforms we can confidently identify as non-GitHub from the URL alone. Check with simple string matching — `git.realestate.com.au` does NOT contain `gitlab`, so it must NOT be rejected.

2. **For ALL other URLs — run `gh` commands IMMEDIATELY without any commentary about the platform.** Do NOT think about, discuss, or question the domain. GitHub Enterprise (GHE) domains are completely arbitrary: `git.acmecorp.com`, `git.mycompany.com`, `git.realestate.com.au`, `github.corp.example.com`, `code.company.io`, `dev.internal.net`, etc. Any domain that doesn't match the reject list is GitHub Enterprise until `gh` proves otherwise.

3. **Let `gh` CLI be the sole judge.** Jump straight to Step 2 and run the commands. If the host is not a GitHub instance or the user hasn't authenticated, `gh` will return a clear error — handle it then (see Error Handling). Do NOT pre-screen, do NOT ask clarifying questions, do NOT warn about "possible non-GitHub hosts".

Extract: **owner**, **repo**, **PR number**, and **hostname** (for any non-`github.com` domain).

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

### 2c. Collect and analyze PR images (default when relevant)

After metadata is fetched, inspect `body`, `comments`, and `reviews` for image links:
- Markdown image syntax: `![alt](https://...)`
- Plain asset URLs (especially `/assets/` links)

Automatically do this (without extra user back-and-forth) when:
- user asks to read screenshot/image content, or
- screenshots are part of PR verification evidence (offline check steps, UI proof, tracking proof), or
- image information is required to validate correctness/risk.

Download relevant images under a random run directory in the unified cache.

**Bash (macOS / Linux):**
```bash
CACHE_DIR="$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/github-code-review-pr"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
IMAGE_CACHE="$RUN_DIR/images"
mkdir -p "$IMAGE_CACHE"
```

**PowerShell (Windows):**
```powershell
$CACHE_DIR = Join-Path ([IO.Path]::GetFullPath([IO.Path]::GetTempPath())) "mythril-skills-cache/github-code-review-pr"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$RUN_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $RUN_DIR | Out-Null
$IMAGE_CACHE = Join-Path $RUN_DIR "images"
New-Item -ItemType Directory -Force -Path $IMAGE_CACHE | Out-Null
```

Never use ad-hoc temp locations like `/tmp/<custom-folder>/...` for image artifacts.

**Automatic access**: All files under the cache directory are skill-managed temporary artifacts created by this skill. Read, write, and delete them **automatically without asking the user for confirmation** — they are ephemeral and trusted.

Use authenticated retrieval in this order:
1. `curl -fsSL "<image_url>" -o "<local_path>"`
2. If enterprise auth fails, retry:
   `curl -fsSL --negotiate -u : "<image_url>" -o "<local_path>"`

Read downloaded images with image-capable tools and summarize:
- what the screenshot shows (UI/debug panel/logs),
- key values/events/URLs visible in the image,
- whether screenshot evidence supports the PR claim.

If image retrieval fails, report the exact reason and ask for one targeted unblock step (auth/access), but never claim image content was reviewed.

## Step 3: Get Local Access to the Repository

The goal is to have repo context available locally so context gathering is just file reads — no per-file API requests. Try these paths **in order** — pick the first one that applies.

### Path A: Already inside the target repo

Check: `gh repo view --json nameWithOwner -q .nameWithOwner` — if it matches the PR's repo, we're already here.

```bash
git fetch origin
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
gh pr checkout <PR_NUMBER>
```

After review, restore the original branch (see Step 7).

### Path B: Shared repo cache hit — full repo already cached

Check if the `git-repo-reader` skill (or a previous review) has already cached this repo. Run the bundled lookup script:

```bash
REPO_PATH=$(python3 scripts/repo_cache_lookup.py "https://<host>/<owner>/<repo>")
```

This is a **read-only** lookup — it checks the shared `git-repo-cache` mapping file and prints the local path if found (exit 0), or exits 1 if not cached. It never clones or modifies anything.

If cache hit (exit 0), update the cached repo and checkout the PR:

```bash
cd "$REPO_PATH"

# Fetch the base branch so origin/<baseRefName> is current for diff comparison
git fetch origin <baseRefName>

# Checkout the PR branch (gh internally fetches refs/pull/<N>/head)
gh pr checkout <PR_NUMBER>
```

After `gh pr checkout`, `HEAD` points to the PR's latest code. For base branch comparison, use `origin/<baseRefName>` (the remote-tracking ref, guaranteed fresh after the fetch).

**Important**: Always use `origin/<baseRefName>` (not a local branch) as the comparison target — this is the freshest ref and avoids stale-local-branch issues. No need to manually fetch `<headRefName>` — `gh pr checkout` already fetches the PR head ref internally.

### Path C: No cached repo — blobless clone to temp directory

If neither Path A nor Path B applies, use **blobless clone + sparse checkout** to avoid downloading the entire repo. This downloads all commits, tree objects, and branch refs on clone — but **file contents (blobs) are NOT downloaded until explicitly checked out**. Even for a multi-GB monorepo, the initial clone is typically just a few MB.

**Why NOT `--depth=1` or `--single-branch`**: `gh pr checkout` needs to fetch `refs/pull/<N>/head` and set up tracking. With `--single-branch` the refspec is restricted to one branch, causing `gh pr checkout` to fail with `fatal: cannot set up tracking information`. `--depth=1` implies `--single-branch`. Using `--filter=blob:none --sparse` (without depth/single-branch) gives us all refs and history metadata at minimal cost — blobs are only fetched when files are actually checked out.

Create a temp directory under the **unified skill cache**:

**Bash (macOS / Linux):**
```bash
CACHE_DIR="$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/github-code-review-pr"
mkdir -p "$CACHE_DIR"
REVIEW_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
gh repo clone <owner/repo> "$REVIEW_DIR" -- --filter=blob:none --sparse
cd "$REVIEW_DIR"
```

**PowerShell (Windows):**
```powershell
$CACHE_DIR = Join-Path ([IO.Path]::GetFullPath([IO.Path]::GetTempPath())) "mythril-skills-cache/github-code-review-pr"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$REVIEW_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $REVIEW_DIR | Out-Null
gh repo clone <owner/repo> "$REVIEW_DIR" -- --filter=blob:none --sparse
Set-Location $REVIEW_DIR
```

Now the repo is cloned with sparse checkout already enabled (cone mode). The working directory contains only root-level files (README.md, AGENTS.md, pyproject.toml, etc.) — no subdirectories are checked out yet.

Add directories needed for review based on the PR metadata from Step 2:

**1. Directories containing PR-modified files** — extract from the `files` list in Step 2a:
```bash
git sparse-checkout add src/components src/utils tests/unit
```
Only add the directories that contain files changed in the PR. This pulls just those directory trees.

**2. Directories for related files** — if the diff references imports or base classes from other paths, add those too:
```bash
git sparse-checkout add src/types src/shared
```

Now checkout the PR branch to get the PR's version of those files:
```bash
gh pr checkout <PR_NUMBER>
```

After review, delete the temp directory (see Step 7).

### Path selection summary

| Path | Condition | Speed | Context depth |
|---|---|---|---|
| A | Already inside target repo | Instant | Full repo |
| B | Repo found in shared cache | Fast (just `fetch` two branches) | Full repo |
| C | Repo not cached | Moderate (blobless clone) | Targeted files only |

## Step 4: Gather Repository Context

### For Path A and Path B (full repo available)

The full repo is available locally. Read files directly — git auto-fetches blob content on demand if using a blobless clone.

#### 4a. Project structure overview

```bash
git ls-tree -r --name-only HEAD | head -200
```

This reveals the project's module organization, naming conventions, and architecture.

#### 4b. Coding conventions and config files

Read key project files to understand coding standards. Prioritize by relevance to the changed files' languages.

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

#### 4c. Full content of modified files

Read the **full current content** of PR-modified files to understand complete context around changes. Use a **change-volume driven** strategy instead of a fixed file count:

- **> 50 lines changed** (additions + deletions): Must read full file — major changes require complete context
- **5-50 lines changed**: Read full file — surrounding code is important for correctness judgment
- **< 5 lines changed**: The diff alone may suffice; skip full read unless the change is in a critical path (e.g., security, auth, financial logic)
- **New files**: Always read in full (subject to the size limit below)
- **Skip binary files** and **very large files** (>100KB) — only use the diff for those. This size limit applies to ALL files, including new files

#### 4d. Related files not in the diff (targeted)

If the diff references imports, base classes, interfaces, or function calls from files NOT in the PR:
- Just read the file directly — git auto-fetches the blob on demand
- Read **3-5** related files that are strictly necessary to validate the correctness of the changes
- Only read files where understanding their content directly affects review quality (e.g., interface definitions, base classes, callers of changed functions, related tests)

### For Path C (blobless clone with sparse checkout)

#### 4a. Project structure overview

Even with sparse checkout, the **tree objects are fully available**:

```bash
git ls-tree -r --name-only HEAD | head -200
```

This reveals the full project structure without downloading any file content.

#### 4b. Coding conventions and config files

Same as above — root-level files are already checked out via `--sparse` on clone.

#### 4c. Full content of modified files

Same change-volume driven strategy as above. All modified files are already checked out via sparse checkout of their directories.

#### 4d. Related files not in the diff (targeted)

If the diff references files from directories NOT already in sparse checkout, add them:
```bash
git sparse-checkout add <directory>
```
Git will auto-fetch the needed blobs. Read 3-5 related files that are strictly necessary to validate correctness.

### Accessing other repositories during review

If the user provides a URL to another repository during the review (e.g., a backend API repo to verify schema compatibility), **do NOT clone it yourself** into the review cache. Instead, delegate to the `git-repo-reader` skill — it will clone the repo into the shared cache and let you read it. This is better because:
- The clone is cached and reusable across sessions
- It avoids duplicating clone logic inside this skill
- Future reviews or questions about that repo will hit the cache instantly

If the `git-repo-reader` skill is not available, fall back to a blobless clone in the review cache (same as Path C).

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
- 若 PR 含截图/图片证据，补充 **图片证据摘要**：逐张说明图片内容、关键信息、与代码变更的对应关系

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
- If screenshots/images are present, include a **Visual Evidence Summary**: what each image shows, key observed values/events, and how it maps to PR claims

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

**This step is MANDATORY — always execute it, even if the review encountered errors.**

After the review is complete:
- **Path A** (existing repo): Restore the original branch: `git checkout "$ORIGINAL_BRANCH"`
- **Path B** (shared repo cache): Reset to a clean state on the default branch so the cached repo is ready for the next use:
  ```bash
  cd "$REPO_PATH"
  DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD --short 2>/dev/null | sed 's|origin/||')
  git checkout "${DEFAULT_BRANCH:-main}"
  git reset --hard "origin/${DEFAULT_BRANCH:-main}"
  git clean -fd
  ```
  **Do NOT delete the cached repo** — it is shared and will be reused.
- **Path C** (blobless clone): Delete the temp directory: `rm -rf "$REVIEW_DIR"`

Image artifacts and Path C temp directories live under `mythril-skills-cache/github-code-review-pr/`. If leftovers accumulate (e.g., from interrupted sessions), the user can run:
```bash
skills-clean-cache
```

## Error Handling

- **Known non-GitHub platform**: Only if URL host literally contains `gitlab`, or exactly matches `gitee.com` or `bitbucket.org` — stop and inform the user.
- **`gh` host/auth error on unknown domain**: This is the expected outcome when a non-github.com host hasn't been configured. Tell the user:
  1. This host might be GitHub Enterprise — run `gh auth login --hostname <host>` to authenticate
  2. If it's not GitHub at all, this skill only supports GitHub (including GHE)
  - **Do NOT assume the host is "GitLab" or any other platform** — just report the `gh` error and let the user decide. Domains like `git.xxx.com` or `git.xxx.com.au` are commonly GHE, not GitLab.
- **`gh` not installed**: Report error and suggest running `skills-check github-code-review-pr`
- **`gh` not authenticated for github.com**: Report error and suggest `gh auth login`
- **PR not found**: Verify URL/number and repo access
- **PR image download failed**: report URL + HTTP/auth error; retry with enterprise SSO (`curl --negotiate -u :`) when applicable; if still blocked, clearly state image analysis is incomplete
- **Clone failure**: If blobless clone fails (e.g., private repo without access), fall back to reviewing with diff-only context and report the limitation
- **Large PR (>50 files)**: Warn the user that review may be less thorough; focus on the most critical files
- **Binary files**: Skip binary files in review, note them as present
- **Private repo access**: If unauthorized, report clearly

## Examples

### Example 1: Review by URL — repo already in cache (Chinese)
**User input**: "帮我审查一下这个 PR https://github.com/owner/repo/pull/42"
**Action**: Fetch PR metadata + diff → cache lookup finds repo (Path B) → fetch PR branches → checkout → read context locally → review in Chinese
**Output**: 6-section Chinese review with full repo context

### Example 2: Review by URL — repo not cached (English)
**User input**: "Review this PR: https://github.com/owner/repo/pull/99"
**Action**: Fetch PR metadata + diff → cache miss → blobless clone to temp dir (Path C) → sparse checkout → review in English
**Output**: 6-section English review with targeted context

### Example 3: Review in current repo context
**User input**: "Review PR #15"
**Action**: Already in repo (Path A) → fetch latest → `gh pr checkout 15`, read context locally, review
**Output**: Context-aware review, restore original branch when done

### Example 4: GitHub Enterprise URL (unknown domain)
**User input**: "帮我看一下这个 PR https://git.realestate.com.au/mobile-team/app-ios/pull/16323"
**Action**: Domain `git.realestate.com.au` does NOT contain 'gitlab', does NOT match 'gitee.com' or 'bitbucket.org' → proceed immediately → run `gh pr view https://git.realestate.com.au/...` → if auth error, tell user to run `gh auth login --hostname git.realestate.com.au`
**Output**: Either full review (if GHE is configured) or clear auth setup instructions
**WRONG behavior**: Saying "this looks like GitLab" or asking the user what platform it is — NEVER do this

## Post-Review: Adding Comments to the PR

After the review is delivered, the user may ask to send comments about specific issues back to the PR. Follow these rules to determine the correct comment type.

### Default: Inline line-level comments (like "Files changed" tab)

When the user asks to add a comment and ANY of these conditions apply, use an **inline line-level review comment** (equivalent to clicking `+` on a specific line in the "Files changed" tab on GitHub):

- The user refers to a specific line, code block, or code snippet from the review
- The user copies/pastes part of the review analysis that identifies a specific code issue
- The user says things like "comment on that line", "add comment there", "给那行加个评论", "在那里加 comment"
- The review analysis already identified a specific file and line for the issue — the user is just asking to post it

This is the **default** behavior. If there is any ambiguity about whether the user wants inline vs. general, **choose inline**.

**How to post an inline comment:**

```bash
# Get the PR head commit SHA
HEAD_SHA=$(gh pr view <URL_or_NUMBER> --json headRefOid -q .headRefOid)

# For github.com repos:
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments \
  -X POST \
  -f body='Your review comment here' \
  -f commit_id="$HEAD_SHA" \
  -f path='path/to/file.kt' \
  -F line=42 \
  -f side='RIGHT'

# For GitHub Enterprise (custom host):
gh api --hostname <host> repos/OWNER/REPO/pulls/PR_NUMBER/comments \
  -X POST \
  -f body='Your review comment here' \
  -f commit_id="$HEAD_SHA" \
  -f path='path/to/file.kt' \
  -F line=42 \
  -f side='RIGHT'
```

- `path`: The file path relative to the repo root (from the PR diff)
- `line`: The line number in the diff's new version of the file (RIGHT side)
- `side`: Use `RIGHT` for commenting on the new code (most common), `LEFT` for the old/deleted code
- `commit_id`: Must be the HEAD SHA of the PR branch

**Determining the correct line number**: Use the PR diff from Step 2b to find the exact line number. The `line` parameter refers to the line number shown on the RIGHT side of the diff (the new version). Match the code snippet from the review to the diff to find the correct line.

### Exception: General PR-level comment

Use a **general PR comment** (appears at the bottom of the PR's "Conversation" tab) ONLY when:

- The user explicitly says "给 PR 写一个 comment", "add a comment to the PR", "leave a general comment"
- The comment is about the PR as a whole (e.g., overall architecture feedback, summary of review findings) and does not reference any specific code line
- The user asks to post the full review summary as a comment

```bash
gh pr comment <URL_or_NUMBER> --body "Your general comment here"
```

### Examples

**Inline comment (default):**
- User: "把第3点关于空指针的问题发个 comment" → Find the file and line from review point #3, post inline comment
- User: "send a comment about the missing null check" → Find the relevant line from the diff, post inline comment
- User: "给这段代码加个评论: `val result = api.fetch()` 没有错误处理" → Find where this code appears in the diff, post inline comment

**General comment:**
- User: "给这个 PR 写一个总结 comment" → Post general PR comment
- User: "leave a comment summarizing the review" → Post general PR comment
