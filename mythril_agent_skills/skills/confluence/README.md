# Confluence Skill

This skill helps AI assistants interact with Confluence using the REST API for common developer workflows:

- View, search, and list pages via CQL
- Create, update, and delete pages
- Add comments and labels
- List spaces and child pages

No third-party CLI tools required — uses only the Confluence REST API via a bundled Python script (Python 3.10+ standard library, zero dependencies).

**Confluence REST API docs**: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/

**Full API reference**: See [`API_REFERENCE.md`](./API_REFERENCE.md) in this directory.

## Prerequisites

### 1. Get an Atlassian API Token

1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**, give it a label, and copy the token

### 2. Set Environment Variables

Add to your shell config (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export ATLASSIAN_API_TOKEN="your-api-token"
export ATLASSIAN_USER_EMAIL="you@example.com"
```

Optionally, set the base URL to avoid passing full URLs every time:

```bash
export ATLASSIAN_BASE_URL="https://yoursite.atlassian.net"  # optional
```

These variables are shared with the Jira skill. If you already have them configured for Jira, no additional setup is needed.

Reload your shell or run `source ~/.zshrc`.

### 3. Verify Setup

```bash
# With ATLASSIAN_BASE_URL set
python3 scripts/confluence_api.py spaces

# Without ATLASSIAN_BASE_URL — pass a full URL
python3 scripts/confluence_api.py view "https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345"
```

## Usage

Page commands accept either a page ID or a full Confluence URL:

```bash
# Both work
python3 scripts/confluence_api.py view 12345
python3 scripts/confluence_api.py view "https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345"

# Search (requires ATLASSIAN_BASE_URL)
python3 scripts/confluence_api.py search "text ~ 'deployment' AND type=page"

# List spaces (requires ATLASSIAN_BASE_URL)
python3 scripts/confluence_api.py spaces

# Create (requires ATLASSIAN_BASE_URL)
python3 scripts/confluence_api.py create --space-id 12345 --title "New Doc" --body "<p>Hello</p>"

# Update
python3 scripts/confluence_api.py update 12345 --body "<p>Updated content</p>" --version-message "Revised"

# Comment
python3 scripts/confluence_api.py comment 12345 "Looks good!"

# Labels
python3 scripts/confluence_api.py labels 12345
python3 scripts/confluence_api.py add-label 12345 architecture backend

# Child pages
python3 scripts/confluence_api.py children 12345
```

Run `python3 scripts/confluence_api.py --help` for all available commands.
