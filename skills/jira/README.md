# Jira Skill

This skill helps AI assistants interact with Jira using the REST API for common developer workflows:

- View, search, and filter issues via JQL
- Create, edit, assign, and transition issues
- Comment on and link issues
- List boards, sprints, and sprint issues

No third-party CLI tools required — uses only the Jira REST API via a bundled Python script (Python 3.10+ standard library, zero dependencies).

**Jira REST API docs**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/

**Full API reference**: See [`API_REFERENCE.md`](./API_REFERENCE.md) in this directory.

## Prerequisites

### 1. Get a Jira API Token

1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**, give it a label, and copy the token

### 2. Set Environment Variables

Add to your shell config (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export JIRA_API_TOKEN="your-api-token"
export JIRA_USER_EMAIL="you@example.com"
```

Optionally, set the base URL to avoid passing full URLs every time:

```bash
export JIRA_BASE_URL="https://yoursite.atlassian.net"  # optional
```

For Jira Server/DC 8.14+ with PAT, only `JIRA_API_TOKEN` is needed (Bearer auth is used when `JIRA_USER_EMAIL` is not set).

Reload your shell or run `source ~/.zshrc`.

### 3. Verify Setup

```bash
# With JIRA_BASE_URL set
python3 scripts/jira_api.py myself

# Without JIRA_BASE_URL — pass a full URL
python3 scripts/jira_api.py view "https://yoursite.atlassian.net/browse/PROJ-123"
```

## Usage

Issue commands accept either an issue key or a full Jira URL:

```bash
# Both work
python3 scripts/jira_api.py view PROJ-123
python3 scripts/jira_api.py view "https://yoursite.atlassian.net/browse/PROJ-123"

# Search (requires JIRA_BASE_URL)
python3 scripts/jira_api.py search "assignee=currentUser() AND status!='Done'"

# Create (requires JIRA_BASE_URL)
python3 scripts/jira_api.py create --project PROJ --summary "Fix bug" --type Bug --priority High

# Transition
python3 scripts/jira_api.py transitions PROJ-123
python3 scripts/jira_api.py transition PROJ-123 31

# Comment
python3 scripts/jira_api.py comment PROJ-123 "Working on it"

# Boards & sprints (requires JIRA_BASE_URL)
python3 scripts/jira_api.py boards --project PROJ
python3 scripts/jira_api.py sprints 42 --state active
python3 scripts/jira_api.py sprint-issues 123
```

Run `python3 scripts/jira_api.py --help` for all available commands.

## Install this skill in your AI assistant

From repository root:

```bash
./scripts/setup .copilot
```

or:

```bash
./scripts/setup .claude
./scripts/setup .cursor
```
