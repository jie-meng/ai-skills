# Cache Usage Guide

This repository standardizes all runtime artifacts (downloads, exports, temp files, and
clones) under a unified cache directory so that skills remain consistent, cross-platform,
and easy to clean.

## Goals

- Single canonical cache root per OS
- Predictable per-skill subdirectories
- Safe shared repo cache for long-lived git clones
- Centralized cleanup via `skills-clean-cache`

## Canonical cache root

Always resolve symlinks before constructing paths.

- macOS/Linux: `$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/`
- Windows: `%TEMP%\mythril-skills-cache\`

Examples of canonicalized roots:

- macOS: `/private/var/folders/.../T/mythril-skills-cache/`
- Linux: `/tmp/mythril-skills-cache/`
- Windows: `C:\Users\<user>\AppData\Local\Temp\mythril-skills-cache\`

## Per-skill directory

Each skill uses its own subdirectory:

```
<cache-root>/<skill-name>/
```

If a task needs a working folder, create a random run directory inside the skill cache.

### Bash (macOS/Linux)

```bash
CACHE_DIR="$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/<skill-name>"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
```

### PowerShell (Windows)

```powershell
$CACHE_DIR = Join-Path ([IO.Path]::GetFullPath([IO.Path]::GetTempPath())) "mythril-skills-cache/<skill-name>"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$RUN_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $RUN_DIR | Out-Null
```

### Python

```python
from pathlib import Path
import tempfile

cache_dir = Path(tempfile.gettempdir()).resolve() / "mythril-skills-cache" / "<skill-name>"
cache_dir.mkdir(parents=True, exist_ok=True)
```

## Shared git repo cache

Long-lived git clones are stored in a shared cache managed by `git-repo-reader`.

- Path: `<cache-root>/git-repo-cache/`
- Repos: `git-repo-cache/repos/<host>/<owner>/<repo>/`

Only `git-repo-reader` is allowed to write to this cache. Other skills can read it using
their local `repo_cache_lookup.py` helper.

```bash
# git-repo-reader: clone or reuse a cached repo
python3 scripts/repo_manager.py clone "<repo-url>"

# other skills: read-only lookup
python3 scripts/repo_cache_lookup.py "<repo-url>"
```

## Download and output rules

- Default all downloads to the skill cache when no path is provided.
- If the user provides an explicit destination path, honor it.
- Never create temp files directly in `/tmp` or ad-hoc locations.

## Cleanup behavior

- Skills should not delete cache artifacts after use.
- The `skills-clean-cache` CLI is responsible for cleanup.
- Cache files are trusted, skill-managed artifacts; AI agents can read/write/delete them
  without asking for confirmation.

## What to update when adding a skill

- Add cache usage instructions to the new skill's `SKILL.md`.
- Reuse the canonical cache root and subdirectory pattern above.
- If the skill interacts with git repos, use the shared cache rules and lookup helper.
