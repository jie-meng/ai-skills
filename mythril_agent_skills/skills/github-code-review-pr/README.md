# github-code-review-pr

Context-aware code review for GitHub Pull Requests. Uses partial clone and sparse checkout to gather deep repository context without downloading the entire repo.

## How It Works

The key challenge of PR review is that a **diff alone lacks context**. To give a high-quality review, the skill needs to understand the project's structure, coding conventions, and the full content of modified files — not just the changed lines.

Naive approaches either download the entire repo (slow for large repos) or make dozens of GitHub API calls to fetch files one by one (slow due to network round-trips). This skill uses **git partial clone + sparse checkout** to download only what's needed.

### Review Flow

```mermaid
flowchart TD
    A["User provides PR URL or number"] --> B["Step 1: Parse PR reference"]
    B --> C["Step 2: Fetch PR metadata + diff via gh"]
    C --> C1["gh pr view (metadata)"]
    C --> C2["gh pr diff"]
    C1 --> D{"Step 3: Already inside the target repo?"}
    C2 --> D

    D -->|"Yes - Path A"| E1["gh pr checkout"]
    D -->|"No - Path B"| E2["Partial clone to temp dir"]

    E2 --> F1["gh repo clone (partial, sparse)"]
    F1 --> F2["Sparse checkout: root files + PR directories"]
    F2 --> F3["gh pr checkout"]

    E1 --> G["Step 4: Gather context - all local reads"]
    F3 --> G

    G --> G1["Project structure via git ls-tree"]
    G --> G2["Convention files: AGENTS.md, CLAUDE.md, etc."]
    G --> G3["Full content of modified files"]
    G --> G4["Related files referenced in diff"]

    G1 --> H["Step 5-6: Analyze and produce structured review"]
    G2 --> H
    G3 --> H
    G4 --> H

    H --> I["Step 7: Clean up"]
    I -->|"Path A"| I1["Restore original branch"]
    I -->|"Path B"| I2["Delete temp directory"]
```

### Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Skill
    participant gh as GitHub CLI
    participant Git as Git (local)

    User->>Skill: PR URL / number
    
    par Fetch in parallel
        Skill->>gh: gh pr view --json (metadata)
        gh-->>Skill: title, body, files, commits, reviews
        Skill->>gh: gh pr diff (unified diff)
        gh-->>Skill: diff output
    end

    Note over Skill: Determine repo access strategy

    alt Already in target repo
        Skill->>Git: gh pr checkout <number>
        Git-->>Skill: Switched to PR branch
    else Not in target repo
        Skill->>gh: gh repo clone --filter=blob:none --sparse
        Note over gh,Git: Downloads only metadata (~MB)<br/>No file blobs yet
        gh-->>Git: Partial clone in temp dir
        Skill->>Git: sparse-checkout set / + PR directories
        Note over Git: Downloads only needed blobs
        Skill->>Git: gh pr checkout <number>
        Git-->>Skill: Switched to PR branch
    end

    Note over Skill,Git: All further reads are local

    Skill->>Git: git ls-tree (project structure)
    Note over Git: Uses cached tree objects<br/>No network needed
    Git-->>Skill: Full file tree

    Skill->>Git: Read convention files (AGENTS.md, etc.)
    Git-->>Skill: File contents

    Skill->>Git: Read modified files (full content)
    Git-->>Skill: File contents

    Skill->>Git: Read related files (if needed)
    Note over Git: Auto-fetches blob on demand<br/>if not yet checked out
    Git-->>Skill: File contents

    Skill->>User: Structured 6-section review
```

## Why Partial Clone + Sparse Checkout?

The problem: you need repo context, but you don't want to download a 2 GB monorepo just to review a 10-file PR.

| Method | What gets downloaded | Typical size (50K-file repo) | Network round-trips |
|--------|---------------------|------------------------------|---------------------|
| Full clone | All commits + all blobs | ~2 GB | 1 |
| `--depth=1` (shallow) | 1 commit, but **all** blobs | ~500 MB | 1 |
| `--filter=blob:none --sparse` | Commits + trees only, blobs on demand | ~5-50 MB | 1 + on-demand |
| Per-file `gh api` calls | Only requested files | ~same bytes | 10-20 HTTP requests |

Partial clone wins because:

1. **Initial clone is tiny** — only git metadata (tree objects), no file content
2. **`git ls-tree` works immediately** — you can see the full project structure without downloading a single file
3. **Sparse checkout pulls only what you ask for** — root config files + directories of changed files
4. **On-demand blob fetch** — if you need a file you didn't sparse-checkout, git fetches just that one blob automatically
5. **One network operation** instead of N API calls — fewer round-trips, faster overall

## Context Gathering Strategy

The skill gathers context at three levels:

### 1. Project-level context (cheap, always gathered)

- **File tree** via `git ls-tree` — understand module layout and naming conventions
- **Convention files** — `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CONTRIBUTING.md`, `pyproject.toml`, `package.json`, `.editorconfig`, etc.
- These are all root-level files, checked out by default with `sparse-checkout set /`

### 2. Change-level context (selective)

- **Full file content** of modified files — not just the diff, but the complete file on the PR branch
- This lets the reviewer see the function a change sits inside, the class structure, nearby code patterns
- Sparse checkout targets only the directories containing changed files

### 3. Reference-level context (on-demand)

- If the diff imports from or calls into files not in the PR, those are fetched on demand
- Git's partial clone handles this transparently — just read the file and git fetches the blob
- Limited to 2-3 files to avoid scope creep

## Requirements

- **GitHub CLI (`gh`)** — installed and authenticated
- **Git 2.25+** — for sparse-checkout support (most systems have this)
- Run `skills-check github-code-review-pr` to verify

## Cleaning Up Temp Directories

PR reviews that use Path B (partial clone) create temporary directories under `${TMPDIR}/mythril-skills-cache/github-code-review-pr/`. These are normally cleaned up after each review, but interrupted sessions may leave them behind. Use the shared cache cleaner:

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
