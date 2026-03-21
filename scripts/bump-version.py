#!/usr/bin/env python3
"""Bump the version across all project files in one shot.

Updates:
  - pyproject.toml          (version = "x.y.z")
  - mythril_agent_skills/__init__.py (__version__ = "x.y.z")
  - .claude-plugin/marketplace.json  (all "version" fields)

Usage:
    python3 scripts/bump-version.py 0.3.0
    python3 scripts/bump-version.py          # show current version
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
INIT_FILE = PROJECT_ROOT / "mythril_agent_skills" / "__init__.py"
MARKETPLACE = PROJECT_ROOT / ".claude-plugin" / "marketplace.json"

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _read_current_versions() -> dict[str, str | list[str]]:
    """Read version strings from all tracked files."""
    versions: dict[str, str | list[str]] = {}

    # pyproject.toml
    pyproject_text = PYPROJECT.read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.MULTILINE)
    versions["pyproject.toml"] = m.group(1) if m else "NOT FOUND"

    # __init__.py
    init_text = INIT_FILE.read_text()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    versions["__init__.py"] = m.group(1) if m else "NOT FOUND"

    # marketplace.json
    if MARKETPLACE.exists():
        data = json.loads(MARKETPLACE.read_text())
        plugin_versions = []
        for plugin in data.get("plugins", []):
            v = plugin.get("version", "NOT FOUND")
            plugin_versions.append(f'{plugin["name"]}={v}')
        versions["marketplace.json"] = plugin_versions

    return versions


def _show_current() -> None:
    """Display current versions across all files."""
    versions = _read_current_versions()
    print(f"{BOLD}Current versions:{NC}")
    for f, v in versions.items():
        if isinstance(v, list):
            print(f"  {f}:")
            for entry in v:
                print(f"    {entry}")
        else:
            print(f"  {f}: {GREEN}{v}{NC}")


def _update_pyproject(new_version: str) -> None:
    """Update version in pyproject.toml."""
    text = PYPROJECT.read_text()
    updated, count = re.subn(
        r'^(version\s*=\s*)"[^"]+"',
        rf'\g<1>"{new_version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        print(f"{RED}Error: version field not found in pyproject.toml{NC}")
        sys.exit(1)
    PYPROJECT.write_text(updated)


def _update_init(new_version: str) -> None:
    """Update __version__ in __init__.py."""
    text = INIT_FILE.read_text()
    updated, count = re.subn(
        r'(__version__\s*=\s*)"[^"]+"',
        rf'\g<1>"{new_version}"',
        text,
        count=1,
    )
    if count == 0:
        print(f"{RED}Error: __version__ not found in __init__.py{NC}")
        sys.exit(1)
    INIT_FILE.write_text(updated)


def _update_marketplace(new_version: str) -> None:
    """Update all version fields in marketplace.json."""
    if not MARKETPLACE.exists():
        print(f"{YELLOW}Warning: {MARKETPLACE} not found, skipping.{NC}")
        return

    data = json.loads(MARKETPLACE.read_text())
    count = 0
    for plugin in data.get("plugins", []):
        if "version" in plugin:
            plugin["version"] = new_version
            count += 1

    MARKETPLACE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return count


def main() -> None:
    if len(sys.argv) < 2:
        _show_current()
        print(f"\n{BOLD}Usage:{NC} python3 scripts/bump-version.py <new-version>")
        print(f"  Example: python3 scripts/bump-version.py 0.3.0")
        sys.exit(0)

    new_version = sys.argv[1]

    if not VERSION_RE.match(new_version):
        print(f"{RED}Error: '{new_version}' is not a valid semver (x.y.z){NC}")
        sys.exit(1)

    # Show current state
    _show_current()

    # Confirm
    print(f"\n  New version: {BOLD}{new_version}{NC}")
    try:
        answer = input(f"  Proceed? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)
    if answer not in ("y", "yes"):
        print("Aborted.")
        sys.exit(1)

    # Update all files
    _update_pyproject(new_version)
    print(f"  {GREEN}Updated{NC} pyproject.toml")

    _update_init(new_version)
    print(f"  {GREEN}Updated{NC} mythril_agent_skills/__init__.py")

    plugin_count = _update_marketplace(new_version)
    if plugin_count:
        print(
            f"  {GREEN}Updated{NC} .claude-plugin/marketplace.json"
            f" ({plugin_count} plugins)"
        )

    # Verify
    print(f"\n{BOLD}Verification:{NC}")
    _show_current()
    print(f"\n{GREEN}Done.{NC} Don't forget to commit and tag:")
    print(f"  git add -A && git commit -m 'Bump version to {new_version}'")
    print(f"  git tag v{new_version}")


if __name__ == "__main__":
    main()
