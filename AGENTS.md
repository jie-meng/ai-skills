# AGENTS.md — Development Guidelines for mythril-agent-skills Repository

## Project Overview

**mythril-agent-skills** is a pip-installable package of reusable skills for AI coding assistants (Github Copilot, Claude Code, Cursor, Codex, Gemini CLI, Qwen CLI, Opencode, Grok CLI). Each skill is a self-contained directory with a `SKILL.md` that defines its metadata, triggering description, and instructions.

Tech Stack:
- **Primary Language**: Python 3.10+
- **Package Format**: `pyproject.toml` (setuptools)
- **Configuration**: YAML (frontmatter in SKILL.md)
- **Documentation**: Markdown
- **CLI**: Python (curses-based interactive installer and cleanup tool)

---

## Package Structure

```
mythril-agent-skills/
├── mythril_agent_skills/        # Python package
│   ├── __init__.py
│   ├── cli/                     # CLI entry points
│   │   ├── skills_setup.py      # Interactive installer
│   │   ├── skills_cleanup.py    # Interactive remover
│   │   └── skills_check.py      # Dependency checker & configurator
│   └── skills/                  # Bundled skill definitions
├── scripts/                     # Backward-compatible wrappers (for dev use)
│   ├── sync-upstream.py         # Fork upstream sync tool
│   └── init-fork.py             # One-time fork initializer (detach + git re-init)
├── .sync-upstream.json           # Upstream sync config (for forks)
├── pyproject.toml               # Package configuration
└── ...
```

## CLI Commands

Installed via `pip install mythril-agent-skills` (or `pip install -e .` for development):

| Command | Entry point | Description |
|---|---|---|
| `skills-setup` | `mythril_agent_skills.cli.skills_setup:main` | Interactive installer |
| `skills-cleanup` | `mythril_agent_skills.cli.skills_cleanup:main` | Interactive remover |
| `skills-check` | `mythril_agent_skills.cli.skills_check:main` | Dependency checker |
| `skills-clean-cache` | `mythril_agent_skills.cli.skills_clean_cache:main` | Cache directory cleaner |

All CLI scripts use Python `curses` for interactive multi-select UIs. They support macOS, Linux, and Windows (auto-install `windows-curses` on Windows if needed).

### Setup: `skills-setup`

Syncs selected skills from the installed package to your AI assistant's user-level configuration directory.

```bash
skills-setup              # Interactive: select tools, then skills
skills-setup .cursor      # Direct target: skip tool selection
```

Interactive mode launches two multi-select screens:
1. **Select AI tools** — choose which tools to install skills to
2. **Select skills** — choose which skills to install

Controls: Up/Down move, Space toggle, `a` all/none, Enter confirm, `q` quit.

### Cleanup: `skills-cleanup`

Scans AI tool config directories for installed skills and lets you selectively remove them.

```bash
skills-cleanup
```

Launches two screens:
1. **Select AI tools** — choose which tool directories to scan (defaults to all detected)
2. **Select skills to remove** — tree view showing each tool and its installed skills (defaults to none selected)

### Check: `skills-check`

Checks and configures external dependencies (CLI tools, API tokens) for selected skills.

```bash
skills-check gh-operations jira figma
```

Features:
- Auto-installs missing CLI tools (e.g. `gh`) with user confirmation
- Prompts for missing API keys and saves them to the shell config file
- Verifies authentication status

### Clean Cache: `skills-clean-cache`

Removes cached files created by skills at runtime. The cache contains two categories: **temp files** (images, exports — ephemeral) and **repo cache** (shared git clones — long-lived, reusable). The interactive mode lets users choose to clean one or both categories.

```bash
skills-clean-cache          # Interactive: list cache contents, choose what to delete
skills-clean-cache --force  # Delete everything without confirmation
skills-clean-cache --show-repos  # Optional: include cached repo names and sizes
```

### Backward-compatible wrappers

The `scripts/` directory contains thin wrappers for running without `pip install`:

```bash
python3 scripts/skills-setup.py
python3 scripts/skills-cleanup.py
python3 scripts/skills-check.py gh-operations jira figma
python3 scripts/skills-clean-cache.py
```

### Fork upstream sync

For users who fork this repository to maintain private skills, a sync script keeps the fork up to date with upstream:

```bash
python3 scripts/sync-upstream.py              # Interactive sync
python3 scripts/sync-upstream.py --dry-run     # Preview only
python3 scripts/sync-upstream.py --force        # No confirmation
```

Configuration is in `.sync-upstream.json` (repo root). The `exclude_skills` list prevents specific skills from being overwritten during sync. See [docs/FORK-SYNC.md](./docs/FORK-SYNC.md) for details.

### Supported tools

All config directories are relative to the user home directory (`~` on macOS/Linux, `%USERPROFILE%` on Windows).

| # | Tool | Config directory | Skills path |
|---|---|---|---|
| 1 | Copilot CLI / VS Code | `~/.copilot/` | `~/.copilot/skills/` |
| 2 | Claude Code | `~/.claude/` | `~/.claude/skills/` |
| 3 | Cursor | `~/.cursor/` | `~/.cursor/skills/` |
| 4 | Codex | `~/.codex/` | `~/.codex/skills/` |
| 5 | Gemini CLI | `~/.gemini/` | `~/.gemini/skills/` |
| 6 | Qwen CLI | `~/.qwen/` | `~/.qwen/skills/` |
| 7 | Opencode | `~/.config/opencode/` | `~/.config/opencode/skills/` |
| 8 | Grok CLI | `~/.grok/` | `~/.grok/skills/` |

---

## Skill File Structure

Each skill is a directory under `mythril_agent_skills/skills/`:

```
mythril_agent_skills/skills/skill-name/
├── SKILL.md              # Required: metadata + instructions
├── README.md             # Optional: overview for humans
├── scripts/              # Optional: helper Python/Bash scripts
├── references/           # Optional: documentation, guides, schemas
├── agents/               # Optional: prompt/instruction files for evaluations
└── assets/               # Optional: templates, icons, HTML/CSS resources
```

### Writing a High-Quality SKILL.md

`SKILL.md` must begin with YAML frontmatter:

```yaml
---
name: skill-name
description: |
  Multi-line description explaining when to use this skill.
  Include trigger keywords and use cases.
  Be specific — mention concrete contexts and phrases that should activate the skill.
license: Apache-2.0
---

# Skill Name

Detailed instructions, examples, and workflows...
```

**Required fields**:
- `name`: Skill identifier (matches directory name)
- `description`: When and why to trigger — this is the AI's activation signal. Be precise and "pushy": list specific contexts, keywords, and phrases.

**Optional fields**:
- `license`: Skill license (e.g., `Apache-2.0`, `MIT`). Defaults to Apache-2.0 if not specified.
- `allowed-tools`: List of tools the skill may use
- `compatibility`: Tool/platform requirements

**Character limit**:
- **The `description` field MUST be at most 1024 characters.** Multiple AI tools enforce this limit at load time — skills with longer descriptions will fail to load silently. Always verify length after editing a description. You can check all skills at once:
  ```bash
  python3 -c "
  import yaml, pathlib
  for p in sorted(pathlib.Path('mythril_agent_skills/skills').glob('*/SKILL.md')):
      fm = yaml.safe_load(p.read_text().split('---', 2)[1])
      d = fm.get('description', ''); n = len(d)
      print(f\"{'!!' if n > 1024 else '  '} {p.parent.name}: {n} chars\")
  "
  ```

**Tips for a good description**:
- State explicitly *when* to invoke the skill (trigger conditions)
- List example user phrases that should activate it
- Mention what the skill does, not just what it is
- Avoid vague descriptions — specificity improves triggering accuracy

### Security Rules for Skills Using API Tokens or Credentials

Skills that require API tokens, passwords, or other credentials (e.g. `ATLASSIAN_API_TOKEN`, `FIGMA_ACCESS_TOKEN`, `GH_TOKEN`) MUST include a **"Security — MANDATORY rules for AI agents"** section in their `SKILL.md` with these rules:

1. **NEVER echo, print, or log** the value of any environment variable — even for debugging. Commands like `echo $TOKEN`, `printenv TOKEN`, `env | grep TOKEN` are strictly forbidden.
2. **NEVER pass credential values as inline CLI arguments or env-var overrides** (e.g. `TOKEN=xxx python3 script.py`). Scripts MUST read credentials from the environment internally via `os.environ`. The AI agent simply runs the script — no manual credential handling.
3. **NEVER read environment variable values** using shell commands or programmatic access. The AI agent should not inspect, verify, or access token values in any way.
4. **When debugging auth errors**, rely solely on the script's error messages (401, 403, etc.). Do NOT attempt to verify tokens by reading or printing them.

These rules prevent accidental credential exposure in terminal output, chat logs, and conversation transcripts.

**For `skills_check.py`**: Token values MUST be masked (show only last 4 chars). Email addresses MUST be partially masked (e.g. `j***@example.com`). Base URLs may be shown in full.

### Skill Ordering Convention

Skills appear in multiple listings: the README "Available Skills" table, the `skills-check` interactive UI and execution order, and the `CHECKABLE_SKILLS` list in code. All MUST follow the same ordering convention.

**Category order** (groups, top to bottom):

| # | Category | Description | Example skills |
|---|---|---|---|
| 1 | **Meta** | Tools for creating/managing skills themselves | skill-creator |
| 2 | **Code Review** | Code review workflows (local and remote) | code-review-staged, branch-diff-review, github-code-review-pr |
| 3 | **Git & GitHub** | Git operations and GitHub platform integration | git-repo-reader, gh-operations |
| 4 | **API Integrations** | Third-party API clients requiring credentials | jira, confluence, figma |
| 5 | **Media Processing** | Standalone CLI tools for media files | imagemagick, ffmpeg |

**Within each category**, order by dependency complexity — no deps first, then CLI deps, then API credential deps:
- No external dependencies → CLI tool dependency (`git`) → Platform CLI dependency (`gh`) → API token dependency

**For `skills-check`**: The execution order follows a different principle — **dependency layers** (check foundational tools before things that depend on them):
1. Foundation CLI (`git`) — almost everything depends on it
2. Platform CLI (`gh`) — builds on git
3. API credentials (Atlassian, Figma) — need tokens configured
4. Standalone media tools (ImageMagick, FFmpeg) — independent binaries

When adding a new skill, place it in the appropriate category. If it doesn't fit any existing category, add a new category row and insert it at a logical position in the table.

---

## Temporary Files & Cache Convention

See [docs/CACHE.md](./docs/CACHE.md) for the full cache usage guide and examples.

Skills that need to download files, clone repos, or create temp artifacts at runtime MUST use the unified per-user cache directory:

```
<user-cache-root>/mythril-skills-cache/<skill-name>/
```

### Shared git repo cache

The `git-repo-reader` skill manages a shared repo cache at `mythril-skills-cache/git-repo-cache/` via its `scripts/repo_manager.py`. Other skills (e.g., `github-code-review-pr`) can **read** this cache to reuse already-cloned repos without re-downloading.

```bash
# git-repo-reader: clone or reuse a cached repo
python3 scripts/repo_manager.py clone "<repo-url>"

# github-code-review-pr: check if repo is already cached (read-only lookup)
python3 scripts/repo_cache_lookup.py "<repo-url>"
```

Cached repos live under `mythril-skills-cache/git-repo-cache/repos/<host>/<owner>/<repo>/`. They are **long-lived** — do NOT delete them after use. The `skills-clean-cache` command lets users selectively clean repo cache vs ephemeral temp files.

**Design principle**: Only `git-repo-reader` writes to the shared cache (clone, pull, sync). Other skills that benefit from cached repos bundle a lightweight **read-only lookup script** (`repo_cache_lookup.py`) that checks the same mapping file. This keeps each skill self-contained while enabling cross-skill cache reuse.

### Cross-platform cache directory creation

Skills run on macOS, Linux, and Windows. Use the appropriate syntax for the user's platform.

**IMPORTANT**: Do NOT use temp roots such as `$TMPDIR`, `/tmp`, or `%TEMP%` for skill cache. Different tools may set different temp environments, causing non-unique cache paths. Always use per-user OS cache roots below.

**Bash (macOS / Linux):**
```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/<skill-name>"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
```

**PowerShell (Windows):**
```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "<skill-name>"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$RUN_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $RUN_DIR | Out-Null
```

**Python:**
```python
from pathlib import Path
import os
import platform

home = Path.home()
if platform.system() == "Darwin":
    cache_root = home / "Library" / "Caches" / "mythril-skills-cache"
elif platform.system() == "Windows":
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
    cache_root = base / "mythril-skills-cache"
else:
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache_home) if xdg_cache_home else home / ".cache"
    cache_root = base / "mythril-skills-cache"

cache_dir = cache_root / "<skill-name>"
cache_dir.mkdir(parents=True, exist_ok=True)
```

All approaches resolve to one **stable per-user** location per platform:
- **macOS**: `/Users/<user>/Library/Caches/mythril-skills-cache/...`
- **Linux**: `/home/<user>/.cache/mythril-skills-cache/...` (or `$XDG_CACHE_HOME/mythril-skills-cache/...`)
- **Windows**: `C:\Users\<user>\AppData\Local\mythril-skills-cache\...`

### Cache directory rules

- **Each skill gets its own subdirectory** named after the skill (e.g., `github-code-review-pr/`, `figma/`)
- **Git repo clones go into the shared `git-repo-cache/`** subdirectory, managed by `git-repo-reader`'s `repo_manager.py`.
- **Within the subdirectory, create random dirs freely** — e.g., `mktemp -d "$CACHE_DIR/XXXXXXXX"`
- **Default rule for ALL downloads**: if the user did not explicitly provide a destination path, save into the unified cache path above (never ad-hoc locations)
- **If user explicitly provides a destination path**, follow it; otherwise always use the unified cache path
- **Skills do NOT need to worry about cleanup** — the `skills-clean-cache` command handles it
- **Never create temp files directly in `/tmp/`** or other ad-hoc locations

### Automatic access to cache files

Files under the unified cache directory are **skill-managed temporary artifacts** (downloaded images, cloned repos, exported assets). The AI agent MUST read, write, and delete these files **automatically without asking the user for confirmation**. These files were created by the skill itself during the current or a previous session — they are inherently trusted and ephemeral. This applies regardless of whether the cache path falls inside or outside the current workspace directory.

This convention ensures `skills-clean-cache` can find and remove all skill-generated temp data in one pass.

---

## Validation

Validate a skill's SKILL.md structure before committing:

```bash
python3 mythril_agent_skills/skills/skill-creator/scripts/quick_validate.py <skill-path>
```

---

## Code Style Guidelines

### Python

- **File naming**: `snake_case`: `run_eval.py`, `utils.py`
- **Shebang + docstring** on all scripts: `#!/usr/bin/env python3`
- **Imports**: stdlib → third-party → local
- **Type hints**: required on all function signatures
  - Use `dict[str, str]`, `list[str]`, `str | None` (Python 3.10+)
- **Docstrings**: concise triple-quote on all public functions
- **Error handling**: raise informative errors with context; no bare `except:`
- **Paths**: use `pathlib.Path`, not `os.path` or raw strings
- **Line length**: 88 chars (Black standard)

```python
def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
    if not (skill_path / "SKILL.md").exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_path}")
```

### Bash

- Shebang `#!/bin/bash` and comment header
- `UPPER_CASE` constants, `lower_case` variables
- Always quote variables: `"$VAR"`
- Explicit error checks or `set -e`

### Markdown

- Start at H1, don't skip heading levels
- Fenced code blocks with language tags
- Relative links for internal references
- Keep `README.md` content in English only

---

## Naming Conventions

- **Skill directories**: lowercase, hyphenated: `skill-creator`, `code-review-staged`
- **Scripts**: lowercase, descriptive: `run_eval.py`, `quick_validate.py`
- **Output directories**: `outputs/` under skill root

---

## Git Commit Guidelines

- **Format**: `[skill-name] Brief description` or `[scripts] Brief description`
- Keep commits atomic: one logical change per commit
- Never commit `.claude/`, `.copilot/`, or local build artifacts

---

## Common Patterns & Anti-Patterns

### DO:
- Validate input early, raise informative errors
- Use `pathlib.Path` for all file operations
- Write type hints on all functions
- Check file existence before reading: `if not path.exists():`
- Use context managers: `with open(...) as f:`

### DON'T:
- Use bare `except:` or silently swallow exceptions
- Hardcode absolute paths — use relative paths or CLI args
- Mix string paths and Path objects in the same function
- Delete or modify eval/test files to force passing validation
