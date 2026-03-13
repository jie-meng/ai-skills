# GH Operations Skill

This skill helps AI assistants use GitHub CLI (`gh`) for common repository workflows:

- Read/write issues
- View pull requests
- Create pull requests
- Read commit details

Official GitHub CLI repository: https://github.com/cli/cli

GitHub CLI manual: https://cli.github.com/manual

## Install GitHub CLI (`gh`)

### macOS (official)

```bash
brew install gh
```

### Windows (official)

```powershell
winget install --id GitHub.cli
```

### Linux (Ubuntu/Debian official repository)

```bash
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && out=$(mktemp) && wget -nv -O"$out" https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  && cat "$out" | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && sudo mkdir -p -m 755 /etc/apt/sources.list.d \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
  && sudo apt update \
  && sudo apt install gh -y
```

After installation, verify:

```bash
gh --version
```

## Login to GitHub

Run interactive login:

```bash
gh auth login
```

Common options:

- GitHub.com
- HTTPS (or SSH if you prefer)
- Browser-based login (`--web`)

Alternative token login:

```bash
gh auth login --with-token < mytoken.txt
```

Verify login status:

```bash
gh auth status
```

If you need to access a specific GitHub Enterprise host:

```bash
gh auth login --hostname <your-ghe-host>
```

## URL-first usage (recommended)

When a user gives a full issue/PR URL, pass that URL directly to `gh`.
This works for both `github.com` and GitHub Enterprise hosts.

```bash
gh issue view "https://github.com/OWNER/REPO/issues/123" \
  --json number,title,state,author,assignees,labels,body,url,comments

gh issue view "https://<github-host>/OWNER/REPO/issues/123" \
  --json number,title,state,author,assignees,labels,body,url,comments

gh pr view "https://github.com/OWNER/REPO/pull/456" \
  --json number,title,state,author,baseRefName,headRefName,reviewDecision,commits,files,url
```

Avoid rewriting URL input into `issue/pr number + --repo + --hostname` for read operations.
If auth fails on the URL's host, run `gh auth login --hostname <host>` and rerun the same URL command.