#!/usr/bin/env python3
"""Skills Setup - Interactive installer for AI assistant skill directories.

Provides a curses-based multi-select UI for choosing which skills to install.
Supports macOS, Linux, and Windows (auto-installs windows-curses if needed).

Usage:
    python3 scripts/skills-setup.py            # Interactive mode
    python3 scripts/skills-setup.py .cursor    # Direct target mode
"""

from __future__ import annotations

import filecmp
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SOURCE_SKILLS_DIR = PROJECT_ROOT / "skills"

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
        # STD_OUTPUT_HANDLE = -11, ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4
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

import curses  # noqa: E402 — must import after _ensure_curses()

# --- Colors for non-curses output ---

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"


# --- Utilities ---


def validate_source() -> None:
    """Ensure the source skills directory exists and is non-empty."""
    if not SOURCE_SKILLS_DIR.is_dir():
        print(f"{RED}Error: Source skills directory not found: {SOURCE_SKILLS_DIR}{NC}")
        sys.exit(1)
    if not any(SOURCE_SKILLS_DIR.iterdir()):
        print(f"{RED}Error: Source skills directory is empty: {SOURCE_SKILLS_DIR}{NC}")
        sys.exit(1)


def get_skill_dirs() -> list[Path]:
    """Return sorted list of skill directories."""
    return sorted(
        p
        for p in SOURCE_SKILLS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def dirs_differ(src: Path, dst: Path) -> bool:
    """Return True if src and dst directory trees differ."""
    cmp = filecmp.dircmp(src, dst)
    if cmp.left_only or cmp.right_only or cmp.diff_files:
        return True
    for sub in cmp.subdirs.values():
        if sub.left_only or sub.right_only or sub.diff_files:
            return True
    return False


def sync_skills(
    label: str,
    config_dir: str,
    skills_subpath: str,
    selected_skills: list[Path],
) -> bool:
    """Sync selected skills to a tool's config directory."""
    config_path = Path.home() / config_dir
    target_skills_dir = config_path / skills_subpath

    if not config_path.is_dir():
        print(
            f"{YELLOW}⚠ {label} is not installed "
            f"(~/{config_dir} not found), skipping.{NC}"
        )
        return False

    target_skills_dir.mkdir(parents=True, exist_ok=True)

    added: list[str] = []
    updated: list[str] = []

    for source_skill in selected_skills:
        skill_name = source_skill.name
        target_skill = target_skills_dir / skill_name

        if not target_skill.is_dir():
            added.append(skill_name)
        elif dirs_differ(source_skill, target_skill):
            updated.append(skill_name)

        if target_skill.exists():
            shutil.rmtree(target_skill)
        shutil.copytree(source_skill, target_skill)

    print(f"{GREEN}✓ [{label}] Skills synced to {target_skills_dir}{NC}")
    if added:
        print(f"  {GREEN}Added:{NC} {' '.join(added)}")
    if updated:
        print(f"  {YELLOW}Updated:{NC} {' '.join(updated)}")
    if not added and not updated:
        print("  No skill changes detected.")
    return True


# --- Curses multi-select UI ---


def curses_multi_select(
    stdscr: curses.window,
    title: str,
    items: list[str],
    preselected: list[bool] | None = None,
    disabled: set[int] | None = None,
) -> list[int] | None:
    """Interactive multi-select with arrow keys, space, and enter.

    Returns list of selected indices, or None if user cancelled (q/Esc).
    Disabled indices are shown dimmed and cannot be selected or toggled.
    """
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)

    disabled = disabled or set()
    if preselected:
        selected = list(preselected)
    else:
        selected = [i not in disabled for i in range(len(items))]
    for i in disabled:
        selected[i] = False

    cursor = 0
    all_item = "Select All / Deselect All"
    total_items = 1 + len(items)
    enabled_count = len(items) - len(disabled)

    def _next_enabled(pos: int, direction: int) -> int:
        """Find next non-disabled position, wrapping around."""
        candidate = (pos + direction) % total_items
        attempts = 0
        while attempts < total_items:
            if candidate == 0 or candidate - 1 not in disabled:
                return candidate
            candidate = (candidate + direction) % total_items
            attempts += 1
        return 0

    def draw() -> None:
        stdscr.clear()
        stdscr.addstr(0, 0, title, curses.A_BOLD)
        hint = "Up/Down move | Space toggle | a all/none | Enter confirm | q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        row = 3
        enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
        all_selected = bool(enabled_sel) and all(enabled_sel)
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
            is_disabled = i in disabled
            if is_disabled:
                marker = "[-]"
                attr = curses.A_DIM
                color = 0
            else:
                marker = "[x]" if selected[i] else "[ ]"
                attr = curses.A_REVERSE if cursor == i + 1 else 0
                color = curses.color_pair(2) if selected[i] else 0
            try:
                stdscr.addstr(row + i, 0, f"  {marker}  {item}", attr | color)
            except curses.error:
                pass

        count = sum(1 for i, s in enumerate(selected) if s and i not in disabled)
        try:
            stdscr.addstr(
                row + len(items) + 1,
                0,
                f"  {count}/{enabled_count} selected",
                curses.color_pair(3),
            )
        except curses.error:
            pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = _next_enabled(cursor, -1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = _next_enabled(cursor, 1)
        elif key == ord(" "):
            if cursor == 0:
                enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
                new_val = not (bool(enabled_sel) and all(enabled_sel))
                selected = [
                    new_val if i not in disabled else False for i in range(len(items))
                ]
            elif cursor - 1 not in disabled:
                selected[cursor - 1] = not selected[cursor - 1]
        elif key == ord("a"):
            enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
            new_val = not (bool(enabled_sel) and all(enabled_sel))
            selected = [
                new_val if i not in disabled else False for i in range(len(items))
            ]
        elif key in (curses.KEY_ENTER, 10, 13):
            return [i for i, s in enumerate(selected) if s and i not in disabled]
        elif key in (ord("q"), 27):
            return None


def select_skills_interactive(skill_dirs: list[Path]) -> list[Path] | None:
    """Launch curses UI to select skills. Returns selected paths or None."""
    items = [d.name for d in skill_dirs]
    indices = curses.wrapper(
        curses_multi_select,
        "Select skills to install:",
        items,
    )
    if indices is None:
        return None
    return [skill_dirs[i] for i in indices]


def _detect_uninstalled_tools() -> set[int]:
    """Return indices of tools whose config directories don't exist."""
    uninstalled: set[int] = set()
    for i, (_, config_dir, _) in enumerate(TOOLS):
        if not (Path.home() / config_dir).is_dir():
            uninstalled.add(i)
    return uninstalled


def select_tools_interactive() -> list[int] | None:
    """Launch curses UI to select AI tools. Returns selected indices or None."""
    uninstalled = _detect_uninstalled_tools()
    items = [
        f"{t[0]}  (not installed)" if i in uninstalled else t[0]
        for i, t in enumerate(TOOLS)
    ]
    return curses.wrapper(
        curses_multi_select,
        "Select AI tools to install skills to:",
        items,
        disabled=uninstalled,
    )


# --- CLI modes ---


def run_skills_check(selected_skills: list[Path]) -> None:
    check_script = SCRIPT_DIR / "skills-check.py"
    if not check_script.is_file():
        return
    skill_names = [skill.name for skill in selected_skills]
    sys.stdout.flush()
    subprocess.run([sys.executable, str(check_script)] + skill_names)


def direct_target_mode(target_dir: str) -> None:
    """Install selected skills to a specific target directory."""
    target_path = Path.home() / target_dir
    if not target_path.is_dir():
        print(
            f"{RED}Error: ~/{target_dir} not found. "
            f"The tool does not appear to be installed.{NC}"
        )
        sys.exit(1)

    skill_dirs = get_skill_dirs()
    selected = select_skills_interactive(skill_dirs)
    if selected is None or len(selected) == 0:
        print("No skills selected. Aborted.")
        sys.exit(0)

    target_skills_dir = target_path / "skills"
    target_skills_dir.mkdir(parents=True, exist_ok=True)

    added: list[str] = []
    updated: list[str] = []

    for source_skill in selected:
        skill_name = source_skill.name
        target_skill = target_skills_dir / skill_name

        if not target_skill.is_dir():
            added.append(skill_name)
        elif dirs_differ(source_skill, target_skill):
            updated.append(skill_name)

        if target_skill.exists():
            shutil.rmtree(target_skill)
        shutil.copytree(source_skill, target_skill)

    print(f"{GREEN}✓ Skills synced to {target_skills_dir}{NC}")
    if added:
        print(f"  {GREEN}Added:{NC} {' '.join(added)}")
    if updated:
        print(f"  {YELLOW}Updated:{NC} {' '.join(updated)}")
    if not added and not updated:
        print("  No skill changes detected.")

    run_skills_check(selected)


def interactive_mode() -> None:
    """Full interactive mode: select tools, then select skills."""
    tool_indices = select_tools_interactive()
    if tool_indices is None or len(tool_indices) == 0:
        print("No tools selected. Aborted.")
        sys.exit(0)

    skill_dirs = get_skill_dirs()
    selected_skills = select_skills_interactive(skill_dirs)
    if selected_skills is None or len(selected_skills) == 0:
        print("No skills selected. Aborted.")
        sys.exit(0)

    print()
    installed = 0
    skipped = 0

    for idx in tool_indices:
        label, config_dir, skills_subpath = TOOLS[idx]
        if sync_skills(label, config_dir, skills_subpath, selected_skills):
            installed += 1
        else:
            skipped += 1
        print()

    print(
        f"{BOLD}Done.{NC} Installed: {GREEN}{installed}{NC}, "
        f"Skipped: {YELLOW}{skipped}{NC}"
    )

    run_skills_check(selected_skills)


def main() -> None:
    validate_source()

    if len(sys.argv) > 1:
        direct_target_mode(sys.argv[1])
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
