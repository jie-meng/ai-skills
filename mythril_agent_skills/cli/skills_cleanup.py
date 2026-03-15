#!/usr/bin/env python3
"""Skills Cleanup - Interactive remover for installed AI assistant skills.

Scans AI tool config directories for installed skills, presents a tree-view
multi-select UI, and deletes the selected skill directories.
Supports macOS, Linux, and Windows (auto-installs windows-curses if needed).

Usage:
    skills-cleanup          # after pip install
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"

TOOLS: list[tuple[str, str, str]] = [
    ("Copilot CLI", ".copilot", "skills"),
    ("Claude Code", ".claude", "skills"),
    ("Cursor", ".cursor", "skills"),
    ("Codex", ".codex", "skills"),
    ("Gemini CLI", ".gemini", "skills"),
    ("Qwen CLI", ".qwen", "skills"),
    ("iFlow CLI", ".iflow", "skills"),
    ("Opencode", ".config/opencode", "skills"),
    ("Grok CLI", ".grok", "skills"),
]


# --- Platform bootstrap ---


def _enable_windows_ansi() -> None:
    """Enable ANSI escape sequences on Windows 10+ terminals."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 4)
    except Exception:
        pass


def _ensure_curses() -> None:
    """Import curses, auto-installing windows-curses on Windows if needed."""
    try:
        import curses as _  # noqa: F401
    except ImportError:
        if IS_WINDOWS:
            print("Installing windows-curses ...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "windows-curses"],
                stdout=subprocess.DEVNULL,
            )
        else:
            print(
                "Error: curses module not available. "
                "Please install Python with curses support."
            )
            sys.exit(1)


_enable_windows_ansi()
_ensure_curses()

import curses  # noqa: E402

# --- Colors for non-curses output ---

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"


# --- Data structures ---


class SkillEntry:
    """A selectable skill under a tool group."""

    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path
        self.selected = False


class ToolGroup:
    """A tool with its installed skills."""

    def __init__(self, label: str, config_dir: str, skills_dir: Path) -> None:
        self.label = label
        self.config_dir = config_dir
        self.skills_dir = skills_dir
        self.skills: list[SkillEntry] = []

    def scan(self) -> None:
        """Populate skills list from the filesystem."""
        self.skills = sorted(
            (
                SkillEntry(p.name, p)
                for p in self.skills_dir.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ),
            key=lambda s: s.name,
        )


# --- Scanning ---


def scan_installed_tools() -> list[ToolGroup]:
    """Return tool groups that exist and contain at least one skill."""
    groups: list[ToolGroup] = []
    for label, config_dir, skills_subpath in TOOLS:
        skills_dir = Path.home() / config_dir / skills_subpath
        if not skills_dir.is_dir():
            continue
        group = ToolGroup(label, config_dir, skills_dir)
        group.scan()
        if group.skills:
            groups.append(group)
    return groups


# --- Curses tree-select UI ---


def _build_rows(
    groups: list[ToolGroup],
) -> list[tuple[str, ToolGroup | None, SkillEntry | None]]:
    """Build a flat list of display rows from the tree structure.

    Each row is (display_text, group_or_none, skill_or_none).
    - Tool header rows:  (text, group, None)    — not selectable
    - Skill rows:        (text, group, skill)   — selectable
    """
    rows: list[tuple[str, ToolGroup | None, SkillEntry | None]] = []
    for group in groups:
        rows.append((group.label, group, None))
        for skill in group.skills:
            rows.append((skill.name, group, skill))
    return rows


def curses_tree_select(
    stdscr: curses.window,
    groups: list[ToolGroup],
) -> bool | None:
    """Tree-view multi-select. Returns True if confirmed, None if cancelled."""
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)

    rows = _build_rows(groups)
    cursor = 0
    scroll_offset = 0

    # "Select All / Deselect All" is a virtual row at index -1 (drawn at top)
    # cursor == 0 means the all-toggle; cursor >= 1 means rows[cursor - 1]
    total_items = 1 + len(rows)

    def is_header(row_idx: int) -> bool:
        return rows[row_idx][2] is None

    def all_skills() -> list[SkillEntry]:
        return [s for g in groups for s in g.skills]

    def selected_count() -> int:
        return sum(1 for s in all_skills() if s.selected)

    def total_skill_count() -> int:
        return len(all_skills())

    def _next_selectable(pos: int, direction: int) -> int:
        """Find next selectable position (skip headers)."""
        pos = (pos + direction) % total_items
        attempts = 0
        while attempts < total_items:
            if pos == 0:
                return pos
            if not is_header(pos - 1):
                return pos
            pos = (pos + direction) % total_items
            attempts += 1
        return pos

    # Start cursor on first selectable row
    if cursor == 0:
        pass
    else:
        cursor = _next_selectable(0, 1)

    def draw() -> None:
        nonlocal scroll_offset
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        stdscr.addstr(0, 0, "Select skills to remove:", curses.A_BOLD)
        hint = "Up/Down move | Space toggle | a all/none | Enter confirm | q quit"
        try:
            stdscr.addstr(1, 0, hint, curses.color_pair(3))
        except curses.error:
            pass

        content_start = 3
        visible_lines = max_y - content_start - 2  # room for footer

        # All-toggle row + separator + data rows
        all_rows_count = 1 + 1 + len(rows)  # toggle + sep + rows

        # Adjust scroll so cursor is visible
        # Map cursor to visual line index
        if cursor == 0:
            visual_cursor = 0
        else:
            visual_cursor = 2 + (cursor - 1)  # after toggle + separator

        if visual_cursor < scroll_offset:
            scroll_offset = visual_cursor
        elif visual_cursor >= scroll_offset + visible_lines:
            scroll_offset = visual_cursor - visible_lines + 1

        line = 0  # visual line counter

        # --- All-toggle row ---
        if line >= scroll_offset and line < scroll_offset + visible_lines:
            screen_row = content_start + (line - scroll_offset)
            all_selected = all(s.selected for s in all_skills())
            marker = "[x]" if all_selected else "[ ]"
            attr = curses.A_REVERSE if cursor == 0 else 0
            text = f"  {marker}  Select All / Deselect All"
            try:
                stdscr.addstr(screen_row, 0, text, attr | curses.color_pair(1))
            except curses.error:
                pass
        line += 1

        # --- Separator ---
        if line >= scroll_offset and line < scroll_offset + visible_lines:
            screen_row = content_start + (line - scroll_offset)
            try:
                stdscr.addstr(screen_row, 0, "  " + "-" * 36, curses.color_pair(1))
            except curses.error:
                pass
        line += 1

        # --- Tree rows ---
        for row_idx, (text, group, skill) in enumerate(rows):
            if line >= scroll_offset and (line < scroll_offset + visible_lines):
                screen_row = content_start + (line - scroll_offset)
                item_cursor = row_idx + 1  # +1 because 0 is all-toggle

                if skill is None:
                    # Tool header — not selectable
                    group_sel = sum(1 for s in group.skills if s.selected)
                    group_total = len(group.skills)
                    header = (
                        f"  {text}  "
                        f"~/{group.config_dir}/skills/ "
                        f"({group_sel}/{group_total})"
                    )
                    try:
                        stdscr.addstr(
                            screen_row,
                            0,
                            header,
                            curses.A_BOLD | curses.color_pair(1),
                        )
                    except curses.error:
                        pass
                else:
                    marker = "[x]" if skill.selected else "[ ]"
                    attr = curses.A_REVERSE if cursor == item_cursor else 0
                    color = (
                        curses.color_pair(2) if skill.selected else curses.color_pair(4)
                    )
                    try:
                        stdscr.addstr(
                            screen_row,
                            0,
                            f"    {marker}  {text}",
                            attr | color,
                        )
                    except curses.error:
                        pass
            line += 1

        # --- Footer ---
        count = selected_count()
        total = total_skill_count()
        footer_row = min(
            content_start + visible_lines,
            max_y - 1,
        )
        try:
            stdscr.addstr(
                footer_row,
                0,
                f"  {count}/{total} selected for removal",
                curses.color_pair(3),
            )
        except curses.error:
            pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = _next_selectable(cursor, -1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = _next_selectable(cursor, 1)
        elif key == ord(" "):
            if cursor == 0:
                skills = all_skills()
                new_val = not all(s.selected for s in skills)
                for s in skills:
                    s.selected = new_val
            else:
                row_idx = cursor - 1
                _, _, skill = rows[row_idx]
                if skill is not None:
                    skill.selected = not skill.selected
        elif key == ord("a"):
            skills = all_skills()
            new_val = not all(s.selected for s in skills)
            for s in skills:
                s.selected = new_val
        elif key in (curses.KEY_ENTER, 10, 13):
            return True
        elif key in (ord("q"), 27):
            return None


# --- Deletion ---


def delete_selected(groups: list[ToolGroup]) -> None:
    """Delete selected skill directories and report results."""
    total_deleted = 0

    for group in groups:
        deleted_names: list[str] = []
        for skill in group.skills:
            if skill.selected and skill.path.is_dir():
                shutil.rmtree(skill.path)
                deleted_names.append(skill.name)
                total_deleted += 1

        if deleted_names:
            print(f"{GREEN}✓ [{group.label}] Removed:{NC} {' '.join(deleted_names)}")

    if total_deleted == 0:
        print("No skills were removed.")
    else:
        print(f"\n{BOLD}Done.{NC} Removed {GREEN}{total_deleted}{NC} skill(s) total.")


# --- Main ---


def main() -> None:
    groups = scan_installed_tools()

    if not groups:
        print(f"{YELLOW}No installed skills found in any AI tool directory.{NC}")
        sys.exit(0)

    # Step 1: Select tools to scan (default: all selected)
    tool_items = [
        f"{g.label}  ~/{g.config_dir}/skills/  ({len(g.skills)} skills)" for g in groups
    ]
    tool_indices = curses.wrapper(
        _curses_tool_select,
        "Select AI tools to scan for cleanup:",
        tool_items,
    )
    if tool_indices is None or len(tool_indices) == 0:
        print("No tools selected. Aborted.")
        sys.exit(0)

    selected_groups = [groups[i] for i in tool_indices]

    # Step 2: Tree-select skills to remove (default: none selected)
    confirmed = curses.wrapper(curses_tree_select, selected_groups)
    if confirmed is None:
        print("Cancelled.")
        sys.exit(0)

    selected_skills = [s for g in selected_groups for s in g.skills if s.selected]
    if not selected_skills:
        print("No skills selected for removal.")
        sys.exit(0)

    # Step 3: Delete
    print()
    delete_selected(selected_groups)


def _curses_tool_select(
    stdscr: curses.window,
    title: str,
    items: list[str],
) -> list[int] | None:
    """Multi-select for tools (reuses the same pattern as skills-setup)."""
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)

    selected = [True] * len(items)
    cursor = 0
    all_item = "Select All / Deselect All"
    total_items = 1 + len(items)

    def draw() -> None:
        stdscr.clear()
        stdscr.addstr(0, 0, title, curses.A_BOLD)
        hint = "Up/Down move | Space toggle | a all/none | Enter confirm | q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        row = 3
        all_selected = all(selected)
        marker = "[x]" if all_selected else "[ ]"
        attr = curses.A_REVERSE if cursor == 0 else 0
        try:
            stdscr.addstr(
                row, 0, f"  {marker}  {all_item}", attr | curses.color_pair(1)
            )
        except curses.error:
            pass

        row += 1
        try:
            stdscr.addstr(row, 0, "  " + "-" * 36, curses.color_pair(1))
        except curses.error:
            pass

        row += 1
        for i, item in enumerate(items):
            marker = "[x]" if selected[i] else "[ ]"
            attr = curses.A_REVERSE if cursor == i + 1 else 0
            color = curses.color_pair(2) if selected[i] else 0
            try:
                stdscr.addstr(row + i, 0, f"  {marker}  {item}", attr | color)
            except curses.error:
                pass

        count = sum(selected)
        try:
            stdscr.addstr(
                row + len(items) + 1,
                0,
                f"  {count}/{len(items)} selected",
                curses.color_pair(3),
            )
        except curses.error:
            pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = (cursor - 1) % total_items
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = (cursor + 1) % total_items
        elif key == ord(" "):
            if cursor == 0:
                new_val = not all(selected)
                selected = [new_val] * len(items)
            else:
                selected[cursor - 1] = not selected[cursor - 1]
        elif key == ord("a"):
            new_val = not all(selected)
            selected = [new_val] * len(items)
        elif key in (curses.KEY_ENTER, 10, 13):
            return [i for i, s in enumerate(selected) if s]
        elif key in (ord("q"), 27):
            return None


if __name__ == "__main__":
    main()
