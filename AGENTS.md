# AGENTS.md — Development Guidelines for ai-skills Repository

## Project Overview

**ai-skills** is a repository of reusable skills for AI coding assistants (Github Copilot, Claude Code, Cursor, Codex, Gemini CLI, Qwen CLI, iFlow CLI, Opencode). Each skill is a self-contained directory with a `SKILL.md` that defines its metadata, triggering description, and instructions.

Tech Stack:
- **Primary Language**: Python 3.10+
- **Configuration**: YAML (frontmatter in SKILL.md)
- **Documentation**: Markdown
- **Script Language**: Bash (setup/deployment)

---

## Setup Script

`./scripts/setup-skills` syncs all skills from `./skills/` to your AI assistant's user-level configuration directory.

### Interactive menu (no arguments)

```bash
./scripts/setup-skills
```

Displays a numbered menu of supported tools. Enter a number to install, or `0` for all. When installing all, tools whose config directory (`~/.claude`, `~/.cursor`, etc.) does not exist are skipped with a warning.

### Direct target

```bash
./scripts/setup-skills .copilot   # Github Copilot
./scripts/setup-skills .claude    # Claude Code
./scripts/setup-skills .cursor    # Cursor
```

Copies all skill directories into `~/<target-dir>/skills/`, creating it if needed, and reports which skills were added or updated.

### Supported tools

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

---

## Skill File Structure

Each skill is a directory under `skills/`:

```
skills/skill-name/
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
---

# Skill Name

Detailed instructions, examples, and workflows...
```

**Required fields**:
- `name`: Skill identifier (matches directory name)
- `description`: When and why to trigger — this is the AI's activation signal. Be precise and "pushy": list specific contexts, keywords, and phrases.

**Optional fields**:
- `allowed-tools`: List of tools the skill may use
- `compatibility`: Tool/platform requirements

**Tips for a good description**:
- State explicitly *when* to invoke the skill (trigger conditions)
- List example user phrases that should activate it
- Mention what the skill does, not just what it is
- Avoid vague descriptions — specificity improves triggering accuracy

---

## Validation

Validate a skill's SKILL.md structure before committing:

```bash
python3 skills/skill-creator/scripts/quick_validate.py <skill-path>
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

### ✅ DO:
- Validate input early, raise informative errors
- Use `pathlib.Path` for all file operations
- Write type hints on all functions
- Check file existence before reading: `if not path.exists():`
- Use context managers: `with open(...) as f:`

### ❌ DON'T:
- Use bare `except:` or silently swallow exceptions
- Hardcode absolute paths — use relative paths or CLI args
- Mix string paths and Path objects in the same function
- Delete or modify eval/test files to force passing validation

