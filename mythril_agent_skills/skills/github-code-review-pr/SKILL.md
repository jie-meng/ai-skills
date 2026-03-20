---
name: github-code-review-pr
description: >
  Comprehensive Pull Request code review via GitHub CLI (`gh`). MANDATORY TRIGGER:
  You MUST use this skill for ANY URL containing `/pull/` (unless the URL literally
  contains 'gitlab', 'gitee', or 'bitbucket'). If the user asks to review/审查/评审/CR
  a PR or requests code-quality analysis, you MUST trigger this skill.
  CRITICAL: Treat ALL unknown domains (e.g., git.company.com) as valid targets.
  NEVER guess, evaluate, or reason about what git platform the domain belongs to
  based on your internal knowledge. Do not try to be smart. Just trigger this skill
  and let the `gh` command handle any platform or auth errors. This skill is for deep
  review output. For routine PR actions, prefer `gh-operations`.
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

**CRITICAL — ZERO SPECULATION RULE**: Do NOT pre-filter by URL domain. Do NOT ask the user what platform a URL belongs to. GitHub Enterprise domains can be literally anything — `git.company.com`, `git.acmecorp.com`, `git.example.com`, `github.corp.example.com`, `code.org.io`, `dev.internal.net`, etc. A `git.xxx.com` or `git.xxx.com.au` domain is **NOT** an indicator of GitLab — these are extremely common GHE patterns. If the URL contains `/pull/`, trigger this skill, run `gh` commands immediately, and let `gh` CLI sort out platform compatibility. NEVER hesitate, speculate, or ask clarifying questions about the platform.

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

**Common misconception**: Domains starting with `git.` (e.g., `git.company.com`, `git.example.com`, `git.corp.io`) are NOT indicators of GitLab. These are the most common GitHub Enterprise domain patterns. Do NOT let domain prefixes influence your judgment.

1. **Only reject URLs whose host literally contains the substring `gitlab`, or exactly matches `gitee.com` or `bitbucket.org`.** These are the only platforms we can confidently identify as non-GitHub from the URL alone. Check with simple string matching — `git.example.com` does NOT contain `gitlab`, so it must NOT be rejected.

2. **For ALL other URLs — run `gh` commands IMMEDIATELY without any commentary about the platform.** Do NOT think about, discuss, or question the domain. GitHub Enterprise (GHE) domains are completely arbitrary: `git.acmecorp.com`, `git.mycompany.com`, `git.example.com`, `github.corp.example.com`, `code.company.io`, `dev.internal.net`, etc. Any domain that doesn't match the reject list is GitHub Enterprise until `gh` proves otherwise.

3. **Let `gh` CLI be the sole judge.** Jump straight to Step 2 and run the commands. If the host is not a GitHub instance or the user hasn't authenticated, `gh` will return a clear error — handle it then (see Error Handling). Do NOT pre-screen, do NOT ask clarifying questions, do NOT warn about "possible non-GitHub hosts".

### Forbidden platform speculation text (MANDATORY)

Before running `gh`, never output any sentence that classifies or guesses the platform.

Forbidden examples (must not appear in user-visible output):
- "This is not a GitHub URL"
- "This looks like GitLab/Bitbucket/Gitea"
- "Possibly self-hosted git platform"
- "This appears to be ..."

Allowed behavior:
- Immediately run `gh pr view <URL>` and `gh pr diff <URL>`
- If those commands fail, report the exact `gh` error and follow Error Handling
- If those commands succeed, describe facts only (for example, "`gh` commands succeeded for this host")

Extract: **owner**, **repo**, **PR number**, and **hostname** (for any non-`github.com` domain).

**Canonical ref rule (avoid duplicate retries):**
- If user input is a full PR URL, treat that URL as the canonical PR reference for all `gh` commands.
- Do NOT first try `owner/repo` shorthand and then retry with URL.
- Only switch format when `gh` returns a clear parsing/request error that requires a different format.

## Step 2: Fetch PR Metadata and Diff

### MANDATORY: Use the bundled runner script

**Do NOT manually run `gh pr view` or `gh pr diff`.** Always use the bundled runner script — it performs Step 2, Step 3 (path selection + checkout), and cleanup wiring in a single deterministic call:

```bash
python3 scripts/review_runner.py prepare <URL_or_NUMBER>
```

Locate the script from known skill install locations (same search pattern as `path_select.py` — check `~/.cursor/skills/`, `~/.claude/skills/`, `~/.copilot/skills/`, `~/.config/opencode/skills/`, `~/.gemini/skills/`, `~/.codex/skills/` under `github-code-review-pr/scripts/review_runner.py`).

This command:
1. Fetches PR metadata (`gh pr view`) and diff (`gh pr diff`) exactly once
2. Runs `path_select.py` (A → B → C selection with `[PATH-CHECK]`/`[PATH-SELECTED]` trace)
3. Handles checkout with fallback (`pull/<PR>/head`)
4. Saves all outputs to a session manifest

Machine-readable output lines:
- `RUN_MANIFEST=<path>` — session manifest JSON (needed for cleanup and gate scripts)
- `PR_VIEW_JSON_PATH=<path>` — saved PR metadata JSON file
- `PR_DIFF_PATH=<path>` — saved PR diff file
- `SELECTED_PATH=A|B|C` — which path was selected
- `REPO_WORKDIR=<path>` — local repo directory (empty if diff-only)
- `PR_STATE=OPEN|CLOSED|MERGED` — PR state
- `CONTEXT_MODE=full_repo|diff_only` — whether full repo context is available
- `CONTEXT_LIMITATION=<message>` — explanation when context is limited

**After `review_runner.py prepare` succeeds:**
- Read PR metadata from `PR_VIEW_JSON_PATH` (do NOT re-run `gh pr view`)
- Read PR diff from `PR_DIFF_PATH` (do NOT re-run `gh pr diff`)
- Skip Step 3 entirely — path selection and checkout are already done
- Save `RUN_MANIFEST` for use in Step 6 gate and Step 7 cleanup

### Fallback: Manual commands (ONLY if review_runner.py is not found)

If and only if `review_runner.py` cannot be located at any install path, fall back to manual commands. **You MUST still run `path_select.py` before any clone/fetch** (see Step 3).

#### 2a. PR metadata
```bash
GH_PAGER=cat gh pr view <URL_or_NUMBER> --json number,title,body,state,author,baseRefName,headRefName,labels,reviewDecision,additions,deletions,changedFiles,commits,files,comments,reviews,url
```

Key fields:
- `title`, `body` — PR description and intent
- `baseRefName`, `headRefName` — branches involved
- `files` — list of changed files with `path`, `additions`, `deletions`
- `commits` — commit history in the PR
- `comments`, `reviews` — existing discussion context
- `url` — used to extract `owner/repo`

#### 2b. PR diff
```bash
GH_PAGER=cat gh pr diff <URL_or_NUMBER>
```

#### 2b.1 Single-fetch rule (avoid repeated network calls)

- Fetch metadata and diff once, then reuse the captured output throughout the review.
- Do NOT re-run `gh pr diff`/`gh pr view` unless output is missing/corrupted or PR head changed during review.
- If a re-fetch is required, state the reason explicitly.

Enforcement rule:
- Persist first successful outputs to variables/files (for example `PR_VIEW_JSON_PATH`, `PR_DIFF_PATH`) and reuse them for all later analysis.
- Any second `gh pr view`/`gh pr diff` call MUST include a log line in advance: `[REFETCH-REASON] <specific reason>`.
- "Need to read another section" is NOT a valid reason; read from the previously captured output instead.

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
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/github-code-review-pr"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
IMAGE_CACHE="$RUN_DIR/images"
mkdir -p "$IMAGE_CACHE"
```

**PowerShell (Windows):**
```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "github-code-review-pr"
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

### Skip condition: If `review_runner.py prepare` was used in Step 2

**Skip this entire Step 3.** The runner already executed path selection, checkout, and fallback handling. Use the `SELECTED_PATH`, `REPO_WORKDIR`, and `CONTEXT_MODE` values from the runner output and proceed directly to Step 4.

The rest of Step 3 below is the **manual fallback path** — only execute it when `review_runner.py` was NOT available and you used manual Step 2 commands.

### Path Selection Script (MANDATORY when not using review_runner.py — run first, before any clone or fetch)

**Do NOT write inline path-check logic.** Instead, run the bundled `path_select.py` script. It checks A → B → C in order and prints `[PATH-CHECK]` / `[PATH-SELECTED]` lines as it runs — guaranteeing the trace appears in the execution log at decision time, not as prose in the final review output.

The script lives alongside this SKILL.md at `scripts/path_select.py`. Locate and run it using Python directly — do NOT use shell `eval` or complex shell expansions, as these may be blocked by shell safety filters in some AI tools:

```python
import subprocess, os, pathlib

# Step 1: locate path_select.py from known install locations
search_dirs = [
    pathlib.Path.home() / ".config/opencode/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".claude/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".copilot/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".cursor/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".gemini/skills/github-code-review-pr/scripts",
    pathlib.Path.home() / ".codex/skills/github-code-review-pr/scripts",
]
script = next((d / "path_select.py" for d in search_dirs if (d / "path_select.py").exists()), None)

# Step 2: get current repo (empty string if not inside any repo or gh unavailable)
result = subprocess.run(
    ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
    capture_output=True, text=True, env={**os.environ, "GH_PAGER": "cat"}
)
current_repo = result.stdout.strip() if result.returncode == 0 else ""

# Step 3: run path selection — prints [PATH-CHECK] / [PATH-SELECTED] trace lines
# and prints machine-readable lines: SELECTED_PATH=..., REPO_PATH=...
output = subprocess.run(
    ["python3", str(script), "https://<host>/<owner>/<repo>", current_repo],
    capture_output=False  # prints trace directly to stdout
)
```

After the script runs, read `SELECTED_PATH` and `REPO_PATH` from the `KEY=VALUE` lines in the output (parse from stdout if needed), or re-run with `capture_output=True` to parse programmatically.

**Rules:**
- Run this block before any `git fetch`, `git checkout`, or clone command.
- Do not proceed to Step 4 until `[PATH-SELECTED]` is visible in the log.
- Do NOT re-implement path-check logic inline — always use the script.

### Execution guardrail (MANDATORY)

Immediately after parsing `SELECTED_PATH` / `REPO_PATH`, register cleanup handling for Step 7.
Do this **before** any fetch/checkout/clone command so cleanup still runs on mid-review failures.

- Keep `SELECTED_PATH` in a shell variable for cleanup branching.
- For Path A, capture `ORIGINAL_BRANCH` immediately.
- For Path B, capture `REPO_PATH` and resolve `DEFAULT_BRANCH` once.
- For Path C, capture created temp dirs (`REVIEW_DIR`, `RUN_DIR`) as soon as they are created.
- Use an `EXIT` trap (or equivalent) so cleanup executes whether review succeeds, partially fails, or exits early.

### Path A: Already inside the target repo

When `SELECTED_PATH=A`, proceed immediately:

```bash
git fetch origin <baseRefName> <headRefName>
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git checkout <headRefName>
```

Same reasoning as Path B: use `git checkout <headRefName>` directly (branch name known from Step 2a) rather than `gh pr checkout`, which can fail on Enterprise hosts that require separate `gh auth login --hostname` even when `gh pr view/diff` works.

After review, restore the original branch (see Step 7).

### Path B: Shared repo cache hit — full repo already cached

When `SELECTED_PATH=B`, `$REPO_PATH` is already set by the path-selection script above.

Update the cached repo and checkout the PR branch. `headRefName` is already known from Step 2a metadata — use it directly:

```bash
cd "$REPO_PATH"

# Fetch both branches: base for diff comparison, head for the PR code
git fetch origin <baseRefName> <headRefName>

# Checkout the PR branch using the branch name from metadata
git checkout <headRefName>
```

If the command above fails (missing remote branch, force-pushed branch, stale refs, or host-specific behavior), do **not** silently continue as if full repo context were available.

Run this mandatory fallback sequence:

```bash
# Keep error output for the final review limitation note
FETCH_ERR="$(git fetch origin <baseRefName> <headRefName> 2>&1)" || true

if ! git rev-parse --verify --quiet "origin/<headRefName>" >/dev/null; then
  # Fallback: fetch PR head ref directly by PR number
  git fetch origin "pull/<PR_NUMBER>/head:pr-<PR_NUMBER>-head" 2>&1 || true
fi

if git rev-parse --verify --quiet "origin/<headRefName>" >/dev/null; then
  git checkout <headRefName>
elif git rev-parse --verify --quiet "pr-<PR_NUMBER>-head" >/dev/null; then
  git checkout "pr-<PR_NUMBER>-head"
else
  CONTEXT_MODE="diff_only"
  CONTEXT_LIMITATION="Path B branch checkout failed: ${FETCH_ERR:-unknown fetch error}"
fi
```

When `CONTEXT_MODE=diff_only`:
- Continue review using Step 2 metadata + diff only (no fake local-context claims)
- Explicitly state this limitation in the review output
- **Still run Step 7 cleanup** and print `[PATH-CLEANUP] ...` status lines

**Why `git checkout <headRefName>` instead of `gh pr checkout`**: `gh pr checkout` can fail if the host hasn't been authenticated with `gh auth login --hostname <host>`, even when `gh pr view/diff` succeeds (those commands may use a different auth path). Since `headRefName` is already known from Step 2a metadata and the branch is available after `git fetch origin <headRefName>`, using `git checkout` directly is more reliable and avoids this failure mode.

For base branch comparison, use `origin/<baseRefName>` (the remote-tracking ref, guaranteed fresh after the fetch).

### Path C: No cached repo — blobless clone to temp directory

When `SELECTED_PATH=C`, use **blobless clone + sparse checkout** to avoid downloading the entire repo. This downloads all commits, tree objects, and branch refs on clone — but **file contents (blobs) are NOT downloaded until explicitly checked out**. Even for a multi-GB monorepo, the initial clone is typically just a few MB.

**Why NOT `--depth=1` or `--single-branch`**: With `--single-branch` the refspec is restricted to one branch, making it impossible to later `git fetch origin <headRefName>` for a different branch. `--depth=1` implies `--single-branch`. Using `--filter=blob:none --sparse` (without depth/single-branch) gives us all refs and history metadata at minimal cost — blobs are only fetched when files are actually checked out.

**Path C location rule (MANDATORY):** Clone directly into the unified skill cache — never use `/tmp`, `$TMPDIR`, or any ad-hoc directory. The `path_select.py` trace already shows the target cache dir; clone into a fresh subdirectory of that path.

Create a temp directory under the **unified skill cache**:

**Bash (macOS / Linux):**
```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/github-code-review-pr"
mkdir -p "$CACHE_DIR"
REVIEW_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
gh repo clone <owner/repo> "$REVIEW_DIR" -- --filter=blob:none --sparse
cd "$REVIEW_DIR"
```

**PowerShell (Windows):**
```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "github-code-review-pr"
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
git fetch origin <headRefName>
git checkout <headRefName>
```

(Use `git checkout <headRefName>` directly — same reasoning as Path A/B: more reliable than `gh pr checkout` on Enterprise hosts.)

After review, delete the temp directory (see Step 7).

### Path selection summary

| Path | Condition | Speed | Context depth |
|---|---|---|---|
| A | Already inside target repo | Instant | Full repo |
| B | Repo found in shared cache | Fast (just `fetch` two branches) | Full repo |
| C | Repo not cached | Moderate (blobless clone) | Targeted files only |

Note: Path B can temporarily degrade to diff-only mode if branch fetch/checkout fails. This is allowed only when the fallback sequence above is attempted and logged.

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

### Evidence certainty rules (MANDATORY)

- Separate **confirmed findings** from **potential risks**.
- A confirmed finding must be directly supported by evidence from the diff, file content, or PR metadata.
- A potential risk must be labeled as such (e.g., "Potential risk") and include one concrete validation step.
- Do NOT present speculative runtime/CI behavior as established fact without direct evidence.

### Finding classification format (MANDATORY)

The final review must separate findings into two explicit groups:

- `Confirmed Findings` / `已确认问题`: only evidence-backed issues
- `Potential Risks` / `潜在风险`: hypotheses that still need validation

Classification constraints:
- Every item must be in exactly one group (never both)
- Every `Potential risk` item must include one concrete validation step
- If no confirmed issues exist, explicitly write `Confirmed Findings: none`
- If no potential risks exist, explicitly write `Potential Risks: none`

### Internal consistency check (MANDATORY before final output)

Run this final check before sending the review:

1. Remove any item that was later disproven during the same review run.
2. Do not keep self-contradicting pairs like "Issue: X" and later "No issue for X".
3. If investigation shows "not an issue", keep only the final conclusion and delete the earlier suspicion from issue lists.
4. Ensure the verdict (`Approve` / `Request Changes` / `Comment`) matches the final issue severity.

### Review output structure (MANDATORY — use exactly these 6 sections)

**Do NOT create ad-hoc section structures** like "Strengths / Issues / What's Working Well". The review MUST use exactly the 6 sections defined below, in order. Every review must include all 6 sections.

**RECOMMENDED: Generate review skeleton first.** Before filling in review content, generate a deterministic skeleton to reduce structural drift:

```bash
python3 scripts/review_template_builder.py \
  --manifest <RUN_MANIFEST> \
  --output <REVIEW_DRAFT_PATH> \
  --language en
```

Use the generated skeleton as the structural foundation for your review. Fill in each `[fill]` placeholder with evidence from the PR metadata, diff, and repo context. Do NOT invent a different section structure.

**CRITICAL: Do NOT send the review to the user yet.** After completing all 6 sections, you MUST proceed to Step 7 (cleanup + gate) before presenting any review output. Write the review content to a temp file and continue to Step 7.

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

## Step 7: Clean Up, Gate, and Send

**This step is MANDATORY — always execute it, even if the review encountered errors.**

This step has three sub-steps that MUST be executed in order. **Do NOT send the review to the user until sub-step 7c passes.**

### 7a. Run cleanup (restore repo, keep session files)

Execute cleanup to restore the repo state (branch checkout / reset). This does **NOT** delete the session `run_dir` — the manifest and command log must remain readable for the gate script in 7b.

```bash
python3 scripts/review_runner.py cleanup <RUN_MANIFEST> 2>&1 | tee /tmp/cleanup_log.txt
```

This prints `[PATH-CLEANUP] ...` evidence lines. **Save the stdout to a file** — it is needed for the gate script in 7b.

If `review_runner.py` was NOT available (manual Step 2/3 path), use the manual cleanup shell function defined in "Fallback: Manual cleanup" below instead.

### 7b. Run the quality gate (MANDATORY)

**You MUST run the gate script before presenting review output to the user.** Do NOT skip this step. Do NOT perform the checklist mentally — the script enforces it programmatically.

1. **Save the review text to a file** (the complete 6-section review you prepared in Step 6):

```bash
cat > /tmp/review_text.md << 'REVIEW_EOF'
<paste your complete review content here>
REVIEW_EOF
```

2. **Run the gate script** (the manifest and command log still exist because cleanup preserved them):

```bash
python3 scripts/review_output_gate.py \
  --manifest <RUN_MANIFEST> \
  --review-text /tmp/review_text.md \
  --cleanup-log /tmp/cleanup_log.txt
```

3. **Interpret the result:**
   - Exit code `0` → all gates pass → proceed to 7c (send the review)
   - Exit code non-zero → read the FAIL details, fix the violations in your review text, and re-run the gate

**If `review_output_gate.py` is not found**, perform this checklist manually and document each PASS/FAIL:

1. `NO_SPECULATION_PASS` — No platform-guessing text appears before the first `gh` command.
2. `SINGLE_FETCH_PASS` — `gh pr view` and `gh pr diff` were each executed exactly once.
3. `CLEANUP_EVIDENCE_PASS` — `[PATH-CLEANUP]` marker is present in cleanup output.
4. `VERDICT_STATE_PASS` — Verdict is consistent with PR state (no `Request Changes` on merged/closed PRs unless user explicitly asked).

### 7c. Send the review and purge session

**Only after the gate passes (7b exit code 0), present the review to the user.** Output the review content exactly once — do NOT output a draft version before the gate and then output again after.

**CRITICAL: Present the full 6-section review as-is.** Do NOT summarize, condense, or restructure the review into a shorter format (e.g., "关键问题 / 优点 / 建议" bullet list). The user must see all 6 sections with their original content. The 6-section structure IS the deliverable — not raw material for a summary.

After sending the review, delete the session artifacts:

```bash
python3 scripts/review_runner.py purge <RUN_MANIFEST>
```

This removes the `run_dir` (manifest, diff, metadata, command log). The purge is a housekeeping step — if it fails or is skipped, `skills-clean-cache` will clean up later.

### Fallback: Manual cleanup (ONLY if review_runner.py was not used)

#### Failure-safe cleanup wiring (MANDATORY for manual path)

Register cleanup right after Step 3 path selection, not at the end of the review flow.
Use an `EXIT` trap (or equivalent in non-shell tools) so cleanup runs on success, command failure, or early return.

```bash
cleanup_review_env() {
  case "${SELECTED_PATH:-}" in
    A)
      if [[ -n "${ORIGINAL_BRANCH:-}" ]]; then
        git checkout "$ORIGINAL_BRANCH" >/dev/null 2>&1 || true
        echo "[PATH-CLEANUP] Path A - restored branch to $ORIGINAL_BRANCH"
      else
        echo "[PATH-CLEANUP] Path A - skipped (ORIGINAL_BRANCH unavailable)"
      fi
      ;;
    B)
      if [[ -n "${REPO_PATH:-}" ]] && [[ -d "$REPO_PATH/.git" ]]; then
        cd "$REPO_PATH" || true
        DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD --short 2>/dev/null | sed 's|origin/||')
        git checkout "${DEFAULT_BRANCH:-main}" >/dev/null 2>&1 || true
        git reset --hard "origin/${DEFAULT_BRANCH:-main}" >/dev/null 2>&1 || true
        git clean -fd >/dev/null 2>&1 || true
        echo "[PATH-CLEANUP] Path B - reset cached repo to ${DEFAULT_BRANCH:-main}, ready for next use"
      else
        echo "[PATH-CLEANUP] Path B - skipped (REPO_PATH unavailable)"
      fi
      ;;
    C)
      REMOVED=()
      for d in "${REVIEW_DIR:-}" "${RUN_DIR:-}"; do
        if [[ -n "$d" ]] && [[ -e "$d" ]]; then
          rm -rf "$d" && REMOVED+=("$d") || echo "[PATH-CLEANUP] Path C - failed to delete: $d"
        fi
      done
      if [[ ${#REMOVED[@]} -gt 0 ]]; then
        echo "[PATH-CLEANUP] Path C - deleted temp dirs: ${REMOVED[*]}"
      else
        echo "[PATH-CLEANUP] Path C - no temp dirs to delete"
      fi
      ;;
    *)
      echo "[PATH-CLEANUP] skipped - SELECTED_PATH not set"
      ;;
  esac
}

trap cleanup_review_env EXIT
```

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
- **Path C** (blobless clone): Delete all temp directories created for this review under `mythril-skills-cache/github-code-review-pr/` (including repo/image run dirs such as `"$REVIEW_DIR"` and `"$RUN_DIR"` when present): `rm -rf "<dir>"`

**Path-specific cleanup rule (MANDATORY):**
- If selected path is **C**, cleanup must delete the created temp directories.
- Do NOT replace Path C cleanup with branch reset/clean commands; those are for Path B cached repos.

**User-facing cleanup confirmation is REQUIRED:**
- After deletion, output a short status line that cleanup succeeded and which temp paths were removed (or how many were removed).
- If any temp directory cannot be deleted, explicitly report the remaining path and error, then suggest `skills-clean-cache`.

The cleanup confirmation MUST be produced by an `echo` command inside the shell cleanup script, not written later as prose:

```bash
# Example for Path B:
echo "[PATH-CLEANUP] Path B - reset cached repo to main, ready for next use"

# Example for Path C:
rm -rf "$REVIEW_DIR" "$RUN_DIR"
echo "[PATH-CLEANUP] Path C - deleted temp dirs: $REVIEW_DIR $RUN_DIR"

# Example for Path A:
git checkout "$ORIGINAL_BRANCH"
echo "[PATH-CLEANUP] Path A - restored branch to $ORIGINAL_BRANCH"
```

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
  - **Do NOT include speculative prefaces** such as "this looks like GitLab" or "not a GitHub URL".
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
**Action**: Already in repo (Path A) → `git fetch origin <base> <head>` → `git checkout <headRefName>`, read context locally, review
**Output**: Context-aware review, restore original branch when done

### Example 4: GitHub Enterprise URL (unknown domain)
**User input**: "帮我看一下这个 PR https://git.example.com/owner/repo/pull/123"
**Action**: Domain `git.example.com` does NOT contain 'gitlab', does NOT match 'gitee.com' or 'bitbucket.org' → proceed immediately → run `gh pr view https://git.example.com/...` → if auth error, tell user to run `gh auth login --hostname git.example.com`
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
