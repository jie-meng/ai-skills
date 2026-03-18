---
name: git-repo-reader
description: |
  Clone and read any git repository given a URL (HTTPS or SSH), from any hosting platform
  (GitHub, GitLab, Gitee, Bitbucket, self-hosted, etc.). Caches cloned repos locally so
  follow-up questions in the same or later sessions can reuse them without re-downloading.
  TRIGGER THIS SKILL whenever the user provides a git repository URL and asks to read,
  explore, understand, or analyze the codebase. Trigger phrases include: 'look at this repo',
  'read this repo', 'check this codebase', 'how does this repo implement X', 'what does
  this project do', 'analyze this repository', 'explore this codebase', 'clone and read',
  '看看这个仓库', '读一下这个代码库', '分析一下这个项目', '这个仓库怎么实现的',
  '帮我看看这个 repo'. Also trigger when a message contains a git clone URL
  (https://..., git@...) combined with a question about the code, architecture, or
  implementation. This skill works with ANY git-cloneable URL — not limited to GitHub.
  Use it even when the user just pastes a repo URL and asks a question about it.
license: Apache-2.0
---

# Git Repo Reader

Clone, cache, and read any git repository for code exploration and analysis.

## Requirements

- **`git`** must be installed and available in PATH
- Run `skills-check git-repo-reader` to verify

## When to Use

- User shares a git repo URL (HTTPS or SSH) and asks about the code
- User wants to understand how a project implements something
- User asks to explore, read, or analyze a remote codebase
- The URL can be from **any** git hosting platform — GitHub, GitLab, Gitee, Bitbucket, Azure DevOps, self-hosted, etc.

## How It Works

This skill uses a helper script (`repo_manager.py`) bundled in `scripts/` to handle all repo operations deterministically. The script manages a cache of cloned repos and a mapping file (`repo_map.json`) so repos persist across conversation sessions.

All cached repos live under the unified cache directory:
- **macOS/Linux**: `$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/git-repo-reader/`
- **Windows**: `%TEMP%\mythril-skills-cache\git-repo-reader\`

The user can clean up all cached repos at any time via `skills-clean-cache`.

## Workflow

### Step 1: Parse the repo URL

Accept URLs in any of these formats:
- HTTPS: `https://github.com/owner/repo`, `https://github.com/owner/repo.git`
- SSH: `git@github.com:owner/repo.git`
- Any host: `https://gitlab.com/org/project`, `git@git.example.com:team/service.git`

**Protocol rule**: Unless the user explicitly provides an SSH URL (`git@...`), always convert to HTTPS for cloning. SSH URLs require pre-configured SSH keys, while HTTPS works more broadly (public repos need no auth, private repos prompt for credentials).

### Step 2: Clone or reuse cached repo

Run the helper script to get the repo. The script handles everything: checking the mapping file, reusing existing clones, pulling latest code, or cloning fresh.

```bash
python3 <skill-dir>/scripts/repo_manager.py clone "<repo-url>"
```

The script will:
1. Normalize the URL and compute a deterministic local path
2. Check `repo_map.json` for an existing entry
3. If found and the directory exists → `git pull` to refresh, then return the path
4. If found but directory is missing → remove stale entry, clone fresh
5. If not found → clone the repo, add entry to `repo_map.json`
6. Print the local path to stdout on success

If the user asks for a specific branch:
```bash
python3 <skill-dir>/scripts/repo_manager.py clone "<repo-url>" --branch dev
```

### Step 3: Read and analyze the code

Once you have the local path, explore the codebase freely — read files, search for patterns, understand the architecture. The repo is a normal local git checkout; use all your usual file-reading and search tools.

Start with an overview:
- Read `README.md`, `AGENTS.md`, or other top-level docs
- List the directory structure to understand project layout
- Then dive into the specific files the user asked about

Because the repo is cached locally, follow-up questions in the **same session** can directly access the files at the same path — no need to re-run the script.

For a **new session**, run the script again — it will find the cached repo, pull latest changes, and return the path. This ensures you always work with up-to-date code.

### Step 4: Post-completion notice

After answering the user's question, include a brief note like:

> This repo has been cached locally for reuse. If you want me to clean it up, just let me know.

When the user asks to clean up (e.g., "帮我清理", "clean up the repo", "删掉这个仓库"):
- **Always clean the specific repo** the user was just working with — don't run `skills-clean-cache` (that wipes all skills' caches, not just this repo).
- Use the `remove` command with the repo URL:

```bash
python3 <skill-dir>/scripts/repo_manager.py remove "<repo-url>"
```

This deletes the cloned repo directory and removes its entry from `repo_map.json`, leaving other cached repos untouched.

## Script Reference

The `repo_manager.py` script in `scripts/` supports these subcommands:

| Command | Description |
|---|---|
| `clone <url> [--branch B]` | Clone or reuse a cached repo. Prints the local path. |
| `lookup <url>` | Look up cached path for a URL without cloning. Prints path or exits 1. |
| `remove <url>` | Delete a cached repo and its mapping entry. |
| `list` | List all cached repos (URL → path). |
| `pull <url>` | Pull latest changes for a cached repo. |

All commands print results to stdout and errors to stderr. Exit code 0 means success.

**How URLs are normalized**: The script strips `.git` suffixes, normalizes SSH URLs to a comparable form, and generates a deterministic directory structure: `<cache-root>/repos/<host>/<owner>/<repo>/`. This means `https://github.com/owner/repo`, `https://github.com/owner/repo.git`, and `git@github.com:owner/repo.git` all map to the same local directory.

## Error Handling

- **git not installed**: Print error, suggest `skills-check git-repo-reader`
- **Clone fails** (auth, network, invalid URL): Report the git error. For private repos, suggest the user configure credentials or SSH keys.
- **Pull fails** on existing cache: Try deleting and re-cloning. If that also fails, report the error.
- **Corrupt mapping file**: Recreate it from scratch by scanning existing repo directories.
- **Branch not found**: Report error, suggest checking available branches with `git branch -r`.

## Examples

### Example 1: Explore a public repo (Chinese)
**User**: "帮我看看 https://github.com/example-org/example-project 这个仓库是怎么实现打包功能的"
**Action**: Clone (or reuse cache) → read project structure → find packaging-related code → explain in Chinese

### Example 2: Analyze implementation (English)
**User**: "How does https://github.com/example-org/awesome-tool implement the plugin system?"
**Action**: Clone (or reuse cache) → read plugin-related files → explain the implementation flow

### Example 3: Specific branch
**User**: "看一下 https://git.example.com/team/backend-service 的 dev 分支有什么新功能"
**Action**: Clone with `--branch dev` → explore recent changes → summarize new features

### Example 4: Follow-up question (same session)
**User**: "刚才那个仓库里有没有用到什么测试框架？"
**Action**: Repo is already cached and path is known → directly search for test files → answer

### Example 5: Clean up
**User**: "帮我清理一下刚才下载的仓库"
**Action**: Run `repo_manager.py remove <url>` → delete the specific repo and its mapping entry → confirm to user
