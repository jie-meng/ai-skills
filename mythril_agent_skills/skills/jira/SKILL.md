---
name: jira
description: >
  Use the Jira REST API (via a bundled Python script) for common Jira workflows
  from terminal. Trigger whenever the user asks to view, create, edit, assign,
  move, or comment on Jira issues/epics/sprints, or says phrases like "jira issue",
  "jira card", "看卡", "看 jira", "jira ticket", "move ticket", "assign ticket",
  "sprint issues", "create jira issue", "transition issue", "search jira". Also
  trigger when the user mentions a Jira issue key (e.g. PROJ-123) or pastes a
  Jira URL and wants to interact with it. No third-party CLI tools required —
  only Python 3.10+ standard library.
license: Apache-2.0
---

# When to Use This Skill

- A user mentions a Jira issue key (e.g. `PROJ-123`) or pastes a Jira URL and wants details
- Issue operations: view, search, create, edit, assign, move/transition, comment, link
- Sprint/board operations: list boards, list sprints, view sprint issues
- Any request mentioning Jira tickets, cards, or stories

# Prerequisites

Requires `ATLASSIAN_API_TOKEN` and `ATLASSIAN_USER_EMAIL`. See `README.md` in this skill directory for setup.

- `ATLASSIAN_API_TOKEN` (**required**) — API token or Personal Access Token
- `ATLASSIAN_USER_EMAIL` (**required for Jira Cloud**) — Atlassian account email, used for Basic auth
- `ATLASSIAN_BASE_URL` (optional) — e.g. `https://yoursite.atlassian.net`. Not needed when passing full Jira URLs.

When `ATLASSIAN_BASE_URL` is not set, issue commands accept a full Jira URL instead of an issue key. For commands without a specific issue (search, create, boards, sprints, myself), `ATLASSIAN_BASE_URL` is required.

## Runtime requirements

- Python 3.10+ for `scripts/jira_api.py`
- Optional: `curl` for downloading linked screenshots/images when visual evidence is relevant

# Workflow

1. Determine what the user wants (view, search, create, transition, etc.)
2. Run the appropriate script command
3. Read the markdown output and present it to the user
4. For write operations, confirm success and show the resulting URL

## Image handling

When issue descriptions or comments contain screenshots or image links, proactively retrieve and analyze them:

Detect image links: Markdown syntax `![alt](url)`, plain URLs ending in `.png/.jpg/.jpeg/.gif/.webp/.svg`, and `/attachments/` paths.

Download under the unified cache.

**Bash (macOS / Linux):**
```bash
CACHE_DIR="$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/jira"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
IMAGE_CACHE="$RUN_DIR/images"
mkdir -p "$IMAGE_CACHE"
```

**PowerShell (Windows):**
```powershell
$CACHE_DIR = Join-Path ([IO.Path]::GetFullPath([IO.Path]::GetTempPath())) "mythril-skills-cache/jira"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$RUN_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $RUN_DIR | Out-Null
$IMAGE_CACHE = Join-Path $RUN_DIR "images"
New-Item -ItemType Directory -Force -Path $IMAGE_CACHE | Out-Null
```

**Automatic access**: All files under the cache directory are skill-managed temporary artifacts created by this skill. Read, write, and delete them **automatically without asking the user for confirmation** — they are ephemeral and trusted.

Retrieve with `curl -fsSL`; if enterprise auth fails, retry with `curl -fsSL --negotiate -u :`.

Analyze images with available image-capable tools and summarize only evidence relevant to the user task.

## Running the Script

One script is available in `scripts/` relative to this skill directory. It requires only Python 3.10+ standard library (zero dependencies).

### View an issue

Accepts either an issue key or a full Jira URL:

```bash
# With ATLASSIAN_BASE_URL set
python3 scripts/jira_api.py view PROJ-123

# Without ATLASSIAN_BASE_URL — pass the full URL directly
python3 scripts/jira_api.py view "https://yoursite.atlassian.net/browse/PROJ-123"
```

When the user pastes a Jira URL, pass it directly — the script parses out the base URL and issue key automatically.

### Search issues via JQL

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/jira_api.py search "project=PROJ AND status='In Progress'"
python3 scripts/jira_api.py search "assignee=currentUser() AND status!=Done" --max-results 30
python3 scripts/jira_api.py search "project=PROJ AND created >= -7d ORDER BY created DESC"
python3 scripts/jira_api.py search "summary ~ 'login bug' AND priority=High"
```

Common JQL patterns for developers:

| JQL | Purpose |
|-----|---------|
| `assignee=currentUser()` | My issues |
| `assignee=currentUser() AND status!='Done'` | My open issues |
| `project=PROJ AND sprint in openSprints()` | Current sprint issues |
| `project=PROJ AND status='In Progress'` | In-progress work |
| `project=PROJ AND created >= -7d` | Created in last 7 days |
| `project=PROJ AND updated >= -1d` | Updated in last 24 hours |
| `project=PROJ AND type=Bug AND priority=High` | High priority bugs |
| `summary ~ 'keyword'` | Search in summary |
| `text ~ 'keyword'` | Full text search |

### Create an issue

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/jira_api.py create --project PROJ --summary "Fix login timeout" --type Bug
python3 scripts/jira_api.py create --project PROJ --summary "Add export feature" --type Story \
  --description "Users should be able to export data as CSV" \
  --priority High --labels feature backend --parent PROJ-100
```

| Flag | Required | Description |
|------|----------|-------------|
| `--project` | Yes | Project key |
| `--summary` | Yes | Issue summary |
| `--type` | No | Issue type (default: Task) |
| `--description` | No | Description text |
| `--priority` | No | Priority name (High, Medium, Low, etc.) |
| `--assignee` | No | Assignee account ID (use `myself` command to get yours) |
| `--labels` | No | Space-separated labels |
| `--parent` | No | Parent issue key (for subtasks / stories under epic) |
| `--components` | No | Space-separated component names |

### Edit an issue

```bash
python3 scripts/jira_api.py edit PROJ-123 --summary "Updated summary" --priority High
python3 scripts/jira_api.py edit "https://yoursite.atlassian.net/browse/PROJ-123" --labels urgent backend
```

### Assign an issue

```bash
python3 scripts/jira_api.py assign PROJ-123 5b10ac8d82e05b22cc7d4ef5
python3 scripts/jira_api.py assign PROJ-123 none    # unassign
```

### Transition (move) an issue

Two-step process: list available transitions, then apply one.

```bash
python3 scripts/jira_api.py transitions PROJ-123
python3 scripts/jira_api.py transition PROJ-123 31
python3 scripts/jira_api.py transition PROJ-123 31 --comment "Starting work on this"
python3 scripts/jira_api.py transition PROJ-123 41 --resolution Fixed
```

### Comment on an issue

```bash
python3 scripts/jira_api.py comment PROJ-123 "Investigating the root cause now."
```

### List comments

```bash
python3 scripts/jira_api.py comments PROJ-123
python3 scripts/jira_api.py comments PROJ-123 --max-results 5
```

### Link two issues

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/jira_api.py link PROJ-123 PROJ-456 Blocks
```

### Current user info

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/jira_api.py myself
```

### List boards / sprints / sprint issues

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/jira_api.py boards --project PROJ
python3 scripts/jira_api.py sprints 42 --state active
python3 scripts/jira_api.py sprint-issues 123
```

## Using the Output

The script outputs structured markdown. When the user asks to "view" or "see" a ticket, run the `view` command and present the output. For search results, the output is a summary table — if the user wants more detail on a specific issue, follow up with `view`.

For write operations (create, edit, transition, comment), the script prints a confirmation with the issue key and URL.

## API Reference

For advanced use cases or when the bundled script doesn't cover an operation, see `API_REFERENCE.md` in this skill directory for the full Jira REST API endpoint reference.

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (issue key, status, assignee, key metadata)
3. If a write operation succeeded, include the issue key and URL
4. If operation fails, include exact error and recommended fix
5. If images were downloaded and analyzed, include an **Image Evidence Summary** (source URL, what was observed, confidence/limits)

# Error Handling

- **Missing ATLASSIAN_API_TOKEN**: The script reports the missing variable and how to set it.
- **Missing ATLASSIAN_BASE_URL**: Only required for non-URL commands. The script suggests passing a full URL instead.
- **401 Unauthorized**: Token is invalid or expired — regenerate at https://id.atlassian.com/manage-profile/security/api-tokens
- **403 Forbidden**: User lacks permission for this operation in the target project.
- **404 Not Found**: Issue key or project doesn't exist — verify the key format (e.g. `PROJ-123`).
- **400 Bad Request**: Check field names, issue types, and transition IDs are valid for this project.
- **Image download failed**: report URL + exact HTTP/auth error; retry with enterprise SSO (`curl --negotiate -u :`) when applicable.

# Notes

- The script uses only Python standard library — no `pip install` needed.
- Issue commands accept both `PROJ-123` and full Jira URLs (`https://.../browse/PROJ-123`).
- When the user pastes a Jira URL, prefer passing it directly to the script (URL-first).
- For destructive actions, confirm intent before executing.
