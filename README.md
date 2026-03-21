# mythril-agent-skills

<p align="center">
  <img src="docs/assets/banner.webp" width="500" alt="mythril-agent-skills">
</p>

English | [中文](./README.zh-CN.md)

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

English | [中文](./README.zh-CN.md)

<details>
<summary><b>Meta</b></summary>
<br>

**[Skill Creator](./mythril_agent_skills/skills/skill-creator/)**

Create skills/prompts for any AI platform — drafting, test case generation, evaluation, benchmarking, description optimization.

- **Try:** Create a new skill for Cursor
- **Deps:** —

</details>

<details>
<summary><b>Code Review</b></summary>
<br>

**[Code Review (Staged)](./mythril_agent_skills/skills/code-review-staged/)**

Context-aware code review for Git staged changes. Reads related files for validation.

- **Try:** Review staged changes
- **Deps:** `git` CLI

**[Code Review (Local Branch Diff)](./mythril_agent_skills/skills/branch-diff-review/)**

Context-aware code review for branch differences using pure local git operations. No platform API needed — works with any git repo (GitHub, GitLab, Gitee, Bitbucket, self-hosted, etc.).

- **Try:** Review feat/123 to main
- **Deps:** `git` CLI

**[Code Review (GitHub PR)](./mythril_agent_skills/skills/github-code-review-pr/)**

Context-aware code review for Pull Requests via `gh` CLI. Supports github.com and GitHub Enterprise (any domain). Uses partial clone and sparse checkout for deep repo context.

- **Try:** Review this PR: https://github.com/xxx/yyy/pull/100
- **Deps:** `git` CLI, `gh` CLI

</details>

<details>
<summary><b>Git & GitHub</b></summary>
<br>

**[Git Repo Reader](./mythril_agent_skills/skills/git-repo-reader/)**

Clone, cache, and read any git repository from any hosting platform (GitHub, GitLab, Gitee, Bitbucket, self-hosted, etc.) for code exploration and analysis. Caches repos across sessions for reuse.

- **Try:** Look at this repo: https://github.com/xxx/yyy
- **Deps:** `git` CLI

**[GH Operations](./mythril_agent_skills/skills/gh-operations/)**

Use GitHub CLI (`gh`) for GitHub issue/PR workflows: read/write issues, inspect/create pull requests, and add PR comments (including inline line-level review comments).

- **Try:** Look at this issue: https://github.com/xxx/yyy/issues/18331
- **Deps:** `gh` CLI

</details>

<details>
<summary><b>API Integrations</b></summary>
<br>

**[Jira](./mythril_agent_skills/skills/jira/)**

Use Jira REST API (via bundled Python script) for issue, sprint, and board workflows.

- **Try:** Look at this Jira ticket: https://yourorg.atlassian.net/browse/PROJ-123
- **Deps:** `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`

**[Confluence](./mythril_agent_skills/skills/confluence/)**

Use Confluence REST API (via bundled Python script) for page, space, comment, and label workflows.

- **Try:** Look at this Confluence page: https://yourorg.atlassian.net/wiki/spaces/XX/pages/123
- **Deps:** `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`

**[Figma](./mythril_agent_skills/skills/figma/)**

Extract design specs from Figma files for implementation. Covers layout, colors, typography, component specs, auto-triggering on Figma links.

- **Try:** What does this Figma design look like: https://figma.com/file/xxx
- **Deps:** `FIGMA_ACCESS_TOKEN`

</details>

<details>
<summary><b>Media Processing</b></summary>
<br>

**[ImageMagick](./mythril_agent_skills/skills/imagemagick/)**

Process and manipulate images via ImageMagick CLI. Supports resizing, format conversion, cropping, thumbnails, effects, watermarks, batch processing, and metadata extraction.

- **Try:** Resize photo.jpg to 800x600
- **Deps:** `magick` CLI

**[FFmpeg](./mythril_agent_skills/skills/ffmpeg/)**

Process and manipulate video and audio files via FFmpeg CLI. Supports transcoding, format conversion, trimming, merging, resizing, compression, extracting audio, subtitles, GIF creation, and audio format conversion (MP3, WAV, PCM, OGG, AAC, FLAC, OPUS).

- **Try:** Convert video.mov to mp4
- **Deps:** `ffmpeg` CLI

</details>

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
skills-clean-cache --repos  # Interactive: select repos to delete
```

The checker will:
- Launch an interactive UI to select skills (when run without arguments)
- Detect missing CLI tools (e.g. `gh`) and offer to install them automatically
- Prompt for missing API keys/tokens and save them to your shell config file
- Verify authentication status (e.g. `gh auth status`)

### Option B: Claude Code plugin (one-command install)

If you use [Claude Code](https://code.claude.com/), you can install skills as a [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) — no pip required. See also: [discover and install plugins](https://code.claude.com/docs/en/discover-plugins).

```bash
# Add the marketplace
/plugin marketplace add jie-meng/mythril-agent-skills
```

Install all skills at once:

```bash
/plugin install all-skills@mythril-agent-skills
```

Or install individual skills as needed:

```bash
/plugin install figma@mythril-agent-skills
/plugin install jira@mythril-agent-skills
/plugin install github-code-review-pr@mythril-agent-skills
```

<details>
<summary>All available plugins</summary>

| Plugin | Description |
|---|---|
| `all-skills` | All-in-one bundle (all 11 skills) |
| `skill-creator` | Create and improve skills/prompts for any AI platform |
| `code-review-staged` | Code review for git staged changes |
| `branch-diff-review` | Code review for local branch differences |
| `github-code-review-pr` | PR code review via GitHub CLI |
| `git-repo-reader` | Clone, cache, and read any git repository |
| `gh-operations` | GitHub CLI operations for issues and PRs |
| `jira` | Jira REST API integration |
| `confluence` | Confluence REST API integration |
| `figma` | Extract Figma design specs |
| `imagemagick` | Image processing via ImageMagick CLI |
| `ffmpeg` | Video and audio processing via FFmpeg CLI |

</details>

To update later:

```bash
/plugin marketplace update mythril-agent-skills
```

To uninstall a plugin:

```bash
/plugin uninstall figma@mythril-agent-skills
```

To remove the marketplace entirely (also uninstalls all its plugins):

```bash
/plugin marketplace remove mythril-agent-skills
```

> **Note:** This option installs skills into Claude Code only. For multi-tool support (Cursor, Copilot, Codex, Gemini CLI, etc.), use Option A.

### Option C: Customize your own skills (GitHub fork or independent clone)

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
| 7 | Opencode | `~/.config/opencode/skills/` |
| 8 | Grok CLI | `~/.grok/skills/` |

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
├── .claude-plugin/              # Claude Code plugin marketplace
│   └── marketplace.json         # Plugin catalog for /plugin install
├── mythril_agent_skills/        # Python package (also the all-in-one plugin)
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
├── plugins/                     # Per-skill plugin wrappers (symlinks into skills/)
├── scripts/                     # Dev scripts & backward-compatible wrappers
│   ├── sync-upstream.py         # Fork upstream sync tool
│   └── init-fork.py             # One-time fork initializer (detach + git re-init)
├── tests/                       # Unit tests for skill scripts
│   └── skills/                  # One test file per skill
├── docs/
│   ├── DEVELOPMENT.md           # Dev setup, tests, contributing
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

## Development & Contributing

For dev environment setup, running tests, adding new skills, and contribution guidelines, see **[docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md)**.

For full coding conventions and architectural decisions, see **[AGENTS.md](./AGENTS.md)**.

---
