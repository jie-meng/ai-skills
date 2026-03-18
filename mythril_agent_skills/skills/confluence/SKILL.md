---
name: confluence
description: >
  Use the Confluence REST API (via a bundled Python script) for common Confluence
  workflows from terminal. Trigger whenever the user asks to view, search, create,
  edit, or delete Confluence pages, list spaces, add comments or labels, or says
  phrases like "confluence page", "wiki page", "看 wiki", "看 confluence",
  "confluence 页面", "search confluence", "create wiki page", "update confluence",
  "confluence space", "wiki 空间". Also trigger when the user pastes a Confluence
  URL and wants to interact with it. No third-party CLI tools required — only
  Python 3.10+ standard library.
license: Apache-2.0
---

# When to Use This Skill

- A user pastes a Confluence page URL and wants to view or edit it
- Page operations: view, search, create, update, delete
- Space operations: list spaces
- Comment operations: list comments, add comment
- Label operations: list labels, add labels
- Child page listing
- Any request mentioning Confluence pages, wiki, or spaces

# Prerequisites

Requires `ATLASSIAN_API_TOKEN` and `ATLASSIAN_USER_EMAIL`. See `README.md` in this skill directory for setup.

- `ATLASSIAN_API_TOKEN` (**required**) — API token or Personal Access Token
- `ATLASSIAN_USER_EMAIL` (**required for Confluence Cloud**) — Atlassian account email, used for Basic auth
- `ATLASSIAN_BASE_URL` (optional) — e.g. `https://yoursite.atlassian.net`. Not needed when passing full Confluence URLs.

When `ATLASSIAN_BASE_URL` is not set, page commands accept a full Confluence URL instead of a page ID. For commands without a specific page (search, spaces, pages, create), `ATLASSIAN_BASE_URL` is required.

These environment variables are shared with the Jira skill.

## Runtime requirements

- Python 3.10+ for `scripts/confluence_api.py`
- Optional: `curl` for downloading linked screenshots/images when visual evidence is relevant

# Workflow

1. Determine what the user wants (view, search, create, update, etc.)
2. Run the appropriate script command
3. Read the markdown output and present it to the user
4. For write operations, confirm success and show the resulting URL

## Image handling

When a viewed page, comments, or search result contains screenshots or image links, proactively retrieve and analyze them:

Detect image links: Markdown syntax `![alt](url)`, plain URLs ending in `.png/.jpg/.jpeg/.gif/.webp/.svg`, and Confluence attachment paths (`/attachments/`, `/download/attachments/`).

Download under the unified cache.

**Bash (macOS / Linux):**
```bash
CACHE_DIR="$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/confluence"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
IMAGE_CACHE="$RUN_DIR/images"
mkdir -p "$IMAGE_CACHE"
```

**PowerShell (Windows):**
```powershell
$CACHE_DIR = Join-Path ([IO.Path]::GetFullPath([IO.Path]::GetTempPath())) "mythril-skills-cache/confluence"
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

### View a page

Accepts either a page ID or a full Confluence URL:

```bash
# With ATLASSIAN_BASE_URL set
python3 scripts/confluence_api.py view 12345

# Without ATLASSIAN_BASE_URL — pass the full URL directly
python3 scripts/confluence_api.py view "https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345/Page+Title"

# Include labels
python3 scripts/confluence_api.py view 12345 --include-labels
```

When the user pastes a Confluence URL, pass it directly — the script parses out the base URL and page ID automatically.

### Search content via CQL

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/confluence_api.py search "space=TEAM AND type=page"
python3 scripts/confluence_api.py search "text ~ 'deployment guide'" --limit 10
python3 scripts/confluence_api.py search "type=page AND lastModified >= now('-7d')"
python3 scripts/confluence_api.py search "label = 'architecture' AND type=page"
```

Common CQL patterns:

| CQL | Purpose |
|-----|---------|
| `space=TEAM AND type=page` | All pages in a space |
| `type=page AND lastModified >= now('-7d')` | Pages modified in last 7 days |
| `text ~ 'keyword'` | Full text search |
| `title = 'Page Title'` | Exact title match |
| `title ~ 'partial'` | Title contains text |
| `label = 'my-label' AND type=page` | Pages with a specific label |
| `creator = currentUser() AND type=page` | Pages I created |
| `space=TEAM AND ancestor = 12345` | Pages under a specific parent |

### List spaces

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/confluence_api.py spaces
python3 scripts/confluence_api.py spaces --type global
python3 scripts/confluence_api.py spaces --limit 50
```

### List pages

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/confluence_api.py pages --space-id 12345
python3 scripts/confluence_api.py pages --title "Meeting Notes"
python3 scripts/confluence_api.py pages --limit 50
```

### Create a page

Requires `ATLASSIAN_BASE_URL`.

```bash
python3 scripts/confluence_api.py create --space-id 12345 --title "New Page"
python3 scripts/confluence_api.py create --space-id 12345 --title "Design Doc" \
  --body "<h2>Overview</h2><p>This document describes...</p>" \
  --parent-id 67890
```

| Flag | Required | Description |
|------|----------|-------------|
| `--space-id` | Yes | Space ID (use `spaces` command to find) |
| `--title` | Yes | Page title |
| `--body` | No | Body in Confluence storage format (HTML) |
| `--parent-id` | No | Parent page ID |

### Update a page

```bash
python3 scripts/confluence_api.py update 12345 --title "Updated Title"
python3 scripts/confluence_api.py update 12345 --body "<p>New content here</p>" --version-message "Fixed typo"
python3 scripts/confluence_api.py update "https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345" --title "New Title"
```

The script automatically handles version numbering — it fetches the current version and increments it.

### Delete a page

```bash
python3 scripts/confluence_api.py delete 12345
python3 scripts/confluence_api.py delete 12345 --purge  # permanently delete
```

### List comments on a page

```bash
python3 scripts/confluence_api.py comments 12345
python3 scripts/confluence_api.py comments 12345 --limit 10
```

### Add a comment to a page

```bash
python3 scripts/confluence_api.py comment 12345 "This looks good, ship it!"
```

### List labels on a page

```bash
python3 scripts/confluence_api.py labels 12345
```

### Add labels to a page

```bash
python3 scripts/confluence_api.py add-label 12345 architecture backend
```

### List child pages

```bash
python3 scripts/confluence_api.py children 12345
```

## Using the Output

The script outputs structured markdown. When the user asks to "view" or "read" a page, run the `view` command and present the output. For search results, the output is a summary table — if the user wants more detail on a specific page, follow up with `view`.

For write operations (create, update, delete, comment), the script prints a confirmation with the page ID and URL.

## API Reference

For advanced use cases or when the bundled script doesn't cover an operation, see `API_REFERENCE.md` in this skill directory for the full Confluence REST API endpoint reference.

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (page title, ID, space, key metadata)
3. If a write operation succeeded, include the page ID and URL
4. If operation fails, include exact error and recommended fix
5. If images were downloaded and analyzed, include an **Image Evidence Summary** (source URL, what was observed, confidence/limits)

# Error Handling

- **Missing ATLASSIAN_API_TOKEN**: The script reports the missing variable and how to set it.
- **Missing ATLASSIAN_BASE_URL**: Only required for non-URL commands. The script suggests passing a full URL instead.
- **401 Unauthorized**: Token is invalid or expired — regenerate at https://id.atlassian.com/manage-profile/security/api-tokens
- **403 Forbidden**: User lacks permission for this operation in the target space.
- **404 Not Found**: Page or space doesn't exist — verify the page ID or space ID.
- **400 Bad Request**: Check field names, CQL syntax, and body format.
- **Image download failed**: report URL + exact HTTP/auth error; retry with enterprise SSO (`curl --negotiate -u :`) when applicable.

# Notes

- The script uses only Python standard library — no `pip install` needed.
- Page commands accept both numeric page IDs and full Confluence URLs.
- When the user pastes a Confluence URL, prefer passing it directly to the script (URL-first).
- For destructive actions (delete, purge), confirm intent before executing.
- Page body uses Confluence storage format (HTML-like). For simple text, wrap in `<p>` tags.
- Shares the same `ATLASSIAN_API_TOKEN` and `ATLASSIAN_USER_EMAIL` as the Jira skill.
