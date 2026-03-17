# Fork Sync Guide

This guide explains how to maintain a **private fork** of mythril-agent-skills — keeping your custom skills separate while staying up to date with the upstream repository.

## Why Fork?

The main [mythril-agent-skills](https://github.com/jie-meng/mythril-agent-skills) repository contains only public, general-purpose skills. If you need **private or organization-specific skills**, you can:

1. Fork the repository
2. Add your own skills under `mythril_agent_skills/skills/`
3. Sync upstream updates — your custom skills with unique names are automatically safe

## Choosing a Sync Method

| Method | Best for | Handles modified upstream skills? |
|---|---|---|
| **GitHub Sync Fork** | github.com forks, simple setups | No — may cause merge conflicts |
| **Sync script** (`sync-upstream.py`) | Any platform; fine-grained control | Yes — use `exclude_skills` to skip them |

### GitHub Sync Fork

If you forked on **github.com**, you can use GitHub's built-in **"Sync fork"** button on your fork's page. This performs a standard git merge/fast-forward.

- Works well when you **only add custom skills with unique names** — no conflicts
- If you've **modified an upstream skill** (e.g., customized `jira`), you may get merge conflicts that need manual resolution
- No extra tooling required — just click the button on GitHub

### Sync script

For forks on **GitHub Enterprise, GitLab, Gitee, Bitbucket**, or any other platform — or when you need **selective sync with `exclude_skills`** to protect modified upstream skills — use the bundled sync script.

## Quick Start (Sync Script)

```bash
# 1. Fork the repo, then clone your fork
git clone https://github.com/<your-username>/mythril-agent-skills.git
cd mythril-agent-skills

# 2. Add your custom skills
mkdir mythril_agent_skills/skills/my-custom-skill
# ... create SKILL.md, scripts, etc.

# 3. Sync upstream changes anytime
#    Custom skills with unique names are never touched — no config needed
python3 scripts/sync-upstream.py
```

## Configuration

The sync behavior is controlled by **`.sync-upstream.json`** in the repository root:

```json
{
  "upstream_repo": "https://github.com/jie-meng/mythril-agent-skills.git",
  "upstream_branch": "main",
  "exclude_skills": ["jira"]
}
```

### Configuration Fields

| Field | Default | Description |
|---|---|---|
| `upstream_repo` | `https://github.com/jie-meng/mythril-agent-skills.git` | Upstream git repository URL |
| `upstream_branch` | `main` | Branch to sync from |
| `exclude_skills` | `[]` | Upstream skill names to skip during sync (see [When to use exclude_skills](#when-to-use-exclude_skills)) |

### When to use `exclude_skills`

The sync script only processes skills that **exist in upstream**. Custom skills with unique names (not present in upstream) are **never touched** — you don't need to add them to `exclude_skills`.

Use `exclude_skills` when:
- You've **modified an upstream skill** locally (e.g., customized `jira` for your organization) and want to prevent it from being overwritten
- You want to **preemptively protect** a custom skill name in case upstream adds a skill with the same name in the future

## Usage

### Basic Sync

```bash
python3 scripts/sync-upstream.py
```

This will:
1. Fetch the latest upstream code
2. Compare your local files with upstream
3. Show a summary of what will change
4. Ask for confirmation before applying

### Dry Run (Preview Only)

```bash
python3 scripts/sync-upstream.py --dry-run
```

Shows what would change without modifying any files. Use this to preview before committing.

### Force Sync (No Confirmation)

```bash
python3 scripts/sync-upstream.py --force
```

Applies changes without asking for confirmation. Useful in CI/CD pipelines.

### Example Output

```
mythril-agent-skills upstream sync

  Excluded skills: jira
  Added remote _mythril_upstream → https://github.com/jie-meng/mythril-agent-skills.git
  Fetching _mythril_upstream/main ...
  Extracting upstream content ...

=== Upstream Sync Summary ===

  New skills:
    + new-upstream-skill
  Updated skills:
    ~ figma
    ~ gh-operations
  Updated files:
    ~ mythril_agent_skills/cli/skills_setup.py
    ~ scripts/sync-upstream.py

  Excluded (in exclude_skills):
    ⊘ jira (upstream has changes, skipped)

  Total: 15 file(s) to sync

Apply these changes? [y/N]
```

## What Gets Synced

The script syncs the following paths from upstream:

| Path | Description |
|---|---|
| `mythril_agent_skills/skills/*` | All skills (except those in `exclude_skills`) |
| `mythril_agent_skills/cli/` | CLI tools (setup, cleanup, check, clean-cache) |
| `mythril_agent_skills/__init__.py` | Package version |
| `scripts/sync-upstream.py` | The sync script itself |
| `docs/` | Documentation |
| `AGENTS.md` | Agent guidelines |

### What Does NOT Get Synced

- **Excluded skills** — anything listed in `exclude_skills`
- **Your own new skills** — skills that only exist in your fork are untouched
- **`.sync-upstream.json`** — your configuration is never overwritten
- **`README.md`** — your fork's README stays as-is
- **`.git/`** — git history is never modified
- **`pyproject.toml`** — your fork's package config stays as-is (you may want to update this manually)

## Workflow Recommendations

### Initial Setup

1. Fork the repository on GitHub
2. Clone your fork locally
3. Add your custom skills (use unique names — they're automatically safe from sync)
4. If you've modified any upstream skill, add its name to `exclude_skills` in `.sync-upstream.json`
5. Commit everything

### Regular Sync Routine

```bash
# Make sure your working tree is clean
git status

# Preview what's changed upstream
python3 scripts/sync-upstream.py --dry-run

# Apply the sync
python3 scripts/sync-upstream.py

# Review the changes
git diff

# Commit
git add -A
git commit -m "Sync upstream mythril-agent-skills changes"
```

### When You Customize an Upstream Skill

If you modify an existing upstream skill (e.g., customizing `jira` for your organization):

1. Make your changes to the skill
2. Add the skill name to `exclude_skills` in `.sync-upstream.json`:
   ```json
   {
     "exclude_skills": ["jira"]
   }
   ```
3. Commit both the skill changes and the config update

The sync script will warn you when an excluded skill has upstream updates, so you can manually review and merge changes if needed.

## Troubleshooting

### "You have uncommitted changes"

The script warns if your working tree is dirty. Commit or stash your changes first:

```bash
git stash
python3 scripts/sync-upstream.py
git stash pop
```

### Network Issues

The script needs to fetch from the upstream remote. If you're behind a firewall or proxy, ensure `git fetch` can reach the upstream URL.

### Merge Conflicts After Sync

The sync script overwrites files directly (no git merge). If you've modified a synced file (e.g., a CLI script), your changes will be overwritten. To prevent this:

- For skills: add them to `exclude_skills`
- For other files: manually diff after sync and re-apply your changes
