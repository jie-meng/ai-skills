# mythril-agent-skills

A unified skill management system for multi-agent AI coding assistants. This package provides a curated collection of reusable skills plus a centralized CLI toolkit to install, configure, and maintain them across Github Copilot, Claude Code, Cursor, Codex, Gemini CLI ...

## What is a Skill?

A skill is a prompt/instruction bundle that teaches an AI assistant how to handle a specific type of task. Think of it like a specialized tool: it has a name, a triggering description, and detailed instructions.

**Example**: The `code-review-staged` skill teaches Claude Code to review Git staged changes with a structured 6-section code review format. When you ask "review staged", Claude automatically loads this skill and executes its workflow.

## Available Skills

| Skill | Description | Use When | Dependencies |
|---|---|---|---|
| [Skill Creator](./mythril_agent_skills/skills/skill-creator/) | Create skills/prompts for any AI platform. Includes drafting, test case generation, evaluation, benchmarking, description optimization. | Create a new skill, improve triggering, or benchmark skill performance | — |
| [Jira](./mythril_agent_skills/skills/jira/) | Use Jira REST API (via bundled Python script) for issue, sprint, and board workflows. No CLI tools needed. | "jira issue", "jira card", "jira ticket", issue key (PROJ-123), or Jira URL | `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL` |
| [Confluence](./mythril_agent_skills/skills/confluence/) | Use Confluence REST API (via bundled Python script) for page, space, comment, and label workflows. No CLI tools needed. | "confluence page", "wiki page", "search confluence", "create wiki page", or Confluence URL | `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL` |
| [Figma](./mythril_agent_skills/skills/figma/) | Extract design specs from Figma files for implementation. Covers layout, colors, typography, component specs, auto-triggering on Figma links. | Figma URL, "implement this design", "what does the design look like", "colors/spacing/fonts from design", "according to Figma" | `FIGMA_ACCESS_TOKEN` |
| [Code Review (Staged)](./mythril_agent_skills/skills/code-review-staged/) | Context-aware code review for Git staged changes. Reads related files for validation, auto-generates and copies commit message to clipboard. | "review staged", "staged code review", "check staged", "look at staged", or "review staged code" | — |
| [Code Review (Local Branch Diff)](./mythril_agent_skills/skills/branch-diff-review/) | Context-aware code review for branch differences using pure local git operations. No platform API needed — works with any git repo (GitHub, GitLab, Gitee, Bitbucket, self-hosted, etc.). | "branch diff review", "branch review", "review feat/xxx to main", "compare branches for review" | — |
| [Code Review (Github PR)](./mythril_agent_skills/skills/github-code-review-pr/) | Context-aware code review for Pull Requests via `gh` CLI. Supports github.com and GitHub Enterprise (any domain). Uses partial clone and sparse checkout for deep repo context. | "review PR", "PR review", any URL containing `/pull/` with a review request | `gh` CLI |
| [GH Operations](./mythril_agent_skills/skills/gh-operations/) | Use GitHub CLI (`gh`) for issue and pull-request workflows: read/write issues, inspect PRs, create PRs, and read commits. | "use gh", "gh issue", "gh pr", or commit lookup requests | `gh` CLI |
| [ImageMagick](./mythril_agent_skills/skills/imagemagick/) | Process and manipulate images via ImageMagick CLI. Supports resizing, format conversion, cropping, thumbnails, effects, watermarks, batch processing, and metadata extraction. | "resize image", "convert to webp", "image thumbnail", "batch resize", "compress image", "add watermark", "imagemagick" | `magick` CLI |
| [FFmpeg](./mythril_agent_skills/skills/ffmpeg/) | Process and manipulate video and audio files via FFmpeg CLI. Supports transcoding, format conversion, trimming, merging, resizing, compression, extracting audio, subtitles, GIF creation, and audio format conversion (MP3, WAV, PCM, OGG, AAC, FLAC, OPUS). | "convert video", "compress video", "trim video", "extract audio", "mp3 to wav", "convert audio", "video to gif", "ffmpeg" | `ffmpeg` CLI |

---

## Quick Start

Choose the path that fits your needs:

### Option A: Use skills (install via pip)

If you just want to install and use existing skills, start here.
Install the package from PyPI — no need to clone the repository:

```bash
pip install mythril-agent-skills
```

To upgrade to the latest version:

```bash
pip install -U mythril-agent-skills
```

This gives you four commands:

| Command | Description |
|---|---|
| `skills-setup` | Interactive installer — select AI tools and skills to install |
| `skills-cleanup` | Interactive remover — select installed skills to remove |
| `skills-check` | Dependency checker — verify and configure required CLI tools and API keys |
| `skills-clean-cache` | Cache cleaner — remove temp files created by skills at runtime |

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

**Clean up cached temp files:**

```bash
skills-clean-cache          # Interactive: list cache, confirm before deleting
skills-clean-cache --force  # Delete without confirmation
```

The checker will:
- Launch an interactive UI to select skills (when run without arguments)
- Detect missing CLI tools (e.g. `gh`) and offer to install them automatically
- Prompt for missing API keys/tokens and save them to your shell config file
- Verify authentication status (e.g. `gh auth status`)

### Option B: Fork or clone for customization

If you want to **customize existing skills, create your own, or maintain private skills**, fork or clone the repo:

```bash
# Fork on GitHub first, then clone your fork:
git clone https://github.com/<your-username>/mythril-agent-skills.git
# Or clone the original repo directly:
git clone https://github.com/jie-meng/mythril-agent-skills.git

cd mythril-agent-skills
```

Run the scripts directly — no installation needed:

```bash
python3 scripts/skills-setup.py       # Interactive installer
python3 scripts/skills-cleanup.py     # Interactive remover
python3 scripts/skills-check.py       # Dependency checker
```

**Stay up to date with upstream:**

When you want to pull in the latest skills from the original repository without overwriting your custom work, use the sync script. Exclude your custom or modified skills in `.sync-upstream.json`:

```json
{
  "exclude_skills": ["my-custom-skill", "jira"]
}
```

Then sync anytime:

```bash
python3 scripts/sync-upstream.py              # Interactive sync
python3 scripts/sync-upstream.py --dry-run     # Preview changes only
python3 scripts/sync-upstream.py --force        # Apply without confirmation
```

The sync script updates skills, CLI tools, docs, and even itself — while preserving your excluded custom skills.

For the full guide, see **[docs/FORK-SYNC.md](./docs/FORK-SYNC.md)**.

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
│       ├── ffmpeg/              # Video & audio processing via FFmpeg CLI
│       ├── imagemagick/         # Image processing via ImageMagick CLI
│       ├── jira/                # Jira REST API issue/sprint/board workflows
│       └── code-review-staged/  # Structured code reviews
├── scripts/                     # Dev scripts & backward-compatible wrappers
│   └── sync-upstream.py         # Fork upstream sync tool
├── docs/
│   ├── INSTALLATION.md          # Full dependency reference
│   ├── PUBLISHING.md            # PyPI publishing & testing guide
│   └── FORK-SYNC.md             # Fork sync guide
├── .sync-upstream.json           # Upstream sync configuration (for forks)
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
   license: Apache-2.0
   ---

   # My Skill

   Detailed instructions, examples, and workflows...
   ```

3. Commit following this format:
   ```bash
   git add .
   git commit -m "[my-skill] Add initial skill with core workflows"
   ```

For full development guidelines and publishing instructions, see **[AGENTS.md](./AGENTS.md)** and **[docs/PUBLISHING.md](./docs/PUBLISHING.md)**.

---

## Contributing

1. **Fork or create a branch** if you want to add a new skill
2. **Follow** [AGENTS.md](./AGENTS.md) for code style and structure guidelines
3. **Commit** with descriptive messages in the format: `[skill-name] Brief description`
4. **Open a pull request** with a summary of the skill's purpose and usage

---
