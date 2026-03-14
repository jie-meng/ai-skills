# Installation & Configuration Guide

## Automatic Setup (Recommended)

Run the interactive dependency checker — it will detect missing tools, install them, and prompt for API keys:

```bash
skills-check gh-operations jira figma
```

The checker handles everything described in this document automatically.

---

## Manual Setup Reference

This section documents all dependencies for reference. An AI agent reading this file should use `skills-check` instead of following these steps manually.

### Detect Shell Config File

```bash
echo "$SHELL"
```

| Shell | Config file |
|-------|------------|
| `/bin/zsh` or `/usr/bin/zsh` | `~/.zshrc` |
| `/bin/bash` or `/usr/bin/bash` | `~/.bashrc` (or `~/.bash_profile` on macOS if `~/.bashrc` is not sourced) |
| `/bin/fish` | `~/.config/fish/config.fish` |

---

### GitHub CLI (`gh`)

**Required by**: [gh-operations](../mythril_agent_skills/skills/gh-operations/)

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

If `gh` is installed but not authenticated:

```bash
gh auth login
```

For GitHub Enterprise:

```bash
gh auth login --hostname <your-ghe-host>
```

**Permissions**: Default scopes from `gh auth login` are sufficient. For project board access: `gh auth refresh -s project`.

---

### Jira (`JIRA_API_TOKEN`, `JIRA_USER_EMAIL`, `JIRA_BASE_URL`)

**Required by**: [jira](../mythril_agent_skills/skills/jira/)

No CLI tool needed — uses a bundled Python script (Python 3.10+ standard library only).

#### `JIRA_API_TOKEN` (required)

1. Open https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Enter a label (e.g. `ai-skills`), click **Create**, then **Copy**

```bash
export JIRA_API_TOKEN="<token>"
```

#### `JIRA_USER_EMAIL` (required for Jira Cloud)

The email address associated with your Atlassian account:

```bash
export JIRA_USER_EMAIL="<email>"
```

For Jira Server/DC 8.14+ using Personal Access Tokens, this variable is not needed.

#### `JIRA_BASE_URL` (optional but recommended)

```bash
export JIRA_BASE_URL="https://yourcompany.atlassian.net"
```

#### Verify

```bash
python3 <path-to-skills>/jira/scripts/jira_api.py myself
```

---

### Figma (`FIGMA_ACCESS_TOKEN`)

**Required by**: [figma](../mythril_agent_skills/skills/figma/)

No CLI tool needed — uses a bundled Python script (Python 3.8+ standard library only).

1. Open https://www.figma.com/settings
2. Under **Personal access tokens**, click **"Generate new token"**
3. Grant at least **File content → Read only** access
4. Copy the token (shown only once)

```bash
export FIGMA_ACCESS_TOKEN="<token>"
```

#### Verify

```bash
python3 <path-to-skills>/figma/scripts/figma_fetch.py "https://www.figma.com/design/<file-key>/Name"
```

---

### Reload Shell Config

After setting variables, reload:

```bash
source ~/.zshrc   # or ~/.bashrc, depending on your shell
```
