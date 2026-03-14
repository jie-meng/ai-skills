#!/usr/bin/env python3
"""Jira REST API client for common developer workflows.

Required environment variables:
  ATLASSIAN_API_TOKEN  — API token or Personal Access Token
  ATLASSIAN_USER_EMAIL — Atlassian account email (for Jira Cloud basic auth)

Optional:
  ATLASSIAN_BASE_URL — e.g. https://yoursite.atlassian.net
                       Not needed when passing a full Jira URL to issue commands.

Uses only Python 3.10+ standard library (zero dependencies).
"""

import os, sys, json, re, argparse, base64
import urllib.request
import urllib.error
from urllib.parse import urlencode, urlparse


def get_token() -> str:
    """Return ATLASSIAN_API_TOKEN from environment."""
    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        print("ERROR: ATLASSIAN_API_TOKEN not set.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Add to your shell config (~/.zshrc, ~/.bashrc, etc.):", file=sys.stderr)
        print('  export ATLASSIAN_API_TOKEN="your-api-token"', file=sys.stderr)
        print('  export ATLASSIAN_USER_EMAIL="you@example.com"', file=sys.stderr)
        print("", file=sys.stderr)
        print("Get token: https://id.atlassian.com/manage-profile/security/api-tokens", file=sys.stderr)
        sys.exit(1)
    return token


def get_base_url() -> str:
    """Return base URL from environment. Exits if not set."""
    base_url = os.environ.get("ATLASSIAN_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        print("ERROR: ATLASSIAN_BASE_URL not set and no Jira URL provided.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Either set the env var:", file=sys.stderr)
        print('  export ATLASSIAN_BASE_URL="https://yoursite.atlassian.net"', file=sys.stderr)
        print("", file=sys.stderr)
        print("Or pass a full Jira URL instead of an issue key:", file=sys.stderr)
        print("  python3 jira_api.py view https://yoursite.atlassian.net/browse/PROJ-123", file=sys.stderr)
        sys.exit(1)
    return base_url


def parse_issue_input(input_str: str) -> tuple[str, str]:
    """Parse an issue key or full Jira URL. Returns (base_url, issue_key).

    Accepts:
      PROJ-123                                          → (from env, PROJ-123)
      https://yoursite.atlassian.net/browse/PROJ-123    → (https://yoursite.atlassian.net, PROJ-123)
      https://yoursite.atlassian.net/jira/browse/PROJ-123 → (https://yoursite.atlassian.net/jira, PROJ-123)
    """
    if input_str.startswith("http://") or input_str.startswith("https://"):
        m = re.search(r"(/browse/|/issues/)([A-Z][A-Z0-9_]+-\d+)", input_str)
        if not m:
            print(f"ERROR: Could not parse issue key from URL: {input_str}", file=sys.stderr)
            sys.exit(2)
        issue_key = m.group(2)
        base_url = input_str[: m.start()]
        return base_url, issue_key

    return get_base_url(), input_str


def _auth_header(token: str) -> str:
    """Build auth header. Uses Basic auth if ATLASSIAN_USER_EMAIL is set, otherwise Bearer."""
    email = os.environ.get("ATLASSIAN_USER_EMAIL", "").strip()
    if email:
        cred = base64.b64encode(f"{email}:{token}".encode()).decode()
        return f"Basic {cred}"
    return f"Bearer {token}"


def jira_request(
    method: str,
    path: str,
    base_url: str,
    token: str,
    data: dict | None = None,
    params: dict | None = None,
) -> dict | list | None:
    """Make an authenticated request to the Jira REST API."""
    url = f"{base_url}/rest/api/3{path}"
    if params:
        url += "?" + urlencode(params)

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", _auth_header(token))
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"ERROR: Jira API {e.code} {method} {path}: {body_text}", file=sys.stderr)
        if e.code in (401, 403) and not os.environ.get("ATLASSIAN_USER_EMAIL", "").strip():
            print("", file=sys.stderr)
            print("HINT: Jira Cloud requires Basic auth. Set ATLASSIAN_USER_EMAIL:", file=sys.stderr)
            print('  export ATLASSIAN_USER_EMAIL="you@example.com"', file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _agile_request(
    base_url: str,
    path: str,
    token: str,
    params: dict | None = None,
) -> dict:
    """Make an authenticated request to the Jira Agile REST API."""
    url = f"{base_url}/rest/agile/1.0{path}"
    if params:
        url += "?" + urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("Authorization", _auth_header(token))
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"ERROR: Jira Agile API {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Formatters — convert API responses to readable markdown
# ---------------------------------------------------------------------------

def format_adf_to_text(node: dict | list | str | None, depth: int = 0) -> str:
    """Best-effort conversion of Atlassian Document Format to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(format_adf_to_text(n, depth) for n in node)
    if not isinstance(node, dict):
        return str(node)

    ntype = node.get("type", "")
    content = node.get("content", [])
    text = node.get("text", "")

    if ntype == "text":
        return text
    if ntype == "hardBreak":
        return "\n"
    if ntype == "paragraph":
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        return inner + "\n"
    if ntype == "heading":
        level = node.get("attrs", {}).get("level", 1)
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        return "#" * level + " " + inner + "\n"
    if ntype == "bulletList":
        items = []
        for item in content:
            item_text = format_adf_to_text(item, depth + 1).strip()
            items.append("  " * depth + "- " + item_text)
        return "\n".join(items) + "\n"
    if ntype == "orderedList":
        items = []
        for i, item in enumerate(content, 1):
            item_text = format_adf_to_text(item, depth + 1).strip()
            items.append("  " * depth + f"{i}. " + item_text)
        return "\n".join(items) + "\n"
    if ntype == "listItem":
        return "".join(format_adf_to_text(c, depth) for c in content)
    if ntype == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        return f"```{lang}\n{inner}```\n"
    if ntype == "blockquote":
        inner = "".join(format_adf_to_text(c, depth) for c in content)
        return "> " + inner.replace("\n", "\n> ") + "\n"
    if ntype == "table":
        rows = []
        for row in content:
            cells = []
            for cell in row.get("content", []):
                cells.append(format_adf_to_text(cell, depth).strip())
            rows.append(" | ".join(cells))
        return "\n".join(rows) + "\n"
    if ntype in ("mediaGroup", "mediaSingle"):
        for c in content:
            if c.get("type") == "media":
                mid = c.get("attrs", {}).get("id", "")
                return f"[media: {mid}]\n"
        return ""
    if ntype == "mention":
        return "@" + node.get("attrs", {}).get("text", "someone")

    inner = "".join(format_adf_to_text(c, depth) for c in content)
    return inner


def format_issue_markdown(issue: dict) -> str:
    """Convert a Jira issue JSON to readable markdown."""
    fields = issue.get("fields", {})
    key = issue.get("key", "")
    lines = [f"## {key}: {fields.get('summary', '(no summary)')}"]
    lines.append("")

    status = fields.get("status", {})
    priority = fields.get("priority", {})
    issuetype = fields.get("issuetype", {})
    assignee = fields.get("assignee") or {}
    reporter = fields.get("reporter") or {}
    labels = fields.get("labels", [])
    components = [c.get("name", "") for c in fields.get("components", [])]
    fix_versions = [v.get("name", "") for v in fields.get("fixVersions", [])]
    created = fields.get("created", "")
    updated = fields.get("updated", "")
    parent = fields.get("parent")
    resolution = fields.get("resolution")

    lines.append(f"- **Status**: {status.get('name', '')}")
    lines.append(f"- **Type**: {issuetype.get('name', '')}")
    lines.append(f"- **Priority**: {priority.get('name', '')}")
    lines.append(f"- **Assignee**: {assignee.get('displayName', 'Unassigned')}")
    lines.append(f"- **Reporter**: {reporter.get('displayName', '')}")
    if labels:
        lines.append(f"- **Labels**: {', '.join(labels)}")
    if components:
        lines.append(f"- **Components**: {', '.join(components)}")
    if fix_versions:
        lines.append(f"- **Fix Versions**: {', '.join(fix_versions)}")
    if parent:
        lines.append(f"- **Parent**: {parent.get('key', '')} — {parent.get('fields', {}).get('summary', '')}")
    if resolution:
        lines.append(f"- **Resolution**: {resolution.get('name', '')}")
    lines.append(f"- **Created**: {created}")
    lines.append(f"- **Updated**: {updated}")

    url = issue.get("self", "")
    if url:
        base = url.split("/rest/")[0]
        lines.append(f"- **URL**: {base}/browse/{key}")

    description = fields.get("description")
    if description:
        lines.append("")
        lines.append("### Description")
        lines.append("")
        lines.append(format_adf_to_text(description).strip())

    subtasks = fields.get("subtasks", [])
    if subtasks:
        lines.append("")
        lines.append("### Subtasks")
        for st in subtasks:
            st_status = st.get("fields", {}).get("status", {}).get("name", "")
            lines.append(f"- {st.get('key', '')}: {st.get('fields', {}).get('summary', '')} [{st_status}]")

    issuelinks = fields.get("issuelinks", [])
    if issuelinks:
        lines.append("")
        lines.append("### Linked Issues")
        for link in issuelinks:
            link_type = link.get("type", {}).get("outward", "")
            target = link.get("outwardIssue") or link.get("inwardIssue") or {}
            if link.get("inwardIssue"):
                link_type = link.get("type", {}).get("inward", "")
            t_key = target.get("key", "")
            t_summary = target.get("fields", {}).get("summary", "")
            lines.append(f"- {link_type} {t_key}: {t_summary}")

    return "\n".join(lines)


def format_search_results_markdown(data: dict) -> str:
    """Format JQL search results as a markdown table."""
    issues = data.get("issues", [])
    total = data.get("total", len(issues))

    lines = [f"## Search Results ({len(issues)} of {total} issues)"]
    lines.append("")

    if not issues:
        lines.append("No issues found.")
        return "\n".join(lines)

    lines.append("| Key | Type | Priority | Status | Assignee | Summary |")
    lines.append("|-----|------|----------|--------|----------|---------|")

    for issue in issues:
        f = issue.get("fields", {})
        key = issue.get("key", "")
        itype = f.get("issuetype", {}).get("name", "")
        priority = f.get("priority", {}).get("name", "")
        status = f.get("status", {}).get("name", "")
        assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")
        summary = f.get("summary", "")
        if len(summary) > 60:
            summary = summary[:57] + "..."
        lines.append(f"| {key} | {itype} | {priority} | {status} | {assignee} | {summary} |")

    return "\n".join(lines)


def format_transitions_markdown(data: dict, issue_key: str) -> str:
    """Format available transitions as a markdown list."""
    transitions = data.get("transitions", [])
    lines = [f"## Available Transitions for {issue_key}"]
    lines.append("")
    if not transitions:
        lines.append("No transitions available.")
        return "\n".join(lines)
    lines.append("| ID | Name | To Status |")
    lines.append("|----|------|-----------|")
    for t in transitions:
        to_status = t.get("to", {}).get("name", "")
        lines.append(f"| {t.get('id', '')} | {t.get('name', '')} | {to_status} |")
    return "\n".join(lines)


def format_comments_markdown(data: dict, issue_key: str) -> str:
    """Format issue comments as markdown."""
    comments = data.get("comments", [])
    total = data.get("total", len(comments))
    lines = [f"## Comments on {issue_key} ({len(comments)} of {total})"]
    lines.append("")
    if not comments:
        lines.append("No comments.")
        return "\n".join(lines)
    for c in comments:
        author = c.get("author", {}).get("displayName", "")
        created = c.get("created", "")
        body = format_adf_to_text(c.get("body")).strip()
        lines.append(f"### {author} — {created}")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def format_sprint_markdown(data: dict) -> str:
    """Format Jira Agile sprint data as markdown."""
    values = data.get("values", [])
    lines = ["## Sprints"]
    lines.append("")
    if not values:
        lines.append("No sprints found.")
        return "\n".join(lines)
    lines.append("| ID | Name | State | Start | End |")
    lines.append("|----|------|-------|-------|-----|")
    for s in values:
        lines.append(
            f"| {s.get('id', '')} | {s.get('name', '')} | {s.get('state', '')} "
            f"| {s.get('startDate', '-')} | {s.get('endDate', '-')} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_view(args: argparse.Namespace) -> None:
    """View a single issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    fields_param = (
        "summary,status,issuetype,priority,assignee,reporter,labels,components,"
        "fixVersions,description,created,updated,parent,subtasks,issuelinks,resolution,comment"
    )
    data = jira_request("GET", f"/issue/{issue_key}", base_url, token,
                        params={"fields": fields_param})
    print(format_issue_markdown(data))


def cmd_search(args: argparse.Namespace) -> None:
    """Search issues via JQL."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {
        "jql": args.jql,
        "maxResults": args.max_results,
        "fields": "summary,status,issuetype,priority,assignee",
    }
    data = jira_request("GET", "/search/jql", base_url, token, params=params)
    print(format_search_results_markdown(data))


def cmd_create(args: argparse.Namespace) -> None:
    """Create a new issue."""
    token = get_token()
    base_url = get_base_url()
    fields: dict = {
        "project": {"key": args.project},
        "summary": args.summary,
        "issuetype": {"name": args.type},
    }
    if args.description:
        fields["description"] = {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.description}]}],
        }
    if args.priority:
        fields["priority"] = {"name": args.priority}
    if args.assignee:
        fields["assignee"] = {"accountId": args.assignee}
    if args.labels:
        fields["labels"] = args.labels
    if args.parent:
        fields["parent"] = {"key": args.parent}
    if args.components:
        fields["components"] = [{"name": c} for c in args.components]

    data = jira_request("POST", "/issue", base_url, token, data={"fields": fields})
    key = data.get("key", "")
    print(f"Created {key}: {base_url}/browse/{key}")


def cmd_edit(args: argparse.Namespace) -> None:
    """Edit an existing issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    fields: dict = {}
    if args.summary:
        fields["summary"] = args.summary
    if args.description:
        fields["description"] = {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.description}]}],
        }
    if args.priority:
        fields["priority"] = {"name": args.priority}
    if args.assignee:
        fields["assignee"] = {"accountId": args.assignee}
    if args.labels is not None:
        fields["labels"] = args.labels

    if not fields:
        print("ERROR: No fields to update. Provide at least one of --summary, --description, --priority, --assignee, --labels.", file=sys.stderr)
        sys.exit(2)

    jira_request("PUT", f"/issue/{issue_key}", base_url, token,
                 data={"fields": fields})
    print(f"Updated {issue_key}: {base_url}/browse/{issue_key}")


def cmd_assign(args: argparse.Namespace) -> None:
    """Assign an issue to a user (by accountId) or unassign with 'none'."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    account_id = None if args.account_id == "none" else args.account_id
    jira_request("PUT", f"/issue/{issue_key}/assignee", base_url, token,
                 data={"accountId": account_id})
    if account_id:
        print(f"Assigned {issue_key} to {account_id}")
    else:
        print(f"Unassigned {issue_key}")


def cmd_transitions(args: argparse.Namespace) -> None:
    """List available transitions for an issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    data = jira_request("GET", f"/issue/{issue_key}/transitions", base_url, token)
    print(format_transitions_markdown(data, issue_key))


def cmd_transition(args: argparse.Namespace) -> None:
    """Transition (move) an issue to a new status."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    payload: dict = {"transition": {"id": args.transition_id}}
    if args.comment:
        payload["update"] = {
            "comment": [{
                "add": {
                    "body": {
                        "version": 1,
                        "type": "doc",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.comment}]}],
                    }
                }
            }]
        }
    if args.resolution:
        payload.setdefault("fields", {})["resolution"] = {"name": args.resolution}

    jira_request("POST", f"/issue/{issue_key}/transitions", base_url, token, data=payload)
    print(f"Transitioned {issue_key} (transition id: {args.transition_id})")


def cmd_comment(args: argparse.Namespace) -> None:
    """Add a comment to an issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    body = {
        "body": {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.body}]}],
        }
    }
    data = jira_request("POST", f"/issue/{issue_key}/comment", base_url, token, data=body)
    print(f"Comment added to {issue_key} (id: {data.get('id', '')})")


def cmd_comments(args: argparse.Namespace) -> None:
    """List comments on an issue."""
    token = get_token()
    base_url, issue_key = parse_issue_input(args.issue)
    params = {"maxResults": args.max_results, "orderBy": "-created"}
    data = jira_request("GET", f"/issue/{issue_key}/comment", base_url, token, params=params)
    print(format_comments_markdown(data, issue_key))


def cmd_myself(args: argparse.Namespace) -> None:
    """Print the authenticated user's info."""
    token = get_token()
    base_url = get_base_url()
    data = jira_request("GET", "/myself", base_url, token)
    print(f"Account ID: {data.get('accountId', '')}")
    print(f"Display Name: {data.get('displayName', '')}")
    print(f"Email: {data.get('emailAddress', '')}")
    print(f"Active: {data.get('active', '')}")


def cmd_link(args: argparse.Namespace) -> None:
    """Link two issues together."""
    token = get_token()
    base_url = get_base_url()
    body = {
        "type": {"name": args.link_type},
        "inwardIssue": {"key": args.inward_key},
        "outwardIssue": {"key": args.outward_key},
    }
    jira_request("POST", "/issueLink", base_url, token, data=body)
    print(f"Linked {args.outward_key} —[{args.link_type}]→ {args.inward_key}")


def cmd_sprints(args: argparse.Namespace) -> None:
    """List sprints for a board (uses Jira Agile REST API)."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str] = {}
    if args.state:
        params["state"] = args.state
    data = _agile_request(base_url, f"/board/{args.board_id}/sprint", token, params=params or None)
    print(format_sprint_markdown(data))


def cmd_sprint_issues(args: argparse.Namespace) -> None:
    """List issues in a sprint (uses Jira Agile REST API)."""
    token = get_token()
    base_url = get_base_url()
    params = {"maxResults": str(args.max_results), "fields": "summary,status,issuetype,priority,assignee"}
    data = _agile_request(base_url, f"/sprint/{args.sprint_id}/issue", token, params=params)
    print(format_search_results_markdown(data))


def cmd_boards(args: argparse.Namespace) -> None:
    """List boards (uses Jira Agile REST API)."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str] = {"maxResults": str(args.max_results)}
    if args.project:
        params["projectKeyOrId"] = args.project
    data = _agile_request(base_url, "/board", token, params=params)

    values = data.get("values", [])
    lines = ["## Boards"]
    lines.append("")
    if not values:
        lines.append("No boards found.")
    else:
        lines.append("| ID | Name | Type | Project |")
        lines.append("|----|------|------|---------|")
        for b in values:
            loc = b.get("location", {})
            proj = loc.get("projectKey", "") if loc else ""
            lines.append(f"| {b.get('id', '')} | {b.get('name', '')} | {b.get('type', '')} | {proj} |")
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

ISSUE_HELP = "Issue key (e.g. PROJ-123) or full Jira URL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Jira REST API client for developer workflows.")
    sub = parser.add_subparsers(dest="command", required=True)

    # view
    p_view = sub.add_parser("view", help="View a single issue")
    p_view.add_argument("issue", help=ISSUE_HELP)
    p_view.set_defaults(func=cmd_view)

    # search
    p_search = sub.add_parser("search", help="Search issues via JQL")
    p_search.add_argument("jql", help='JQL query string (e.g. "project=PROJ AND status=Open")')
    p_search.add_argument("--max-results", type=int, default=20, help="Max results (default: 20)")
    p_search.set_defaults(func=cmd_search)

    # create
    p_create = sub.add_parser("create", help="Create a new issue")
    p_create.add_argument("--project", required=True, help="Project key (e.g. PROJ)")
    p_create.add_argument("--summary", required=True, help="Issue summary")
    p_create.add_argument("--type", default="Task", help="Issue type (default: Task)")
    p_create.add_argument("--description", help="Description text")
    p_create.add_argument("--priority", help="Priority name (e.g. High)")
    p_create.add_argument("--assignee", help="Assignee account ID")
    p_create.add_argument("--labels", nargs="*", help="Labels")
    p_create.add_argument("--parent", help="Parent issue key (for subtasks/stories under epic)")
    p_create.add_argument("--components", nargs="*", help="Component names")
    p_create.set_defaults(func=cmd_create)

    # edit
    p_edit = sub.add_parser("edit", help="Edit an existing issue")
    p_edit.add_argument("issue", help=ISSUE_HELP)
    p_edit.add_argument("--summary", help="New summary")
    p_edit.add_argument("--description", help="New description")
    p_edit.add_argument("--priority", help="New priority")
    p_edit.add_argument("--assignee", help="New assignee account ID")
    p_edit.add_argument("--labels", nargs="*", help="Replace labels")
    p_edit.set_defaults(func=cmd_edit)

    # assign
    p_assign = sub.add_parser("assign", help="Assign an issue")
    p_assign.add_argument("issue", help=ISSUE_HELP)
    p_assign.add_argument("account_id", help='Assignee account ID or "none" to unassign')
    p_assign.set_defaults(func=cmd_assign)

    # transitions
    p_trans_list = sub.add_parser("transitions", help="List available transitions")
    p_trans_list.add_argument("issue", help=ISSUE_HELP)
    p_trans_list.set_defaults(func=cmd_transitions)

    # transition
    p_trans = sub.add_parser("transition", help="Transition (move) an issue")
    p_trans.add_argument("issue", help=ISSUE_HELP)
    p_trans.add_argument("transition_id", help="Transition ID (from 'transitions' command)")
    p_trans.add_argument("--comment", help="Add a comment during transition")
    p_trans.add_argument("--resolution", help="Set resolution (e.g. Done, Fixed)")
    p_trans.set_defaults(func=cmd_transition)

    # comment
    p_comment = sub.add_parser("comment", help="Add a comment to an issue")
    p_comment.add_argument("issue", help=ISSUE_HELP)
    p_comment.add_argument("body", help="Comment text")
    p_comment.set_defaults(func=cmd_comment)

    # comments
    p_comments = sub.add_parser("comments", help="List comments on an issue")
    p_comments.add_argument("issue", help=ISSUE_HELP)
    p_comments.add_argument("--max-results", type=int, default=10, help="Max results (default: 10)")
    p_comments.set_defaults(func=cmd_comments)

    # link
    p_link = sub.add_parser("link", help="Link two issues")
    p_link.add_argument("outward_key", help="Outward issue key")
    p_link.add_argument("inward_key", help="Inward issue key")
    p_link.add_argument("link_type", help='Link type name (e.g. "Blocks", "Relates")')
    p_link.set_defaults(func=cmd_link)

    # myself
    p_me = sub.add_parser("myself", help="Print current user info")
    p_me.set_defaults(func=cmd_myself)

    # boards
    p_boards = sub.add_parser("boards", help="List boards")
    p_boards.add_argument("--project", help="Filter by project key")
    p_boards.add_argument("--max-results", type=int, default=50, help="Max results (default: 50)")
    p_boards.set_defaults(func=cmd_boards)

    # sprints
    p_sprints = sub.add_parser("sprints", help="List sprints for a board")
    p_sprints.add_argument("board_id", help="Board ID")
    p_sprints.add_argument("--state", help='Filter by state: active, closed, future (comma-separated)')
    p_sprints.set_defaults(func=cmd_sprints)

    # sprint-issues
    p_si = sub.add_parser("sprint-issues", help="List issues in a sprint")
    p_si.add_argument("sprint_id", help="Sprint ID")
    p_si.add_argument("--max-results", type=int, default=50, help="Max results (default: 50)")
    p_si.set_defaults(func=cmd_sprint_issues)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
