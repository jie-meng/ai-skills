# github-code-review-pr

Context-aware code review for GitHub Pull Requests. Uses a hybrid strategy to gather repository context efficiently.

## How It Works

The key challenge of PR review is that a **diff alone lacks context**. To give a high-quality review, the skill needs to understand the project's structure, coding conventions, and the full content of modified files — not just the changed lines.

This skill uses a **three-path strategy** that adapts to what's available, from fastest to most self-sufficient:

| Path | Condition | Speed | Context depth |
|---|---|---|---|
| **A** | Already inside the target repo | Instant | Full repo |
| **B** | Repo found in shared cache (`git-repo-cache`) | Fast (fetch 2 branches) | Full repo |
| **C** | Repo not cached anywhere | Moderate (partial clone) | Targeted files only |

### Shared Cache Integration

Path B leverages repos cached by the `git-repo-reader` skill (or previous reviews that used Path B). The bundled path selector (`scripts/path_select.py`) checks A/B/C in order, prints explicit `[PATH-CHECK]` / `[PATH-SELECTED]` trace lines, and reads the shared `git-repo-cache` mapping (read-only, never clones). When the cache hits, the skill fetches the two PR branches and checks out by `headRefName`, avoiding any clone operation.

### Review Flow

```mermaid
flowchart TD
    A["User provides PR URL or number"] --> B["Step 1: Parse PR reference"]
    B --> C["Step 2: Fetch PR metadata + diff via gh"]
    C --> C1["gh pr view (metadata)"]
    C --> C2["gh pr diff"]
    C1 --> D["Step 3: Run path_select.py (A/B/C + trace)"]
    C2 --> D

    D -->|"Path A"| E1["git fetch origin base head + git checkout headRefName"]
    D -->|"Path B"| F1["cd REPO_PATH + git fetch origin base head + git checkout headRefName"]

    D -->|"Path C"| G1["Partial clone to temp dir"]
    G1 --> G2["Sparse checkout: root files + PR directories"]
    G2 --> G3["git fetch origin head + git checkout headRefName"]

    E1 --> H["Step 4: Gather context - all local reads"]
    F1 --> H
    G3 --> H

    H --> I["Step 5-6: Analyze and produce structured review"]

    I --> J["Step 7: Clean up"]
    J -->|"Path A"| J1["Restore original branch"]
    J -->|"Path B"| J2["Reset to default branch (keep cache)"]
    J -->|"Path C"| J3["Delete temp directory"]
```

### Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Skill
    participant gh as GitHub CLI
    participant PathSel as path_select.py
    participant Cache as git-repo-cache
    participant Git as Git (local)

    User->>Skill: PR URL / number
    
    par Fetch in parallel
        Skill->>gh: gh pr view --json (metadata)
        gh-->>Skill: title, body, files, commits, reviews
        Skill->>gh: gh pr diff (unified diff)
        gh-->>Skill: diff output
    end

    Note over Skill: Determine repo access strategy
    Skill->>PathSel: path_select.py <repo-url> <current-repo>
    PathSel->>Cache: read repo_map.json
    Cache-->>PathSel: cache hit / miss
    PathSel-->>Skill: PATH-CHECK lines + SELECTED_PATH/REPO_PATH

    alt Path A
        Skill->>Git: git fetch origin base head
        Skill->>Git: git checkout <headRefName>
        Git-->>Skill: Switched to PR branch
    else Path B
        Skill->>Git: cd REPO_PATH
        Skill->>Git: git fetch origin base head
        Skill->>Git: git checkout <headRefName>
        Git-->>Skill: Switched to PR branch
    else Path C
        Skill->>gh: gh repo clone (partial, sparse)
        gh-->>Git: Partial clone in temp dir
        Skill->>Git: sparse-checkout set / + PR directories
        Skill->>Git: git fetch origin head
        Skill->>Git: git checkout <headRefName>
        Git-->>Skill: Switched to PR branch
    end

    Note over Skill,Git: All further reads are local

    Skill->>Git: git ls-tree (project structure)
    Git-->>Skill: Full file tree

    Skill->>Git: Read convention files, modified files, related files
    Git-->>Skill: File contents

    Skill->>User: Structured 6-section review
```

## Why This Hybrid Strategy?

| Method | Download size (50K-file repo) | Reusable? | When used |
|--------|------------------------------|-----------|-----------|
| Path A — already in repo | 0 (just fetch) | N/A | Working in the repo |
| Path B — shared cache hit | ~KB (fetch 2 branches) | Yes | Repo was cloned by git-repo-reader or previous review |
| Path C — partial clone | ~5-50 MB (metadata + sparse files) | No (deleted after) | First encounter with the repo |
| Full clone (not used) | ~2 GB | Yes | Too slow for review |

Path B is the sweet spot for repos you work with regularly — near-instant after the first `git-repo-reader` clone. Path C is the safe fallback that works for any repo without waiting for a full clone.

## Context Gathering Strategy

### With full repo (Path A / Path B)

1. **Project structure** via `git ls-tree` — full file tree, no network needed
2. **Convention files** — read root-level config files directly
3. **Modified files** — read full content, git auto-fetches blobs on demand
4. **Related files** — read any file in the repo, auto-fetched transparently

### With partial clone (Path C)

1. **Project structure** via `git ls-tree` — full file tree from cached tree objects
2. **Convention files** — checked out via `sparse-checkout set /` (root-level)
3. **Modified files** — checked out via sparse-checkout of their directories
4. **Related files** — add directories to sparse checkout as needed (2-3 max)

## Path C Step-by-Step (Blobless + Sparse)

Path C is the fallback when the repo is not available locally and not found in shared cache. It is designed to stay lightweight while still enabling context-aware review.

1. **Fetch PR metadata and diff once (no pager)**
   - Use the PR URL as the canonical reference.
   - Disable interactive paging so automation does not block.

```bash
GH_PAGER=cat gh pr view "<PR_URL>" --json number,title,body,baseRefName,headRefName,files,changedFiles,additions,deletions,url
GH_PAGER=cat gh pr diff "<PR_URL>"
```

2. **Create a temp review directory under the unified cache**

```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/github-code-review-pr"
mkdir -p "$CACHE_DIR"
REVIEW_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
```

3. **Clone with blobless + sparse mode (not full clone)**
   - `--filter=blob:none`: skip file blobs during clone.
   - `--sparse`: start with a minimal working tree.

```bash
gh repo clone "<REPO_URL_OR_OWNER/REPO>" "$REVIEW_DIR" -- --filter=blob:none --sparse
cd "$REVIEW_DIR"
```

4. **Add only directories touched by the PR**
   - Extract parent directories from the `files` list returned by `gh pr view`.
   - Add only those directories to sparse checkout.

```bash
git sparse-checkout add src/moduleA deploy .github/workflows
```

5. **Checkout the PR branch after sparse scope is set**

```bash
git fetch origin <headRefName>
git checkout <headRefName>
```

6. **Read context incrementally**
   - Read modified files in full when change volume justifies it.
   - If a dependency/reference points outside current sparse scope, add one more directory and continue.

```bash
git sparse-checkout add src/shared src/types
```

7. **Clean up temp repo after review**

```bash
rm -rf "$REVIEW_DIR"
```

### Why this is efficient

- Initial clone transfers commit/tree metadata, not full file content.
- File content is fetched only when directories are added to sparse checkout.
- Review stays focused on changed areas plus minimal related context.
- This avoids the cost of a full clone while preserving review quality.

### Operational best practices for Path C

- Use one canonical PR reference per run (URL if user provided URL).
- Disable pager for all `gh` review commands (`GH_PAGER=cat`).
- Fetch metadata/diff once, then reuse; avoid repeated `gh pr diff` calls.
- In the final report, clearly separate confirmed findings from potential risks.

## Path C Visual Map (What gets downloaded, when)

```mermaid
flowchart TD
    S0["Input: PR URL"] --> S1["1) GH_PAGER=cat gh pr view + gh pr diff"]
    S1 --> D1["Downloads: PR metadata + patch text\n(no repo clone yet)"]
    D1 --> A1["Analyzable now:\n- PR title/body/commits/reviews\n- changed file list\n- unified diff"]

    A1 --> S2["2) gh repo clone --filter=blob:none --sparse"]
    S2 --> D2["Downloads: commits + trees + refs\n(no full file blobs)"]
    D2 --> A2["Analyzable now:\n- full repo tree via git ls-tree\n- root files in sparse checkout"]

    A2 --> S3["3) git sparse-checkout add <PR dirs>"]
    S3 --> D3["Downloads: blobs only for PR-touched directories"]
    D3 --> A3["Analyzable now:\n- full content of modified files\n- directory-local context"]

    A3 --> S4["4) git fetch origin <headRefName> + git checkout <headRefName>"]
    S4 --> D4["Downloads: head branch refs\n+ blobs for sparse paths as needed"]
    D4 --> A4["Analyzable now:\n- PR branch version of sparse files"]

    A4 --> S5["5) git sparse-checkout add <related dirs> (optional)"]
    S5 --> D5["Downloads: additional blobs for only those related dirs"]
    D5 --> A5["Analyzable now:\n- cross-file interfaces/callers/tests\n  required for correctness checks"]
```

### Step-to-Command Matrix

| Step | Command | Network download at this step | Files analyzed after this step |
|---|---|---|---|
| 1 | `GH_PAGER=cat gh pr view ...` + `GH_PAGER=cat gh pr diff ...` | PR metadata and diff text | PR intent, changed files, patch hunks |
| 2 | `gh repo clone ... --filter=blob:none --sparse` | Commit graph, tree objects, refs (no full blobs) | Repo structure, root convention files |
| 3 | `git sparse-checkout add <pr-dirs>` | Blobs for changed directories only | Full content of modified files |
| 4 | `git fetch origin <headRefName>` + `git checkout <headRefName>` | Head branch refs and sparse-path blobs as needed | PR branch version of sparse files |
| 5 | `git sparse-checkout add <related-dirs>` | Blobs for specifically added related dirs | Interfaces/callers/tests needed for validation |
| 6 | `rm -rf "$REVIEW_DIR"` | None | Cleanup only |

## Ensuring Branch Freshness

A critical concern with cached repos (Path B) is stale branches leading to inaccurate reviews:

1. **Targeted branch fetch** — `git fetch origin <baseRefName> <headRefName>` fetches exactly the two branches the PR needs
2. **Remote-tracking refs for comparison** — always uses `origin/<baseRefName>` (not local branches) as the diff base
3. **Direct branch checkout** — `git checkout <headRefName>` uses metadata from `gh pr view` and avoids `gh pr checkout` auth edge cases on Enterprise hosts

## Requirements

- **GitHub CLI (`gh`)** — installed and authenticated
- **Git 2.25+** — for sparse-checkout support (most systems have this)
- **`curl`** — for downloading PR screenshots/assets when visual evidence matters
- Run `skills-check github-code-review-pr` to verify

## Visual Evidence Handling (Screenshots/Images)

When PR body/comments/reviews include image links, the skill should proactively download and inspect them when:
- the user asks to interpret screenshots,
- screenshots are part of verification steps (UI proof, tracking proof, offline check), or
- image content is necessary to validate correctness/risk.

Store image files under a random run dir in `~/Library/Caches/mythril-skills-cache/github-code-review-pr/` (Linux: `${XDG_CACHE_HOME:-~/.cache}/mythril-skills-cache/github-code-review-pr/`).

Do not store artifacts in ad-hoc paths like `/tmp/pr81_deskcheck/...`.
Then summarize what each image shows and whether it supports PR claims.

## Cleaning Up

| Type | Location | Lifecycle |
|---|---|---|
| **Shared repo cache** | `mythril-skills-cache/git-repo-cache/` | Long-lived, managed by `git-repo-reader` |
| **Temp clones (Path C)** | `mythril-skills-cache/github-code-review-pr/` | Deleted after each review |
| **Image artifacts** | `mythril-skills-cache/github-code-review-pr/` | Ephemeral, per-review |

```bash
skills-clean-cache          # interactive — lists cache contents, asks for confirmation
skills-clean-cache --force  # delete without asking
```

## Usage Examples

```
"Review this PR: https://github.com/owner/repo/pull/42"
"帮我审查一下这个 PR https://github.com/owner/repo/pull/42"
"帮我看一下这个 PR https://git.company.com/org/repo/pull/456"
"PR review #15"
"review PR owner/repo#99"
```
