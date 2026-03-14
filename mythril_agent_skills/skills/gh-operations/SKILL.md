---
name: gh-operations
description: >
  Use GitHub CLI (`gh`) for common GitHub workflows from terminal. Trigger whenever
  the user asks to read/write issues, view pull requests, create PRs, read commit
  details, or says phrases like "use gh", "gh issue", "gh pr", "创建PR", "看PR",
  "读 commit". Prefer `gh` commands (including `gh api` when needed), return clear
  action summaries, and handle auth/repo/permission errors explicitly. When users
  provide full issue/PR URLs, pass the URL directly to `gh` (URL-first) instead
  of rewriting into issue/PR number plus repo flags.
---

# When to Use This Skill

Use this skill whenever the user wants GitHub operations through `gh`, especially:

- Issue operations: list, read, create, edit, comment, close, reopen
- PR operations: list, inspect, review context, create PR
- Commit operations: read commit details, changed files, and commit history
- Requests mentioning `gh`, GitHub CLI, or command-line GitHub workflows

# Workflow

## 1) Pre-flight checks

1. Verify `gh` exists:
   ```bash
   gh --version
   ```
2. Verify authentication:
   ```bash
   gh auth status
   ```
3. If not authenticated, run:
   ```bash
   gh auth login
   ```
4. Confirm target repository:
    - If working in a repo directory, use current repo context.
    - If user provides a full GitHub URL, keep that URL as the primary identifier.
    - Do **not** rewrite URL input into `<number> --repo ...` for read operations.
    - Otherwise require `--repo OWNER/REPO`.
    - To print resolved repo:
      ```bash
      gh repo view --json nameWithOwner -q .nameWithOwner
      ```

## 2) Issue operations (`gh issue`)

### Read/list issues

```bash
gh issue list --state open --limit 20
gh issue view 123 --comments
gh issue view 123 --json number,title,state,author,assignees,labels,body,url,comments
gh issue view "https://github.com/OWNER/REPO/issues/123" --json number,title,state,author,assignees,labels,body,url,comments
gh issue view "https://<github-host>/OWNER/REPO/issues/123" --json number,title,state,author,assignees,labels,body,url,comments
```

Critical rule:

- If user supplies a full issue URL, prefer passing that URL directly to `gh issue view`.
- Do not rewrite URL input to `<number> --repo ...` for read operations.

### Create/update/comment issues

```bash
gh issue create --title "Bug: login fails" --body "Steps to reproduce..."
gh issue create --title "Feature: add export" --body-file issue.md --label enhancement --assignee "@me"
gh issue edit 123 --title "Updated title" --add-label bug --remove-label "needs-triage"
gh issue comment 123 --body "Investigating this now."
```

### State changes

```bash
gh issue close 123 --comment "Fixed in #456"
gh issue reopen 123 --comment "Reopening due to regression"
```

## 3) Pull request operations (`gh pr`)

### Read/list PRs

```bash
gh pr list --state open --limit 20
gh pr view 456 --comments
gh pr view 456 --json number,title,state,author,baseRefName,headRefName,reviewDecision,commits,files,url
gh pr view "https://github.com/OWNER/REPO/pull/456" --json number,title,state,author,baseRefName,headRefName,reviewDecision,commits,files,url
gh pr view "https://<github-host>/OWNER/REPO/pull/456" --json number,title,state,author,baseRefName,headRefName,reviewDecision,commits,files,url
gh pr diff 456
gh pr checks 456
```

### Create PR

```bash
gh pr create --base main --head feature-branch --title "feat: add export API" --body "Closes #123"
```

Useful variants:

```bash
gh pr create --fill
gh pr create --draft --fill
gh pr create --reviewer monalisa --label enhancement
```

## 4) Commit reading (`gh api` + repo context)

When commit-level details are requested, use `gh api`:

```bash
gh api repos/{owner}/{repo}/commits/<sha>
gh api repos/{owner}/{repo}/commits/<sha> --jq '{sha: .sha, author: .commit.author.name, date: .commit.author.date, message: .commit.message, files: [.files[].filename]}'
```

List recent commits:

```bash
gh api repos/{owner}/{repo}/commits -f per_page=20 --jq '.[] | {sha: .sha, message: .commit.message}'
```

# Output Expectations

For every task, provide:

1. Commands executed (or planned) in code blocks
2. Short result summary (issue/PR number, URL, state, key metadata)
3. If write operation succeeded, include created/updated URL explicitly
4. If operation fails, include exact error and next action

# Error Handling

- **Not logged in**: run `gh auth login`, then retry.
- **Wrong host / enterprise**: use `gh auth login --hostname <host-from-url>`, then rerun the same URL command unchanged.
- **Repo not found from URL request**: this usually means URL was rewritten incorrectly; retry using the original URL directly.
- **Permission/scope issues**: show failing command and required scope, e.g. `gh auth refresh -s project`.
- **No repo context**: require `--repo OWNER/REPO` or switch to repository directory.
- **Invalid issue/PR reference**: verify number/URL/repo before retrying.

# Notes

- Prefer URL-first reads (`gh issue view "<url>"`, `gh pr view "<url>"`) to stay host-agnostic.
- Prefer non-interactive flags (`--title`, `--body`, `--json`, `--jq`) for reproducible results.
- For destructive actions (delete/force operations), explicitly confirm intent before executing.
