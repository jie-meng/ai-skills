# mythril-agent-skills

A unified skill management system for multi-agent AI coding assistants. This package provides a curated collection of reusable skills plus a centralized CLI toolkit to install, configure, and maintain them across Github Copilot, Claude Code, Cursor, Codex, Gemini CLI ...

## What is a Skill?

A skill is a prompt/instruction bundle that teaches an AI assistant how to handle a specific type of task. Think of it like a specialized tool: it has a name, a triggering description, and detailed instructions.

**Example**: The `code-review-staged` skill teaches Claude Code to review Git staged changes with a structured 6-section code review format. When you ask "review staged", Claude automatically loads this skill and executes its workflow.

## Available Skills

| Skill | Description | Use When |
|---|---|---|
| [Skill Creator](./mythril_agent_skills/skills/skill-creator/) | Create skills/prompts for any AI platform. Includes drafting, test case generation, evaluation, benchmarking, description optimization. | Create a new skill, improve triggering, or benchmark skill performance |
| [Jira](./mythril_agent_skills/skills/jira/) | Use Jira REST API (via bundled Python script) for issue, sprint, and board workflows. No CLI tools needed. | "jira issue", "jira card", "PROJ-123", or sprint/board requests |
| [Figma](./mythril_agent_skills/skills/figma/) | Extract design specs from Figma files for implementation. Covers layout, colors, typography, component specs, auto-triggering on Figma links. | Implementing a design from Figma, inspecting colors/spacing, or matching components |
| [GH Operations](./mythril_agent_skills/skills/gh-operations/) | Use GitHub CLI (`gh`) for issue and pull-request workflows: read/write issues, inspect PRs, create PRs, and read commits. | "use gh", "gh issue", "gh pr", or commit lookup requests |
| [Code Review (Staged)](./mythril_agent_skills/skills/code-review-staged/) | Context-aware code review for Git staged changes. Reads related files for validation, auto-generates and copies commit message to clipboard. | "审查暂存", "看看暂存", "看一下暂存代码", "检查暂存代码", or "review staged" |
| [Code Review (PR)](./mythril_agent_skills/skills/github-code-review-pr/) | Context-aware code review for GitHub Pull Requests (including GitHub Enterprise). Uses partial clone and sparse checkout for deep repo context. | "review PR", "PR review", or reviewing a GitHub PR URL |

---

## Quick Start

Choose the path that fits your needs:

### Option A: Use skills (install via pip)

If you just want to install and use existing skills, start here.
Install the package from PyPI — no need to clone the repository:

```bash
pip install mythril-agent-skills
```

This gives you three commands:

| Command | Description |
|---|---|
| `skills-setup` | Interactive installer — select AI tools and skills to install |
| `skills-cleanup` | Interactive remover — select installed skills to remove |
| `skills-check` | Dependency checker — verify and configure required CLI tools and API keys |

**Install skills:**

```bash
skills-setup              # Interactive: select tools, then skills
skills-setup .cursor      # Direct target: skip tool selection
```

**Remove skills:**

```bash
skills-cleanup
```

**Check dependencies:**

```bash
skills-check                    # Interactive: select skills to check
skills-check gh-operations jira figma  # Check specific skills
```

The checker will:
- Launch an interactive UI to select skills (when run without arguments)
- Detect missing CLI tools (e.g. `gh`) and offer to install them automatically
- Prompt for missing API keys/tokens and save them to your shell config file
- Verify authentication status (e.g. `gh auth status`)

### Option B: Build skills (clone the repository)

If you want to create or modify skills (or contribute changes), clone the repo:

```bash
git clone https://github.com/jie-meng/mythril-agent-skills.git
cd mythril-agent-skills
```

Run the scripts directly — no installation needed:

```bash
python3 scripts/skills-setup.py       # Interactive installer
python3 scripts/skills-cleanup.py     # Interactive remover
python3 scripts/skills-check.py       # Dependency checker
```

---

## How the Installer Works

The `skills-setup` command guides you through two interactive screens:

1. **Select AI tools** — choose which tools to install skills to
2. **Select skills** — choose which skills to install

```
Select skills to install:
Up/Down move | Space toggle | a all/none | Enter confirm | q quit

  [x]  Select All / Deselect All
  ------------------------------------
  [x]  code-review-staged
  [x]  figma
  [x]  gh-operations
  [x]  jira
  [x]  skill-creator

  5/5 selected
```

Tools that are not installed on your machine are shown dimmed with `[-]` markers and cannot be selected.

After installation, `skills-check` runs automatically for skills that need external dependencies (CLI tools or API tokens).

### Supported tools and skills paths

All config directories are relative to the user home directory (`~` on macOS/Linux, `%USERPROFILE%` on Windows).

| # | Tool | Skills path |
|---|---|---|
| 1 | Copilot CLI / VS Code | `~/.copilot/skills/` |
| 2 | Claude Code | `~/.claude/skills/` |
| 3 | Cursor | `~/.cursor/skills/` |
| 4 | Codex | `~/.codex/skills/` |
| 5 | Gemini CLI | `~/.gemini/skills/` |
| 6 | Qwen CLI | `~/.qwen/skills/` |
| 7 | iFlow CLI | `~/.iflow/skills/` |
| 8 | Opencode | `~/.config/opencode/skills/` |
| 9 | Grok CLI | `~/.grok/skills/` |

### Cleanup installed skills

```bash
skills-cleanup
```

The cleanup command guides you through two screens:

1. **Select AI tools** — choose which tool directories to scan (defaults to all detected)
2. **Select skills to remove** — a tree view showing each tool and its installed skills (defaults to none selected)

```
Select skills to remove:
Up/Down move | Space toggle | a all/none | Enter confirm | q quit

  [ ]  Select All / Deselect All
  ------------------------------------
  Copilot CLI  ~/.copilot/skills/  (0/3)
      [ ]  code-review-staged
      [ ]  figma
      [ ]  skill-creator
  Cursor  ~/.cursor/skills/  (0/2)
      [ ]  gh-operations
      [ ]  jira

  0/5 selected for removal
```

### Project-specific setup

To install skills at the project level instead, manually copy them:

```bash
cp -r mythril_agent_skills/skills/skill-name ./your-project/.github/skills/
# or
cp -r mythril_agent_skills/skills/skill-name ./your-project/.claude/skills/
```

---

## Project Structure

```
mythril-agent-skills/
├── mythril_agent_skills/        # Python package
│   ├── cli/                     # CLI entry points
│   │   ├── skills_setup.py      # Interactive installer
│   │   ├── skills_cleanup.py    # Interactive remover
│   │   └── skills_check.py      # Dependency checker & configurator
│   └── skills/                  # Bundled skill definitions
│       ├── skill-creator/       # Create and improve skills
│       ├── figma/               # Design extraction from Figma
│       ├── gh-operations/       # GitHub CLI issue/PR/commit workflows
│       ├── jira/                # Jira REST API issue/sprint/board workflows
│       └── code-review-staged/  # Structured code reviews
├── scripts/                     # Dev scripts & backward-compatible wrappers
├── docs/
│   ├── INSTALLATION.md          # Full dependency reference
│   └── PUBLISHING.md            # PyPI publishing & testing guide
├── pyproject.toml               # Package configuration
├── AGENTS.md                    # Developer guidelines for agents
├── LICENSE                      # Apache 2.0 License
└── README.md                    # This file
```

### Skill Directory Structure

Each skill follows this pattern:

```
mythril_agent_skills/skills/skill-name/
├── SKILL.md                  # Required: Metadata + instructions
├── README.md                 # Optional: Overview for humans
├── scripts/                  # Optional: Helper scripts (Python/Bash)
├── references/               # Optional: Documentation, guides, schemas
├── agents/                   # Optional: Prompts for evaluations
└── assets/                   # Optional: Templates, icons, HTML resources
```

---

## For Developers

### Adding a New Skill

1. Create a new directory under `mythril_agent_skills/skills/`:
   ```bash
   mkdir mythril_agent_skills/skills/my-skill
   ```

2. Create `SKILL.md` with required frontmatter:
   ```yaml
   ---
   name: my-skill
   description: |
      What this skill does and when to use it.
     Include trigger keywords for better AI assistant activation.
   ---

   # My Skill

   Detailed instructions, examples, and workflows...
   ```

3. Commit following this format:
   ```bash
   git add .
   git commit -m "[my-skill] Add initial skill with core workflows"
   ```

### Publishing to PyPI

```bash
python3 scripts/publish.py          # Publish to PyPI
python3 scripts/publish.py --test   # Publish to TestPyPI first
```

For the full publishing workflow, version management, and pre-release testing steps, see **[docs/PUBLISHING.md](./docs/PUBLISHING.md)**.

For full development guidelines, see **[AGENTS.md](./AGENTS.md)**.

---

## Contributing

1. **Fork or create a branch** if you want to add a new skill
2. **Follow** [AGENTS.md](./AGENTS.md) for code style and structure guidelines
3. **Commit** with descriptive messages in the format: `[skill-name] Brief description`
4. **Open a pull request** with a summary of the skill's purpose and usage

---
