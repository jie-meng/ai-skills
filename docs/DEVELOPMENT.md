# Development Guide

This guide is for contributors and developers working on the `mythril-agent-skills` repository itself.

For full coding conventions, naming rules, and architectural decisions, see [AGENTS.md](../AGENTS.md).

## Dev Environment Setup

```bash
git clone https://github.com/jie-meng/mythril-agent-skills.git
cd mythril-agent-skills

# Editable install with test dependencies
pip install -e ".[test]"
```

## Running Tests

Unit tests live in `tests/skills/` and cover pure functions across all skill scripts (URL parsing, formatters, validators, gate logic, template rendering, etc.). They require no network, git, or API access.

```bash
# Run all tests
pytest

# Verbose output
pytest -vv

# Run tests for a specific skill
pytest tests/skills/test_figma.py
pytest tests/skills/test_jira.py

# Filter by keyword
pytest -k "parse_url"
pytest -k "format_adf"
```

### Test coverage by skill

| Skill | Test file | What's covered |
|---|---|---|
| github-code-review-pr | `test_github_code_review_pr.py` | URL parsing, key-value output parsing, 4 quality gates, verdict detection, template rendering (EN/ZH), path selection helpers, cache lookup |
| git-repo-reader | `test_git_repo_reader.py` | URL parsing, normalize key, repo map JSON round-trip |
| figma | `test_figma.py` | Color conversion, paint formatting, node simplification, markdown rendering, URL parsing, safe filename |
| skill-creator | `test_skill_creator.py` | SKILL.md validation (12 edge cases), frontmatter parsing, stats calculation, benchmark aggregation, markdown generation |
| jira | `test_jira.py` | ADF→text (11 node types), issue/search markdown formatting, URL parsing |
| confluence | `test_confluence.py` | HTML stripping (11 patterns), page/space/search/comment formatting, URL parsing |

### Adding tests for new skills

1. Create `tests/skills/test_<skill_name>.py`
2. Import functions from the skill's `scripts/` directory (auto-added to `sys.path` by `conftest.py`)
3. Test pure functions only — avoid network, subprocess, or API calls
4. Run `pytest -vv` to verify

## Adding a New Skill

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

3. Validate the skill structure:

```bash
python3 mythril_agent_skills/skills/skill-creator/scripts/quick_validate.py mythril_agent_skills/skills/my-skill
```

4. Validate description length (must not exceed 1024 characters — multiple AI tools enforce this limit at load time and silently skip skills that exceed it):

```bash
python3 scripts/validate-skill-descriptions.py                # check all skills
python3 scripts/validate-skill-descriptions.py --limit 512     # custom limit
python3 scripts/validate-skill-descriptions.py --skills-dir mythril_agent_skills/skills  # explicit path
```

5. If the skill has Python scripts, add unit tests in `tests/skills/`.

6. Commit following this format:

```bash
git commit -m "[my-skill] Add initial skill with core workflows"
```

For full conventions (naming, description limits, security rules, cache usage, ordering), see [AGENTS.md](../AGENTS.md).

## Versioning Strategy

All version numbers across the project use a **single unified version**. The pip package version, Python `__version__`, and every plugin entry in `marketplace.json` always share the same semver string. There are no per-plugin version numbers.

### Why unified versioning

- Per-skill plugins (`plugins/<name>/`) are thin symlink wrappers pointing back into the main package — they share the same source code and cannot be released independently
- Claude Code uses the version field solely to detect updates and bust its plugin cache; a unified bump ensures all users get the latest content
- Independent versions would add maintenance overhead (per-skill changelogs, selective bumps) with no practical benefit in a monorepo

### Where the version lives

| File | Field | Updated by |
|---|---|---|
| `pyproject.toml` | `version = "x.y.z"` | `bump-version.py` |
| `mythril_agent_skills/__init__.py` | `__version__ = "x.y.z"` | `bump-version.py` |
| `.claude-plugin/marketplace.json` | `"version": "x.y.z"` (all plugin entries) | `bump-version.py` |

### Bumping the version

```bash
python3 scripts/bump-version.py          # show current versions
python3 scripts/bump-version.py 0.3.0    # bump all three files
```

The script updates all files in one shot and verifies consistency afterwards. The publish script (`scripts/publish.py`) also checks that all three sources agree before uploading — if any version is out of sync, it aborts with an actionable error.

Follow [Semantic Versioning](https://semver.org/):
- **Patch** (`0.2.4` → `0.2.5`): bug fixes, doc updates
- **Minor** (`0.2.4` → `0.3.0`): new skills, new features
- **Major** (`0.2.4` → `1.0.0`): breaking changes

---

## Claude Code Plugin Marketplace

This repository is also a [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces). The marketplace catalog is at `.claude-plugin/marketplace.json` and exposes all bundled skills as installable plugins for Claude Code users.

Reference docs:
- [Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) — marketplace.json schema, plugin sources, hosting
- [Create plugins](https://code.claude.com/docs/en/plugins) — plugin structure, skills, agents, hooks
- [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins) — user-facing install commands
- [Plugins reference](https://code.claude.com/docs/en/plugins-reference) — full technical specifications

### How it works

- The `marketplace.json` lists an **all-in-one plugin** (`all-skills`) whose source points to `./mythril_agent_skills`, plus **individual plugins** for each skill under `./plugins/<name>`
- Each per-skill plugin is a thin wrapper directory containing a symlink: `plugins/<name>/skills/<name>` → `mythril_agent_skills/skills/<name>`
- All plugins use `strict: false`, so no separate `plugin.json` is needed — the marketplace entry defines everything
- Claude Code follows symlinks when copying plugins to cache, so the actual skill content is resolved correctly

### Adding a new skill to the marketplace

```bash
# 1. Create the plugin wrapper
mkdir -p plugins/<name>/skills
ln -s ../../../mythril_agent_skills/skills/<name> plugins/<name>/skills/<name>

# 2. Add a new plugin entry in .claude-plugin/marketplace.json
# 3. The all-skills plugin picks it up automatically
```

### Testing locally

```bash
# In Claude Code, add the local marketplace
/plugin marketplace add ./path/to/mythril-agent-skills

# Install the all-in-one plugin
/plugin install all-skills@mythril-agent-skills

# Or install a single skill
/plugin install figma@mythril-agent-skills
```

## Publishing

See [docs/PUBLISHING.md](./PUBLISHING.md) for PyPI publishing and testing instructions.

## Contributing

1. **Fork or create a branch** for your changes
2. **Follow** [AGENTS.md](../AGENTS.md) for code style and structure guidelines
3. **Add tests** for any new script functions
4. **Run `pytest`** to ensure all tests pass
5. **Commit** with descriptive messages: `[skill-name] Brief description`
6. **Open a pull request** with a summary of the changes
