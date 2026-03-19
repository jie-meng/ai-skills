# mythril-agent-skills

A unified skill management system for multi-agent AI coding assistants. This toolkit (distributed as a Python package) provides a curated collection of reusable skills plus centralized CLI commands to install, configure, and maintain them across Github Copilot, Claude Code, Cursor, Codex, Gemini CLI ...

## What is a Skill?

A skill is a prompt/instruction bundle that teaches an AI assistant how to handle a specific type of task. Think of it like a specialized tool: it has a name, a triggering description, and detailed instructions.

There are two primary types of skills based on their scope and how they are managed:

| Feature | User-Level Skills (Global) | Project-Level Skills (Local) |
| :--- | :--- | :--- |
| **Scope** | Available across all your projects | Confined to a specific project repository |
| **Portability** | Reusable across different projects on your machine | Moves with that specific project repository |
| **Use Cases** | General-purpose tools (e.g., Jira integration, code review, Git operations, Figma) | Project-specific rules (e.g., custom UI guidelines, specific build/deploy steps) |
| **Management** | Installed in your user home directory (`~/.claude/skills`, `~/.cursor/skills`, etc.) | Stored inside the project directory (e.g., `.claude/skills/`, `.github/skills/`) |
| **Version Control**| Managed centrally via this toolkit | Committed to the project's Git repository and shared with the team |

### How this toolkit fits in

**`mythril-agent-skills` is designed to manage User-Level Skills.** It acts as a centralized CLI toolkit to install, configure, and keep your general-purpose skills synchronized across multiple AI coding assistants on your machine. 

For **Project-Level Skills**, you don't need this installer. Instead, we recommend using the included **[Skill Creator](./mythril_agent_skills/skills/skill-creator/)** skill. Simply invoke the Skill Creator within your project workspace to scaffold a new project-specific skill, and then commit it directly to your version control system so your entire team can benefit from it.

## Available Skills

| Skill | Description | Use When | Dependencies |
|---|---|---|---|
| **Meta** | | | |
| [Skill Creator](./mythril_agent_skills/skills/skill-creator/) | Create skills/prompts for any AI platform. Includes drafting, test case generation, evaluation, benchmarking, description optimization. | Create a new skill, improve triggering, or benchmark skill performance | — |
| **Code Review** | | | |
| [Code Review (Staged)](./mythril_agent_skills/skills/code-review-staged/) | Context-aware code review for Git staged changes. Reads related files for validation, auto-generates and copies commit message to clipboard. | "review staged", "staged code review", "check staged", "look at staged", or "review staged code" | `git` CLI |
| [Code Review (Local Branch Diff)](./mythril_agent_skills/skills/branch-diff-review/) | Context-aware code review for branch differences using pure local git operations. No platform API needed — works with any git repo (GitHub, GitLab, Gitee, Bitbucket, self-hosted, etc.). | "branch diff review", "branch review", "review feat/xxx to main", "compare branches for review" | `git` CLI |
| [Code Review (Github PR)](./mythril_agent_skills/skills/github-code-review-pr/) | Context-aware code review for Pull Requests via `gh` CLI. Supports github.com and GitHub Enterprise (any domain). Uses partial clone and sparse checkout for deep repo context. | "review PR", "PR review", any URL containing `/pull/` with a review request | `git` CLI, `gh` CLI |
| **Git & GitHub** | | | |
| [Git Repo Reader](./mythril_agent_skills/skills/git-repo-reader/) | Clone, cache, and read any git repository from any hosting platform (GitHub, GitLab, Gitee, Bitbucket, self-hosted, etc.) for code exploration and analysis. Caches repos across sessions for reuse. | "look at this repo", "read this repo", "how does this repo implement X", git clone URL + code question | `git` CLI |
| [GH Operations](./mythril_agent_skills/skills/gh-operations/) | Use GitHub CLI (`gh`) for GitHub issue/PR workflows: read/write issues, inspect/create pull requests, and add PR comments (including inline line-level review comments). | "use gh", "gh issue", "gh pr", "comment on this PR line", or "add an inline PR comment" | `gh` CLI |
| **API Integrations** | | | |
| [Jira](./mythril_agent_skills/skills/jira/) | Use Jira REST API (via bundled Python script) for issue, sprint, and board workflows. No CLI tools needed. | "jira issue", "jira card", "jira ticket", issue key (PROJ-123), or Jira URL | `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL` |
| [Confluence](./mythril_agent_skills/skills/confluence/) | Use Confluence REST API (via bundled Python script) for page, space, comment, and label workflows. No CLI tools needed. | "confluence page", "wiki page", "search confluence", "create wiki page", or Confluence URL | `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL` |
| [Figma](./mythril_agent_skills/skills/figma/) | Extract design specs from Figma files for implementation. Covers layout, colors, typography, component specs, auto-triggering on Figma links. | Figma URL, "implement this design", "what does the design look like", "colors/spacing/fonts from design", "according to Figma" | `FIGMA_ACCESS_TOKEN` |
| **Media Processing** | | | |
| [ImageMagick](./mythril_agent_skills/skills/imagemagick/) | Process and manipulate images via ImageMagick CLI. Supports resizing, format conversion, cropping, thumbnails, effects, watermarks, batch processing, and metadata extraction. | "resize image", "convert to webp", "image thumbnail", "batch resize", "compress image", "add watermark", "imagemagick" | `magick` CLI |
| [FFmpeg](./mythril_agent_skills/skills/ffmpeg/) | Process and manipulate video and audio files via FFmpeg CLI. Supports transcoding, format conversion, trimming, merging, resizing, compression, extracting audio, subtitles, GIF creation, and audio format conversion (MP3, WAV, PCM, OGG, AAC, FLAC, OPUS). | "convert video", "compress video", "trim video", "extract audio", "mp3 to wav", "convert audio", "video to gif", "ffmpeg" | `ffmpeg` CLI |

---

## Quick Start

Choose the path that fits your needs:

### Option A: Use the skills provided (install via pip)

If you just want to install and use existing skills, start here.
Install it from PyPI — no need to clone the repository:

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
skills-clean-cache --show-repos  # Optional: show cached repo names and sizes
```

The checker will:
- Launch an interactive UI to select skills (when run without arguments)
- Detect missing CLI tools (e.g. `gh`) and offer to install them automatically
- Prompt for missing API keys/tokens and save them to your shell config file
- Verify authentication status (e.g. `gh auth status`)

### Option B: Customize your own skills (GitHub fork or independent clone)

If you want to customize skills and keep your own repository, you have two equivalent paths:

- **GitHub fork** (stay linked to upstream on github.com)
- **Independent clone** (fully detach from upstream, any platform)

Pick one setup below, then follow the shared usage steps after it.

**Setup A — GitHub fork (linked to upstream):**

```bash
# Fork on GitHub, then clone your fork:
git clone https://github.com/<your-username>/mythril-agent-skills.git
cd mythril-agent-skills
```

**Setup B — Independent clone (detached from upstream, non-GitHub hosting):**

```bash
# 1. Clone the original repo
git clone https://github.com/jie-meng/mythril-agent-skills.git
cd mythril-agent-skills

# 2. Detach from upstream (removes .git, creates fresh repo)
python3 scripts/init-fork.py

# 3. Follow the on-screen instructions to push to your new remote
```

The init script will:
- Delete `.git` history (severs the link to upstream)
- Run `git init` (empty repo — you make the first commit)
- Optionally rename the root directory

> **Warning**: This is a destructive, one-time operation. Run it on a fresh clone only.

**Shared usage for both setups:**

Run the scripts directly — no installation needed:

```bash
python3 scripts/skills-setup.py       # Interactive installer
python3 scripts/skills-cleanup.py     # Interactive remover
python3 scripts/skills-check.py       # Dependency checker
```

**Stay up to date with upstream (optional):**

- **Setup A (GitHub fork)**: use GitHub's built-in **"Sync fork"** button
- **Setup B (Independent clone)**: use the bundled sync script (below)

```bash
python3 scripts/sync-upstream.py              # Interactive sync
python3 scripts/sync-upstream.py --dry-run     # Preview changes only
python3 scripts/sync-upstream.py --force        # Apply without confirmation
```

The sync script only processes skills that exist in upstream. **Your custom skills with unique names are never touched** — no configuration needed.

Use `exclude_skills` in `.sync-upstream.json` only when you need to prevent an **upstream skill** from being overwritten (e.g., you've modified `jira` locally, or you want to protect a custom skill name in case upstream adds one with the same name in the future):

```json
{
  "exclude_skills": ["jira"]
}
```

For the full guide, see **[docs/FORK-SYNC.md](./docs/FORK-SYNC.md)**.

- Works well when you **only add custom skills with unique names** — no conflicts
- If you've **modified an upstream skill** (e.g., customized `jira`), you may get merge conflicts that need manual resolution

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
│       ├── code-review-staged/  # Structured code reviews
│       └── git-repo-reader/     # Clone and read any git repo
├── scripts/                     # Dev scripts & backward-compatible wrappers
│   ├── sync-upstream.py         # Fork upstream sync tool
│   └── init-fork.py             # One-time fork initializer (detach + git re-init)
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
