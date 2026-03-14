#!/usr/bin/env python3
"""Confluence REST API client for common developer workflows.

Required environment variables:
  ATLASSIAN_API_TOKEN  — API token or Personal Access Token
  ATLASSIAN_USER_EMAIL — Atlassian account email (for Cloud basic auth)

Optional:
  ATLASSIAN_BASE_URL — e.g. https://yoursite.atlassian.net
                       Not needed when passing a full Confluence URL to page commands.

Uses only Python 3.10+ standard library (zero dependencies).
"""

import os, sys, json, re, argparse, base64, html
import urllib.request
import urllib.error
from urllib.parse import urlencode, urlparse, quote


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
        print("ERROR: ATLASSIAN_BASE_URL not set and no Confluence URL provided.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Either set the env var:", file=sys.stderr)
        print('  export ATLASSIAN_BASE_URL="https://yoursite.atlassian.net"', file=sys.stderr)
        print("", file=sys.stderr)
        print("Or pass a full Confluence URL instead of a page ID:", file=sys.stderr)
        print("  python3 confluence_api.py view https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345", file=sys.stderr)
        sys.exit(1)
    return base_url


def parse_page_input(input_str: str) -> tuple[str, str]:
    """Parse a page ID or full Confluence URL. Returns (base_url, page_id).

    Accepts:
      12345                                                              → (from env, 12345)
      https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345        → (https://yoursite.atlassian.net, 12345)
      https://yoursite.atlassian.net/wiki/spaces/TEAM/pages/12345/Title  → (https://yoursite.atlassian.net, 12345)
    """
    if input_str.startswith("http://") or input_str.startswith("https://"):
        m = re.search(r"/pages/(\d+)", input_str)
        if not m:
            print(f"ERROR: Could not parse page ID from URL: {input_str}", file=sys.stderr)
            sys.exit(2)
        page_id = m.group(1)
        parsed = urlparse(input_str)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        return base_url, page_id

    return get_base_url(), input_str


def _auth_header(token: str) -> str:
    """Build auth header. Uses Basic auth if ATLASSIAN_USER_EMAIL is set, otherwise Bearer."""
    email = os.environ.get("ATLASSIAN_USER_EMAIL", "").strip()
    if email:
        cred = base64.b64encode(f"{email}:{token}".encode()).decode()
        return f"Basic {cred}"
    return f"Bearer {token}"


def confluence_request(
    method: str,
    path: str,
    base_url: str,
    token: str,
    data: dict | None = None,
    params: dict | None = None,
    api_prefix: str = "/wiki/api/v2",
) -> dict | list | None:
    """Make an authenticated request to the Confluence REST API."""
    url = f"{base_url}{api_prefix}{path}"
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
        print(f"ERROR: Confluence API {e.code} {method} {path}: {body_text}", file=sys.stderr)
        if e.code in (401, 403) and not os.environ.get("ATLASSIAN_USER_EMAIL", "").strip():
            print("", file=sys.stderr)
            print("HINT: Confluence Cloud requires Basic auth. Set ATLASSIAN_USER_EMAIL:", file=sys.stderr)
            print('  export ATLASSIAN_USER_EMAIL="you@example.com"', file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Formatters — convert API responses to readable markdown
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Minimal HTML-to-text conversion for Confluence storage format."""
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: "#" * int(m.group(1)) + " " + m.group(2) + "\n", text)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", text, flags=re.DOTALL)
    text = re.sub(r"<ac:structured-macro[^>]*>.*?</ac:structured-macro>", "[macro]", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def format_page_markdown(page: dict, base_url: str = "") -> str:
    """Convert a Confluence page JSON to readable markdown."""
    page_id = page.get("id", "")
    title = page.get("title", "(no title)")
    status = page.get("status", "")
    space_id = page.get("spaceId", "")
    author_id = page.get("authorId", "")
    created = page.get("createdAt", "")
    version = page.get("version", {})
    version_num = version.get("number", "")
    version_date = version.get("createdAt", "")
    version_msg = version.get("message", "")

    lines = [f"## {title}"]
    lines.append("")
    lines.append(f"- **Page ID**: {page_id}")
    lines.append(f"- **Space ID**: {space_id}")
    lines.append(f"- **Status**: {status}")
    lines.append(f"- **Version**: {version_num}")
    if version_msg:
        lines.append(f"- **Version Message**: {version_msg}")
    lines.append(f"- **Author**: {author_id}")
    lines.append(f"- **Created**: {created}")
    lines.append(f"- **Last Updated**: {version_date}")

    parent_id = page.get("parentId")
    if parent_id:
        lines.append(f"- **Parent Page ID**: {parent_id}")

    links = page.get("_links", {})
    webui = links.get("webui", "")
    link_base = links.get("base", base_url)
    if webui and link_base:
        lines.append(f"- **URL**: {link_base}{webui}")

    body = page.get("body", {})
    storage = body.get("storage", {})
    if isinstance(storage, dict) and storage.get("value"):
        lines.append("")
        lines.append("### Content")
        lines.append("")
        lines.append(_strip_html(storage["value"]))

    labels = page.get("labels", {})
    if isinstance(labels, dict):
        label_results = labels.get("results", [])
        if label_results:
            names = [lb.get("name", "") for lb in label_results]
            lines.append(f"- **Labels**: {', '.join(names)}")

    return "\n".join(lines)


def format_pages_table(results: list[dict], total_label: str = "") -> str:
    """Format a list of pages as a markdown table."""
    header = total_label or f"{len(results)} pages"
    lines = [f"## {header}"]
    lines.append("")

    if not results:
        lines.append("No pages found.")
        return "\n".join(lines)

    lines.append("| ID | Title | Space ID | Status | Version | Updated |")
    lines.append("|----|-------|----------|--------|---------|---------|")

    for p in results:
        pid = p.get("id", "")
        title = p.get("title", "")
        if len(title) > 50:
            title = title[:47] + "..."
        space_id = p.get("spaceId", "")
        status = p.get("status", "")
        ver = p.get("version", {})
        ver_num = ver.get("number", "")
        ver_date = ver.get("createdAt", "")[:10] if ver.get("createdAt") else ""
        lines.append(f"| {pid} | {title} | {space_id} | {status} | {ver_num} | {ver_date} |")

    return "\n".join(lines)


def format_spaces_table(results: list[dict]) -> str:
    """Format a list of spaces as a markdown table."""
    lines = [f"## Spaces ({len(results)})"]
    lines.append("")

    if not results:
        lines.append("No spaces found.")
        return "\n".join(lines)

    lines.append("| ID | Key | Name | Type | Status |")
    lines.append("|----|-----|------|------|--------|")

    for s in results:
        sid = s.get("id", "")
        key = s.get("key", "")
        name = s.get("name", "")
        if len(name) > 40:
            name = name[:37] + "..."
        stype = s.get("type", "")
        status = s.get("status", "")
        lines.append(f"| {sid} | {key} | {name} | {stype} | {status} |")

    return "\n".join(lines)


def format_search_results(data: dict) -> str:
    """Format CQL search results as markdown."""
    results = data.get("results", [])
    total = data.get("totalSize", len(results))

    lines = [f"## Search Results ({len(results)} of {total})"]
    lines.append("")

    if not results:
        lines.append("No results found.")
        return "\n".join(lines)

    lines.append("| Type | ID | Title | Space | Last Modified |")
    lines.append("|------|----|-------|-------|---------------|")

    for r in results:
        content = r.get("content", {}) or r.get("space", {})
        ctype = content.get("type", r.get("entityType", ""))
        cid = content.get("id", "")
        title = r.get("title", content.get("title", content.get("name", "")))
        title = re.sub(r"@@@[eh]l@@@", "", title)
        if len(title) > 50:
            title = title[:47] + "..."
        space = ""
        if "space" in content:
            space = content["space"].get("key", "")
        elif "_expandable" in content and "space" in content["_expandable"]:
            space_path = content["_expandable"]["space"]
            m = re.search(r"/([^/]+)$", space_path)
            if m:
                space = m.group(1)
        last_mod = r.get("lastModified", content.get("history", {}).get("lastUpdated", {}).get("when", ""))
        if last_mod:
            last_mod = last_mod[:10]
        lines.append(f"| {ctype} | {cid} | {title} | {space} | {last_mod} |")

    return "\n".join(lines)


def format_comments_markdown(results: list[dict]) -> str:
    """Format page comments as markdown."""
    lines = [f"## Comments ({len(results)})"]
    lines.append("")
    if not results:
        lines.append("No comments.")
        return "\n".join(lines)
    for c in results:
        cid = c.get("id", "")
        author = c.get("authorId", "")
        created = c.get("createdAt", "")
        version = c.get("version", {})
        body = c.get("body", {})
        storage = body.get("storage", {})
        text = ""
        if isinstance(storage, dict) and storage.get("value"):
            text = _strip_html(storage["value"])
        lines.append(f"### Comment {cid} — {author} — {created}")
        lines.append("")
        if text:
            lines.append(text)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_view(args: argparse.Namespace) -> None:
    """View a single page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str] = {"body-format": "storage"}
    if args.include_labels:
        params["include-labels"] = "true"
    data = confluence_request("GET", f"/pages/{page_id}", base_url, token, params=params)
    print(format_page_markdown(data, base_url))


def cmd_search(args: argparse.Namespace) -> None:
    """Search content via CQL."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {
        "cql": args.cql,
        "limit": args.limit,
    }
    data = confluence_request(
        "GET", "/search", base_url, token, params=params,
        api_prefix="/wiki/rest/api",
    )
    print(format_search_results(data))


def cmd_pages(args: argparse.Namespace) -> None:
    """List pages, optionally filtered by space."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {"limit": args.limit}
    if args.title:
        params["title"] = args.title
    if args.status:
        params["status"] = args.status

    if args.space_id:
        data = confluence_request("GET", f"/spaces/{args.space_id}/pages", base_url, token, params=params)
    else:
        data = confluence_request("GET", "/pages", base_url, token, params=params)

    results = data.get("results", [])
    print(format_pages_table(results))


def cmd_spaces(args: argparse.Namespace) -> None:
    """List spaces."""
    token = get_token()
    base_url = get_base_url()
    params: dict[str, str | int] = {"limit": args.limit}
    if args.type:
        params["type"] = args.type
    if args.status:
        params["status"] = args.status
    data = confluence_request("GET", "/spaces", base_url, token, params=params)
    results = data.get("results", [])
    print(format_spaces_table(results))


def cmd_create(args: argparse.Namespace) -> None:
    """Create a new page."""
    token = get_token()
    base_url = get_base_url()
    body: dict = {
        "spaceId": args.space_id,
        "status": "current",
        "title": args.title,
        "body": {
            "representation": "storage",
            "value": args.body or "",
        },
    }
    if args.parent_id:
        body["parentId"] = args.parent_id

    data = confluence_request("POST", "/pages", base_url, token, data=body)
    page_id = data.get("id", "")
    links = data.get("_links", {})
    webui = links.get("webui", "")
    link_base = links.get("base", base_url)
    url = f"{link_base}{webui}" if webui else f"{base_url}/wiki/pages/{page_id}"
    print(f"Created page {page_id}: {data.get('title', '')}")
    print(f"URL: {url}")


def cmd_update(args: argparse.Namespace) -> None:
    """Update an existing page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)

    current = confluence_request("GET", f"/pages/{page_id}", base_url, token, params={"body-format": "storage"})
    current_version = current.get("version", {}).get("number", 1)
    current_title = current.get("title", "")
    current_status = current.get("status", "current")

    payload: dict = {
        "id": page_id,
        "status": current_status,
        "title": args.title or current_title,
        "body": {
            "representation": "storage",
            "value": args.body if args.body is not None else current.get("body", {}).get("storage", {}).get("value", ""),
        },
        "version": {
            "number": current_version + 1,
            "message": args.version_message or "",
        },
    }

    confluence_request("PUT", f"/pages/{page_id}", base_url, token, data=payload)
    print(f"Updated page {page_id}: {payload['title']} (version {current_version + 1})")
    links = current.get("_links", {})
    webui = links.get("webui", "")
    link_base = links.get("base", base_url)
    if webui:
        print(f"URL: {link_base}{webui}")


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a page (moves to trash)."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str] = {}
    if args.purge:
        params["purge"] = "true"
    confluence_request("DELETE", f"/pages/{page_id}", base_url, token, params=params or None)
    action = "Purged" if args.purge else "Deleted (moved to trash)"
    print(f"{action} page {page_id}")


def cmd_comments(args: argparse.Namespace) -> None:
    """List comments on a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str | int] = {"body-format": "storage", "limit": args.limit}
    data = confluence_request("GET", f"/pages/{page_id}/footer-comments", base_url, token, params=params)
    results = data.get("results", [])
    print(format_comments_markdown(results))


def cmd_comment(args: argparse.Namespace) -> None:
    """Add a comment to a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    body = {
        "pageId": page_id,
        "body": {
            "representation": "storage",
            "value": f"<p>{html.escape(args.body)}</p>",
        },
    }
    data = confluence_request("POST", "/footer-comments", base_url, token, data=body)
    print(f"Comment added to page {page_id} (id: {data.get('id', '')})")


def cmd_labels(args: argparse.Namespace) -> None:
    """List labels on a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str | int] = {"limit": args.limit}
    data = confluence_request("GET", f"/pages/{page_id}/labels", base_url, token, params=params)
    results = data.get("results", [])
    if not results:
        print(f"No labels on page {page_id}.")
        return
    names = [lb.get("name", "") for lb in results]
    print(f"Labels on page {page_id}: {', '.join(names)}")


def cmd_add_label(args: argparse.Namespace) -> None:
    """Add labels to a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    labels_data = [{"name": name} for name in args.names]
    confluence_request("POST", f"/pages/{page_id}/labels", base_url, token, data=labels_data)
    print(f"Added labels to page {page_id}: {', '.join(args.names)}")


def cmd_children(args: argparse.Namespace) -> None:
    """List child pages of a page."""
    token = get_token()
    base_url, page_id = parse_page_input(args.page)
    params: dict[str, str | int] = {"limit": args.limit}
    data = confluence_request("GET", f"/pages/{page_id}/children", base_url, token, params=params)
    results = data.get("results", [])
    print(format_pages_table(results, f"Children of page {page_id}"))


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

PAGE_HELP = "Page ID (e.g. 12345) or full Confluence page URL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Confluence REST API client for developer workflows.")
    sub = parser.add_subparsers(dest="command", required=True)

    # view
    p_view = sub.add_parser("view", help="View a single page")
    p_view.add_argument("page", help=PAGE_HELP)
    p_view.add_argument("--include-labels", action="store_true", help="Include labels")
    p_view.set_defaults(func=cmd_view)

    # search
    p_search = sub.add_parser("search", help="Search content via CQL")
    p_search.add_argument("cql", help='CQL query string (e.g. "space=TEAM AND type=page")')
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p_search.set_defaults(func=cmd_search)

    # pages
    p_pages = sub.add_parser("pages", help="List pages")
    p_pages.add_argument("--space-id", help="Filter by space ID")
    p_pages.add_argument("--title", help="Filter by exact title")
    p_pages.add_argument("--status", help="Filter by status (current, draft, trashed)")
    p_pages.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_pages.set_defaults(func=cmd_pages)

    # spaces
    p_spaces = sub.add_parser("spaces", help="List spaces")
    p_spaces.add_argument("--type", help="Filter by type (global, personal)")
    p_spaces.add_argument("--status", help="Filter by status (current, archived)")
    p_spaces.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_spaces.set_defaults(func=cmd_spaces)

    # create
    p_create = sub.add_parser("create", help="Create a new page")
    p_create.add_argument("--space-id", required=True, help="Space ID")
    p_create.add_argument("--title", required=True, help="Page title")
    p_create.add_argument("--body", help="Page body in Confluence storage format (HTML)")
    p_create.add_argument("--parent-id", help="Parent page ID")
    p_create.set_defaults(func=cmd_create)

    # update
    p_update = sub.add_parser("update", help="Update an existing page")
    p_update.add_argument("page", help=PAGE_HELP)
    p_update.add_argument("--title", help="New title")
    p_update.add_argument("--body", help="New body in storage format (HTML)")
    p_update.add_argument("--version-message", help="Version comment")
    p_update.set_defaults(func=cmd_update)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a page")
    p_delete.add_argument("page", help=PAGE_HELP)
    p_delete.add_argument("--purge", action="store_true", help="Permanently delete (skip trash)")
    p_delete.set_defaults(func=cmd_delete)

    # comments
    p_comments = sub.add_parser("comments", help="List comments on a page")
    p_comments.add_argument("page", help=PAGE_HELP)
    p_comments.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_comments.set_defaults(func=cmd_comments)

    # comment
    p_comment = sub.add_parser("comment", help="Add a comment to a page")
    p_comment.add_argument("page", help=PAGE_HELP)
    p_comment.add_argument("body", help="Comment text")
    p_comment.set_defaults(func=cmd_comment)

    # labels
    p_labels = sub.add_parser("labels", help="List labels on a page")
    p_labels.add_argument("page", help=PAGE_HELP)
    p_labels.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_labels.set_defaults(func=cmd_labels)

    # add-label
    p_add_label = sub.add_parser("add-label", help="Add labels to a page")
    p_add_label.add_argument("page", help=PAGE_HELP)
    p_add_label.add_argument("names", nargs="+", help="Label names to add")
    p_add_label.set_defaults(func=cmd_add_label)

    # children
    p_children = sub.add_parser("children", help="List child pages")
    p_children.add_argument("page", help=PAGE_HELP)
    p_children.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    p_children.set_defaults(func=cmd_children)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
