# Installation & Configuration Guide

This guide is designed for both humans and AI agents. An agent reading this file should:

1. Check which environment variables are already configured
2. For any missing variables, explain how to obtain the credentials
3. Prompt the user to provide the values
4. Write them to the user's shell config file
5. Print a summary of all configured variables so the user knows where to find and update them

---

## Step 1: Detect Shell Config File

Determine the user's shell and config file path:

```bash
echo "$SHELL"
```

| Shell | Config file |
|-------|------------|
| `/bin/zsh` or `/usr/bin/zsh` | `~/.zshrc` |
| `/bin/bash` or `/usr/bin/bash` | `~/.bashrc` (or `~/.bash_profile` on macOS if `~/.bashrc` is not sourced) |
| `/bin/fish` | `~/.config/fish/config.fish` |

Use the detected config file for all `export` commands below.

---

## Step 2: Check and Configure Environment Variables

Check each variable. If already set, print its current value (masked for tokens). If missing, guide the user through obtaining and setting it.

### 2.1 GitHub CLI (`gh`)

**Required by**: [gh-operations](../skills/gh-operations/)

Check:

```bash
gh --version 2>/dev/null && gh auth status 2>/dev/null
```

If `gh` is not installed:

- **macOS**: `brew install gh`
- **Windows**: `winget install --id GitHub.cli`
- **Linux (Ubuntu/Debian)**:
  ```bash
  (type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
    && sudo mkdir -p -m 755 /etc/apt/keyrings \
    && out=$(mktemp) && wget -nv -O"$out" https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    && cat "$out" | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && sudo mkdir -p -m 755 /etc/apt/sources.list.d \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
       | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
    && sudo apt update \
    && sudo apt install gh -y
  ```

If `gh` is installed but not authenticated, run:

```bash
gh auth login
```

For GitHub Enterprise hosts:

```bash
gh auth login --hostname <your-ghe-host>
```

**Permissions needed**: Default scopes from `gh auth login` are sufficient for issue/PR/commit operations. If the user needs project board access, run `gh auth refresh -s project`.

---

### 2.2 Jira (`JIRA_API_TOKEN`, `JIRA_USER_EMAIL`, `JIRA_BASE_URL`)

**Required by**: [jira](../skills/jira/)

No CLI tool needed — uses a bundled Python script (Python 3.10+ standard library only).

Check:

```bash
echo "JIRA_API_TOKEN: $([ -n "$JIRA_API_TOKEN" ] && echo 'set' || echo 'NOT SET')"
echo "JIRA_USER_EMAIL: $([ -n "$JIRA_USER_EMAIL" ] && echo "$JIRA_USER_EMAIL" || echo 'NOT SET')"
echo "JIRA_BASE_URL: $([ -n "$JIRA_BASE_URL" ] && echo "$JIRA_BASE_URL" || echo 'NOT SET')"
```

#### `JIRA_API_TOKEN` (required)

If not set, instruct the user:

1. Open https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Enter a label (e.g. `ai-skills`)
4. Click **Create**, then **Copy** the generated token

**Permissions**: The token inherits the user's Jira permissions — no separate scope configuration needed. The user must have at least **Browse Projects** permission on the projects they want to access.

Once the user provides the token, append to their shell config:

```bash
export JIRA_API_TOKEN="<token>"
```

#### `JIRA_USER_EMAIL` (required for Jira Cloud)

This is the email address associated with the user's Atlassian account. It is used together with the API token for Basic auth (which Jira Cloud requires).

Ask the user for their Atlassian account email and append:

```bash
export JIRA_USER_EMAIL="<email>"
```

For Jira Server/DC 8.14+ using Personal Access Tokens, this variable is not needed — Bearer auth is used automatically when `JIRA_USER_EMAIL` is not set.

#### `JIRA_BASE_URL` (optional but recommended)

The base URL of the user's Jira instance (e.g. `https://yourcompany.atlassian.net`). Without this, the user must pass full Jira URLs (e.g. `https://yourcompany.atlassian.net/browse/PROJ-123`) to every command. With it set, they can use just the issue key (e.g. `PROJ-123`).

Ask the user for their Jira instance URL and append:

```bash
export JIRA_BASE_URL="<url>"
```

#### Verify

```bash
python3 <path-to-skills>/jira/scripts/jira_api.py myself
```

---

### 2.3 Figma (`FIGMA_ACCESS_TOKEN`)

**Required by**: [figma](../skills/figma/)

No CLI tool needed — uses a bundled Python script (Python 3.8+ standard library only).

Check:

```bash
echo "FIGMA_ACCESS_TOKEN: $([ -n "$FIGMA_ACCESS_TOKEN" ] && echo 'set' || echo 'NOT SET')"
```

#### `FIGMA_ACCESS_TOKEN` (required)

If not set, instruct the user:

1. Open https://www.figma.com/settings
2. Scroll to the **Security** section
3. Under **Personal access tokens**, click **"Generate new token"**
4. Enter a description (e.g. `ai-skills`)
5. Under **Expiration**, choose a suitable duration or **No expiration**
6. Under **Scopes**, grant at least **File content → Read only** access
7. Click **Generate token**, then copy the generated token (it is only shown once)

**Permissions**: The token needs read access to the Figma files the user wants to inspect. If the user is in a Figma organization, the token inherits their file access permissions.

Once the user provides the token, append to their shell config:

```bash
export FIGMA_ACCESS_TOKEN="<token>"
```

#### Verify

```bash
python3 <path-to-skills>/figma/scripts/figma_fetch.py "https://www.figma.com/design/<any-file-key>/Name"
```

---

## Step 3: Reload Shell Config

After writing all variables, reload the config:

```bash
source ~/.zshrc   # or ~/.bashrc, depending on detected shell
```

---

## Step 4: Print Summary

After all checks, print a summary like this:

```
=== ai-skills Configuration Summary ===

GitHub CLI (gh):
  Status:   installed, authenticated
  User:     @username
  Config:   gh manages its own auth (run `gh auth status` to inspect)

Jira:
  JIRA_API_TOKEN:   set (token ending in ...xxxx)
  JIRA_USER_EMAIL:  you@example.com
  JIRA_BASE_URL:    https://yourcompany.atlassian.net
  Config file:      ~/.zshrc

Figma:
  FIGMA_ACCESS_TOKEN:  set (token ending in ...xxxx)
  Config file:         ~/.zshrc

All configured. To update any value, edit the corresponding
line in your shell config file and run `source ~/.zshrc`.
```

If any variable is missing, list it clearly as `NOT SET` with a one-line instruction on how to obtain it.
