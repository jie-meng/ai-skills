# AGENTS.md — Development Guidelines for mythril-agent-skills Repository

## Project Overview

**mythril-agent-skills** is a pip-installable package of reusable skills for AI coding assistants (Github Copilot, Claude Code, Cursor, Codex, Gemini CLI, Qwen CLI, iFlow CLI, Opencode, Grok CLI). Each skill is a self-contained directory with a `SKILL.md` that defines its metadata, triggering description, and instructions.

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

Removes temporary files created by skills at runtime (git clones for PR review, exported images, etc.). All skills store temp files under a unified cache directory: `${TMPDIR:-/tmp}/mythril-skills-cache/`.

```bash
skills-clean-cache          # Interactive: list cache contents, confirm before deleting
skills-clean-cache --force  # Delete without confirmation
```

### Backward-compatible wrappers

The `scripts/` directory contains thin wrappers for running without `pip install`:

```bash
python3 scripts/skills-setup.py
python3 scripts/skills-cleanup.py
python3 scripts/skills-check.py gh-operations jira figma
python3 scripts/skills-clean-cache.py
```

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
| 7 | iFlow CLI | `~/.iflow/` | `~/.iflow/skills/` |
| 8 | Opencode | `~/.config/opencode/` | `~/.config/opencode/skills/` |
| 9 | Grok CLI | `~/.grok/` | `~/.grok/skills/` |

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

**Tips for a good description**:
- State explicitly *when* to invoke the skill (trigger conditions)
- List example user phrases that should activate it
- Mention what the skill does, not just what it is
- Avoid vague descriptions — specificity improves triggering accuracy

---

## Temporary Files & Cache Convention

Skills that need to download files, clone repos, or create temp artifacts at runtime MUST use the unified cache directory:

```
${TMPDIR:-/tmp}/mythril-skills-cache/<skill-name>/
```

- **Each skill gets its own subdirectory** named after the skill (e.g., `github-code-review-pr/`, `figma/`)
- **Within the subdirectory, create random dirs freely** — e.g., `mktemp -d "${TMPDIR:-/tmp}/mythril-skills-cache/github-code-review-pr/XXXXXXXX"`
- **Skills do NOT need to worry about cleanup** — the `skills-clean-cache` command handles it
- **Never create temp files directly in `/tmp/`** or other ad-hoc locations

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
