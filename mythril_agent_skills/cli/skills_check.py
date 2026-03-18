#!/usr/bin/env python3
"""Skills Check - Interactive dependency checker and configurator.

Checks CLI tools and environment variables required by installed skills.
Automatically installs missing CLI tools (with user confirmation), prompts
for missing API keys/tokens, and saves them to the user's shell config file.

Usage:
    skills-check                    # Interactive: select skills to check
    skills-check gh-operations jira # Check specific skills
"""

from __future__ import annotations

import getpass
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


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

import curses  # noqa: E402 — must import after _ensure_curses()

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

SKILL_GH_OPERATIONS = "gh-operations"
SKILL_CODE_REVIEW_PR = "github-code-review-pr"
SKILL_JIRA = "jira"
SKILL_CONFLUENCE = "confluence"
SKILL_FIGMA = "figma"
SKILL_IMAGEMAGICK = "imagemagick"
SKILL_FFMPEG = "ffmpeg"
SKILL_GIT_REPO_READER = "git-repo-reader"

CHECKABLE_SKILLS = [
    SKILL_GH_OPERATIONS,
    SKILL_CODE_REVIEW_PR,
    SKILL_JIRA,
    SKILL_CONFLUENCE,
    SKILL_FIGMA,
    SKILL_IMAGEMAGICK,
    SKILL_FFMPEG,
    SKILL_GIT_REPO_READER,
]


def _detect_shell_config() -> Path:
    """Detect the user's shell config file."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()

    if "zsh" in shell:
        return home / ".zshrc"
    elif "fish" in shell:
        return home / ".config" / "fish" / "config.fish"
    elif "bash" in shell:
        bashrc = home / ".bashrc"
        bash_profile = home / ".bash_profile"
        if IS_MACOS and bash_profile.exists() and not bashrc.exists():
            return bash_profile
        return bashrc

    if IS_WINDOWS:
        ps_profile = Path(os.environ.get("USERPROFILE", "")) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        if ps_profile.exists():
            return ps_profile

    zshrc = home / ".zshrc"
    if zshrc.exists():
        return zshrc
    return home / ".bashrc"


def _read_config_file(config_path: Path) -> str:
    """Read config file contents, return empty string if not exists."""
    if config_path.exists():
        return config_path.read_text()
    return ""


def _env_var_exists_in_config(config_path: Path, var_name: str) -> bool:
    """Check if an env var export already exists in the config file."""
    content = _read_config_file(config_path)
    pattern = rf'^export\s+{re.escape(var_name)}='
    return bool(re.search(pattern, content, re.MULTILINE))


def _append_env_var(config_path: Path, var_name: str, value: str) -> None:
    """Append an export statement to the shell config file."""
    content = _read_config_file(config_path)

    if _env_var_exists_in_config(config_path, var_name):
        lines = content.splitlines()
        new_lines = []
        pattern = rf'^export\s+{re.escape(var_name)}='
        for line in lines:
            if re.match(pattern, line):
                new_lines.append(f'export {var_name}="{value}"')
            else:
                new_lines.append(line)
        config_path.write_text("\n".join(new_lines) + "\n")
        print(f"    {GREEN}Updated{NC} {var_name} in {config_path}")
    else:
        with open(config_path, "a") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write(f'export {var_name}="{value}"\n')
        print(f"    {GREEN}Added{NC} {var_name} to {config_path}")

    os.environ[var_name] = value


def _prompt_value(prompt_text: str, secret: bool = False) -> str | None:
    """Prompt user for a value. Returns None if user skips."""
    try:
        if secret:
            value = getpass.getpass(f"    {prompt_text}: ")
        else:
            value = input(f"    {prompt_text}: ")
        return value.strip() if value.strip() else None
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _confirm(prompt_text: str, default: bool = True) -> bool:
    """Ask user a yes/no question."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"    {prompt_text} {suffix} ").strip().lower()
        if not answer:
            return default
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _run_command(
    cmd: list[str], check: bool = False, **kwargs: object
) -> subprocess.CompletedProcess[str]:
    """Run a command and return result."""
    return subprocess.run(
        cmd, capture_output=True, text=True, check=check, **kwargs  # type: ignore[arg-type]
    )


# --- Platform install hints ---

_GH_INSTALL_HINTS: dict[str, list[str]] = {
    "macOS": ["brew install gh"],
    "Linux (Debian/Ubuntu)": ["sudo apt-get install gh"],
    "Linux (Fedora/RHEL)": ["sudo dnf install gh"],
    "Windows (scoop)": ["scoop install gh"],
    "Windows (choco)": ["choco install gh"],
    "Windows (winget)": ["winget install --id GitHub.cli"],
}

_IMAGEMAGICK_INSTALL_HINTS: dict[str, list[str]] = {
    "macOS": ["brew install imagemagick"],
    "Linux (Debian/Ubuntu)": ["sudo apt-get install imagemagick"],
    "Linux (Fedora/RHEL)": ["sudo dnf install ImageMagick"],
    "Windows (scoop)": ["scoop install imagemagick"],
    "Windows (choco)": ["choco install imagemagick"],
    "Windows (winget)": ["winget install --id ImageMagick.ImageMagick"],
}

_FFMPEG_INSTALL_HINTS: dict[str, list[str]] = {
    "macOS": ["brew install ffmpeg"],
    "Linux (Debian/Ubuntu)": ["sudo apt-get install ffmpeg"],
    "Linux (Fedora/RHEL)": ["sudo dnf install ffmpeg-free"],
    "Windows (scoop)": ["scoop install ffmpeg"],
    "Windows (choco)": ["choco install ffmpeg"],
    "Windows (winget)": ["winget install --id Gyan.FFmpeg"],
}


def _print_install_hints(hints: dict[str, list[str]], url: str) -> None:
    """Print platform-specific install commands."""
    print(f"    {BOLD}Install options:{NC}")
    for platform_name, cmds in hints.items():
        for cmd in cmds:
            print(f"      {DIM}{platform_name}:{NC} {cmd}")
    print(f"      {DIM}More info:{NC} {url}")


# --- GitHub CLI ---


def _install_gh() -> bool:
    """Attempt to install GitHub CLI based on platform."""
    if IS_MACOS:
        if shutil.which("brew"):
            print(f"    {YELLOW}Installing gh via Homebrew...{NC}")
            result = subprocess.run(
                ["brew", "install", "gh"], capture_output=False
            )
            return result.returncode == 0
        else:
            print(f"    {RED}Homebrew not found.{NC} Install gh manually:")
            _print_install_hints(_GH_INSTALL_HINTS, "https://cli.github.com/")
            return False
    elif IS_LINUX:
        if shutil.which("apt-get"):
            print(f"    {YELLOW}Installing gh via apt...{NC}")
            cmds = [
                "type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)",
                "sudo mkdir -p -m 755 /etc/apt/keyrings",
                'out=$(mktemp) && wget -nv -O"$out" https://cli.github.com/packages/githubcli-archive-keyring.gpg'
                ' && cat "$out" | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null'
                " && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg",
                "sudo mkdir -p -m 755 /etc/apt/sources.list.d",
                'echo "deb [arch=$(dpkg --print-architecture)'
                " signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg]"
                ' https://cli.github.com/packages stable main"'
                " | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null",
                "sudo apt update && sudo apt install gh -y",
            ]
            for cmd in cmds:
                result = subprocess.run(cmd, shell=True)
                if result.returncode != 0:
                    print(f"    {RED}Installation step failed.{NC}")
                    return False
            return True
        elif shutil.which("dnf"):
            print(f"    {YELLOW}Installing gh via dnf...{NC}")
            result = subprocess.run(
                ["sudo", "dnf", "install", "-y", "gh"], capture_output=False
            )
            return result.returncode == 0
        else:
            print(f"    {RED}No supported package manager found.{NC}")
            _print_install_hints(_GH_INSTALL_HINTS, "https://cli.github.com/")
            return False
    elif IS_WINDOWS:
        if shutil.which("scoop"):
            print(f"    {YELLOW}Installing gh via scoop...{NC}")
            result = subprocess.run(
                ["scoop", "install", "gh"], capture_output=False
            )
            return result.returncode == 0
        elif shutil.which("choco"):
            print(f"    {YELLOW}Installing gh via Chocolatey...{NC}")
            result = subprocess.run(
                ["choco", "install", "gh", "-y"], capture_output=False
            )
            return result.returncode == 0
        elif shutil.which("winget"):
            print(f"    {YELLOW}Installing gh via winget...{NC}")
            result = subprocess.run(
                ["winget", "install", "--id", "GitHub.cli"],
                capture_output=False,
            )
            return result.returncode == 0
        else:
            print(f"    {RED}No package manager found (scoop/choco/winget).{NC}")
            _print_install_hints(_GH_INSTALL_HINTS, "https://cli.github.com/")
            return False
    return False


def check_gh_operations(config_path: Path) -> bool:
    """Check and configure GitHub CLI."""
    print(f"\n{BOLD}GitHub CLI (gh):{NC}")

    if not shutil.which("gh"):
        print(f"  Status:   {RED}NOT INSTALLED{NC}")
        if _confirm("Install gh now?"):
            if not _install_gh():
                return False
            if not shutil.which("gh"):
                print(f"    {RED}gh still not found after install.{NC}")
                return False
            print(f"    {GREEN}gh installed successfully.{NC}")
        else:
            print(f"    {DIM}Skipped.{NC} Install manually:")
            _print_install_hints(_GH_INSTALL_HINTS, "https://cli.github.com/")
            return False

    gh_auth = _run_command(["gh", "auth", "status"])
    if gh_auth.returncode != 0:
        print(f"  Status:   {YELLOW}installed, NOT AUTHENTICATED{NC}")
        if _confirm("Run 'gh auth login' now?"):
            subprocess.run(["gh", "auth", "login"])
            gh_auth = _run_command(["gh", "auth", "status"])
            if gh_auth.returncode != 0:
                print(f"    {RED}Authentication failed or cancelled.{NC}")
                return False
        else:
            print(f"    {DIM}Skipped. Run 'gh auth login' manually.{NC}")
            return False

    print(f"  Status:   {GREEN}installed, authenticated{NC}")
    return True


# --- Jira ---


def check_atlassian(config_path: Path) -> bool:
    """Check and configure Atlassian credentials (shared by Jira and Confluence)."""
    print(f"\n{BOLD}Atlassian (Jira / Confluence):{NC}")

    all_ok = True

    token = os.environ.get("ATLASSIAN_API_TOKEN")
    if token:
        masked = f"...{token[-4:]}" if len(token) >= 4 else "set"
        print(f"  ATLASSIAN_API_TOKEN:   {GREEN}set{NC} (ending in {masked})")
    else:
        print(f"  ATLASSIAN_API_TOKEN:   {RED}NOT SET{NC}")
        print("    How to get it:")
        print(f"    1. Open {BOLD}https://id.atlassian.com/manage-profile/security/api-tokens{NC}")
        print('    2. Click "Create API token", copy the token')
        value = _prompt_value("Paste your Atlassian API token (or Enter to skip)", secret=True)
        if value:
            _append_env_var(config_path, "ATLASSIAN_API_TOKEN", value)
        else:
            all_ok = False

    email = os.environ.get("ATLASSIAN_USER_EMAIL")
    if email:
        print(f"  ATLASSIAN_USER_EMAIL:  {GREEN}{email}{NC}")
    else:
        print(f"  ATLASSIAN_USER_EMAIL:  {RED}NOT SET{NC} (Required for Jira Cloud)")
        value = _prompt_value("Enter your Atlassian account email (or Enter to skip)")
        if value:
            _append_env_var(config_path, "ATLASSIAN_USER_EMAIL", value)
        else:
            all_ok = False

    url = os.environ.get("ATLASSIAN_BASE_URL")
    if url:
        print(f"  ATLASSIAN_BASE_URL:    {GREEN}{url}{NC}")
    else:
        print(f"  ATLASSIAN_BASE_URL:    {YELLOW}NOT SET{NC} (Optional, recommended)")
        print("    Example: https://yourcompany.atlassian.net")
        value = _prompt_value("Enter your Atlassian base URL (or Enter to skip)")
        if value:
            _append_env_var(config_path, "ATLASSIAN_BASE_URL", value)

    return all_ok


# --- Figma ---


def check_figma(config_path: Path) -> bool:
    """Check and configure Figma access token."""
    print(f"\n{BOLD}Figma:{NC}")

    token = os.environ.get("FIGMA_ACCESS_TOKEN")
    if token:
        masked = f"...{token[-4:]}" if len(token) >= 4 else "set"
        print(f"  FIGMA_ACCESS_TOKEN:  {GREEN}set{NC} (ending in {masked})")
        return True

    print(f"  FIGMA_ACCESS_TOKEN:  {RED}NOT SET{NC}")
    print("    How to get it:")
    print(f"    1. Open {BOLD}https://www.figma.com/settings{NC}")
    print('    2. Under "Personal access tokens", generate a new token')
    print("    3. Grant at least: File content -> Read only")
    value = _prompt_value(
        "Paste your Figma access token (or Enter to skip)", secret=True
    )
    if value:
        _append_env_var(config_path, "FIGMA_ACCESS_TOKEN", value)
        return True
    return False


# --- ImageMagick ---


def _install_imagemagick() -> bool:
    """Attempt to install ImageMagick based on platform."""
    if IS_MACOS:
        if shutil.which("brew"):
            print(f"    {YELLOW}Installing ImageMagick via Homebrew...{NC}")
            result = subprocess.run(
                ["brew", "install", "imagemagick"], capture_output=False
            )
            return result.returncode == 0
        else:
            print(f"    {RED}Homebrew not found.{NC} Install ImageMagick manually:")
            _print_install_hints(
                _IMAGEMAGICK_INSTALL_HINTS,
                "https://imagemagick.org/script/download.php",
            )
            return False
    elif IS_LINUX:
        if shutil.which("apt-get"):
            print(f"    {YELLOW}Installing ImageMagick via apt...{NC}")
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "imagemagick"],
                capture_output=False,
            )
            return result.returncode == 0
        elif shutil.which("dnf"):
            print(f"    {YELLOW}Installing ImageMagick via dnf...{NC}")
            result = subprocess.run(
                ["sudo", "dnf", "install", "-y", "ImageMagick"],
                capture_output=False,
            )
            return result.returncode == 0
        else:
            print(f"    {RED}No supported package manager found.{NC}")
            _print_install_hints(
                _IMAGEMAGICK_INSTALL_HINTS,
                "https://imagemagick.org/script/download.php",
            )
            return False
    elif IS_WINDOWS:
        if shutil.which("scoop"):
            print(f"    {YELLOW}Installing ImageMagick via scoop...{NC}")
            result = subprocess.run(
                ["scoop", "install", "imagemagick"], capture_output=False
            )
            return result.returncode == 0
        elif shutil.which("choco"):
            print(f"    {YELLOW}Installing ImageMagick via Chocolatey...{NC}")
            result = subprocess.run(
                ["choco", "install", "imagemagick", "-y"], capture_output=False
            )
            return result.returncode == 0
        elif shutil.which("winget"):
            print(f"    {YELLOW}Installing ImageMagick via winget...{NC}")
            result = subprocess.run(
                ["winget", "install", "--id", "ImageMagick.ImageMagick"],
                capture_output=False,
            )
            return result.returncode == 0
        else:
            print(f"    {RED}No package manager found (scoop/choco/winget).{NC}")
            _print_install_hints(
                _IMAGEMAGICK_INSTALL_HINTS,
                "https://imagemagick.org/script/download.php",
            )
            return False
    return False


def check_imagemagick(config_path: Path) -> bool:
    """Check and configure ImageMagick CLI."""
    print(f"\n{BOLD}ImageMagick (magick):{NC}")

    if not shutil.which("magick"):
        print(f"  Status:   {RED}NOT INSTALLED{NC}")
        if _confirm("Install ImageMagick now?"):
            if not _install_imagemagick():
                return False
            if not shutil.which("magick"):
                print(f"    {RED}magick still not found after install.{NC}")
                return False
            print(f"    {GREEN}ImageMagick installed successfully.{NC}")
        else:
            print(f"    {DIM}Skipped.{NC} Install manually:")
            _print_install_hints(
                _IMAGEMAGICK_INSTALL_HINTS,
                "https://imagemagick.org/script/download.php",
            )
            return False

    version = _run_command(["magick", "-version"])
    if version.returncode == 0:
        first_line = version.stdout.strip().splitlines()[0] if version.stdout.strip() else ""
        print(f"  Status:   {GREEN}installed{NC}")
        if first_line:
            print(f"  Version:  {DIM}{first_line}{NC}")
    else:
        print(f"  Status:   {GREEN}installed{NC}")

    return True


# --- FFmpeg ---


def _install_ffmpeg() -> bool:
    """Attempt to install FFmpeg based on platform."""
    if IS_MACOS:
        if shutil.which("brew"):
            print(f"    {YELLOW}Installing FFmpeg via Homebrew...{NC}")
            result = subprocess.run(
                ["brew", "install", "ffmpeg"], capture_output=False
            )
            return result.returncode == 0
        else:
            print(f"    {RED}Homebrew not found.{NC} Install FFmpeg manually:")
            _print_install_hints(
                _FFMPEG_INSTALL_HINTS, "https://ffmpeg.org/download.html"
            )
            return False
    elif IS_LINUX:
        if shutil.which("apt-get"):
            print(f"    {YELLOW}Installing FFmpeg via apt...{NC}")
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "ffmpeg"],
                capture_output=False,
            )
            return result.returncode == 0
        elif shutil.which("dnf"):
            print(f"    {YELLOW}Installing FFmpeg via dnf...{NC}")
            result = subprocess.run(
                ["sudo", "dnf", "install", "-y", "ffmpeg-free"],
                capture_output=False,
            )
            return result.returncode == 0
        else:
            print(f"    {RED}No supported package manager found.{NC}")
            _print_install_hints(
                _FFMPEG_INSTALL_HINTS, "https://ffmpeg.org/download.html"
            )
            return False
    elif IS_WINDOWS:
        if shutil.which("scoop"):
            print(f"    {YELLOW}Installing FFmpeg via scoop...{NC}")
            result = subprocess.run(
                ["scoop", "install", "ffmpeg"], capture_output=False
            )
            return result.returncode == 0
        elif shutil.which("choco"):
            print(f"    {YELLOW}Installing FFmpeg via Chocolatey...{NC}")
            result = subprocess.run(
                ["choco", "install", "ffmpeg", "-y"], capture_output=False
            )
            return result.returncode == 0
        elif shutil.which("winget"):
            print(f"    {YELLOW}Installing FFmpeg via winget...{NC}")
            result = subprocess.run(
                ["winget", "install", "--id", "Gyan.FFmpeg"],
                capture_output=False,
            )
            return result.returncode == 0
        else:
            print(f"    {RED}No package manager found (scoop/choco/winget).{NC}")
            _print_install_hints(
                _FFMPEG_INSTALL_HINTS, "https://ffmpeg.org/download.html"
            )
            return False
    return False


def check_ffmpeg(config_path: Path) -> bool:
    """Check and configure FFmpeg CLI."""
    print(f"\n{BOLD}FFmpeg (ffmpeg / ffprobe):{NC}")

    if not shutil.which("ffmpeg"):
        print(f"  Status:   {RED}NOT INSTALLED{NC}")
        if _confirm("Install FFmpeg now?"):
            if not _install_ffmpeg():
                return False
            if not shutil.which("ffmpeg"):
                print(f"    {RED}ffmpeg still not found after install.{NC}")
                return False
            print(f"    {GREEN}FFmpeg installed successfully.{NC}")
        else:
            print(f"    {DIM}Skipped.{NC} Install manually:")
            _print_install_hints(
                _FFMPEG_INSTALL_HINTS, "https://ffmpeg.org/download.html"
            )
            return False

    version = _run_command(["ffmpeg", "-version"])
    if version.returncode == 0:
        first_line = version.stdout.strip().splitlines()[0] if version.stdout.strip() else ""
        print(f"  Status:   {GREEN}installed{NC}")
        if first_line:
            print(f"  Version:  {DIM}{first_line}{NC}")
    else:
        print(f"  Status:   {GREEN}installed{NC}")

    if not shutil.which("ffprobe"):
        print(f"  ffprobe:  {YELLOW}NOT FOUND{NC} (usually bundled with ffmpeg)")
    else:
        print(f"  ffprobe:  {GREEN}available{NC}")

    return True


# --- Git ---


_GIT_INSTALL_HINTS: dict[str, list[str]] = {
    "macOS": ["xcode-select --install", "brew install git"],
    "Linux (Debian/Ubuntu)": ["sudo apt-get install git"],
    "Linux (Fedora/RHEL)": ["sudo dnf install git"],
    "Windows (scoop)": ["scoop install git"],
    "Windows (choco)": ["choco install git"],
    "Windows (winget)": ["winget install --id Git.Git"],
}


def check_git(config_path: Path) -> bool:
    """Check that git CLI is installed and functional."""
    print(f"\n{BOLD}Git (git):{NC}")

    if not shutil.which("git"):
        print(f"  Status:   {RED}NOT INSTALLED{NC}")
        print(f"    {BOLD}Install options:{NC}")
        _print_install_hints(_GIT_INSTALL_HINTS, "https://git-scm.com/downloads")
        return False

    version = _run_command(["git", "--version"])
    if version.returncode == 0:
        first_line = version.stdout.strip().splitlines()[0] if version.stdout.strip() else ""
        print(f"  Status:   {GREEN}installed{NC}")
        if first_line:
            print(f"  Version:  {DIM}{first_line}{NC}")
    else:
        print(f"  Status:   {GREEN}installed{NC}")

    return True


# --- Curses multi-select UI ---


def curses_multi_select(
    stdscr: curses.window,
    title: str,
    items: list[str],
    preselected: list[bool] | None = None,
) -> list[int] | None:
    """Interactive multi-select with arrow keys, space, and enter.

    Returns list of selected indices, or None if user cancelled (q/Esc).
    """
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)

    selected = list(preselected) if preselected else [True] * len(items)
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


def select_skills_interactive() -> list[str] | None:
    """Launch curses UI to select skills to check. Returns skill names or None."""
    indices = curses.wrapper(
        curses_multi_select,
        "Select skills to check:",
        CHECKABLE_SKILLS,
        [True] * len(CHECKABLE_SKILLS),
    )
    if indices is None:
        return None
    return [CHECKABLE_SKILLS[i] for i in indices]


# --- Main ---


def main() -> None:
    skills = sys.argv[1:]
    if not skills:
        skills_selection = select_skills_interactive()
        if skills_selection is None or len(skills_selection) == 0:
            print("No skills selected. Aborted.")
            return
        skills = skills_selection

    needs_config = any(s in skills for s in CHECKABLE_SKILLS)

    if not needs_config:
        return

    config_path = _detect_shell_config()
    print(f"\n{BOLD}=== Skills Dependency Check ==={NC}")
    print(f"  Shell config: {DIM}{config_path}{NC}")

    all_configured = True

    if SKILL_GH_OPERATIONS in skills or SKILL_CODE_REVIEW_PR in skills:
        if not check_gh_operations(config_path):
            all_configured = False

    if SKILL_JIRA in skills or SKILL_CONFLUENCE in skills:
        if not check_atlassian(config_path):
            all_configured = False

    if SKILL_FIGMA in skills:
        if not check_figma(config_path):
            all_configured = False

    if SKILL_IMAGEMAGICK in skills:
        if not check_imagemagick(config_path):
            all_configured = False

    if SKILL_FFMPEG in skills:
        if not check_ffmpeg(config_path):
            all_configured = False

    if SKILL_GIT_REPO_READER in skills:
        if not check_git(config_path):
            all_configured = False

    print()
    if all_configured:
        print(
            f"{GREEN}All dependencies configured.{NC} "
            f"Run {BOLD}source {config_path}{NC} to apply changes."
        )
    else:
        print(
            f"{YELLOW}Some dependencies are missing.{NC} "
            f"Run {BOLD}skills-check{NC} again after configuring them."
        )


if __name__ == "__main__":
    main()
