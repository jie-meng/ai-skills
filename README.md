# ai-skills

A repository of reusable skills for AI coding assistants. Skills are self-contained, well-documented modules that extend Github Copilot, Claude Code, Cursor, Codex, Gemini CLI, Qwen CLI, iFlow CLI, Opencode, and other AI tools with specialized capabilities.

## What is a Skill?

A skill is a prompt/instruction bundle that teaches an AI assistant how to handle a specific type of task. Think of it like a specialized tool: it has a name, a triggering description, and detailed instructions.

**Example**: The `code-review-staged` skill teaches Claude Code to review Git staged changes with a structured 6-section code review format. When you ask "review staged", Claude automatically loads this skill and executes its workflow.

## Available Skills

| Skill | Description | Use When |
|---|---|---|
| 🛠️ [Skill Creator](./skills/skill-creator/) | Create skills/prompts for any AI platform. Includes drafting, test case generation, evaluation, benchmarking, description optimization. Supports Github Copilot, Claude Code, Cursor, Codex, and custom platforms. | Create a new skill, improve triggering, or benchmark skill performance |
| 🎨 [Figma](./skills/figma/) | Extract design specs from Figma files for implementation. Covers layout, colors, typography, component specs, auto-triggering on Figma links, design-to-code workflows. | Implementing a design from Figma, inspecting colors/spacing, or matching components |
| 📝 [Code Review (Staged)](./skills/code-review-staged/) | Structured code review for Git staged changes. Tech stack inference, 6-section review, auto-generated commit messages, smart file context reading. | "review staged" or similar code review requests |
| 🧰 [GH Operations](./skills/gh-operations/) | Use GitHub CLI (`gh`) for issue and pull-request workflows: read/write issues, inspect PRs, create PRs, and read commits. | "use gh", "gh issue", "gh pr", "创建PR", "看PR", or commit lookup requests |
| 🎫 [Jira](./skills/jira/) | Use Jira REST API (via bundled Python script) for issue, sprint, and board workflows: view/search/create/edit/assign/transition issues, comment, link, manage sprints. No CLI tools needed. | "jira issue", "jira card", "看卡", "看 jira", "PROJ-123", or sprint/board requests |

---

## Prerequisites

Some skills require external CLI tools or API credentials (environment variables). See **[docs/INSTALLATION.md](./docs/INSTALLATION.md)** for setup instructions.

**Quick agent setup** — copy and paste this prompt to your LLM agent (Claude Code, Cursor, Codex, etc.):

```
Check and configure ai-skills dependencies (CLI tools, API tokens, environment variables) by reading and following the instructions at:
https://raw.githubusercontent.com/jie-meng/ai-skills/main/docs/INSTALLATION.md
```

---

## Quick Start

### Install skills

The setup script syncs all skills from this repository to your AI assistant's user-level configuration directory. It supports two modes:

#### Interactive menu (recommended)

Run without arguments to pick a tool from the menu:

```bash
./scripts/setup
```

```
Select an AI tool to install skills:

  1. Copilot CLI
  2. Claude Code
  3. Cursor
  4. Codex
  5. Gemini CLI
  6. Qwen CLI
  7. iFlow CLI
  8. Opencode

  0. All

Enter your choice:
```

Choose `0` to install to all detected tools at once. Tools that are not installed on your machine will be skipped with a warning.

#### Direct target

Specify the target directory name explicitly:

```bash
./scripts/setup .copilot   # Github Copilot
./scripts/setup .claude    # Claude Code
./scripts/setup .cursor    # Cursor
```

### Supported tools and skills paths

| # | Tool | User-level skills path |
|---|---|---|
| 1 | Copilot CLI / VS Code | `~/.copilot/skills/` |
| 2 | Claude Code | `~/.claude/skills/` |
| 3 | Cursor | `~/.cursor/skills/` |
| 4 | Codex | `~/.codex/skills/` |
| 5 | Gemini CLI | `~/.gemini/skills/` |
| 6 | Qwen CLI | `~/.qwen/skills/` |
| 7 | iFlow CLI | `~/.iflow/skills/` |
| 8 | Opencode | `~/.config/opencode/skills/` |

### Project-specific setup

To install skills at the project level instead, manually copy them:

```bash
cp -r skills/skill-name ./your-project/.github/skills/
# or
cp -r skills/skill-name ./your-project/.claude/skills/
```

## Project Structure

```
ai-skills/
├── skills/                    # All available skills
│   ├── skill-creator/        # Create and improve skills
│   ├── figma/                # Design extraction from Figma
│   ├── gh-operations/        # GitHub CLI issue/PR/commit workflows
│   ├── jira/                 # Jira REST API issue/sprint/board workflows
│   └── code-review-staged/   # Structured code reviews
├── docs/
│   └── INSTALLATION.md       # CLI dependency installation guide
├── scripts/
│   └── setup                 # Installation script for AI assistants
├── AGENTS.md                 # Developer guidelines for agents
├── LICENSE                   # MIT License
└── README.md                 # This file
```

### Skill Directory Structure

Each skill follows this pattern:

```
skills/skill-name/
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

1. Create a new directory under `skills/`:
   ```bash
   mkdir skills/my-skill
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

For full development guidelines, see **[AGENTS.md](./AGENTS.md)**.

---

## Contributing

1. **Fork or create a branch** if you want to add a new skill
2. **Follow** [AGENTS.md](./AGENTS.md) for code style and structure guidelines
3. **Commit** with descriptive messages in the format: `[skill-name] Brief description`
4. **Open a pull request** with a summary of the skill's purpose and usage

---
