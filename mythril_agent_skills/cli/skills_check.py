#!/usr/bin/env python3
"""Skills Check - Interactive dependency checker and configurator.

Checks CLI tools and environment variables required by installed skills.
Automatically installs missing CLI tools (with user confirmation), prompts
for missing API keys/tokens, and saves them to the user's shell config file.

Usage:
    skills-check                    # Check all skills
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

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


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
            print("      https://cli.github.com/")
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
            print("      Install manually: https://cli.github.com/")
            return False
    elif IS_WINDOWS:
        if shutil.which("winget"):
            print(f"    {YELLOW}Installing gh via winget...{NC}")
            result = subprocess.run(
                ["winget", "install", "--id", "GitHub.cli"],
                capture_output=False,
            )
            return result.returncode == 0
        else:
            print(f"    {RED}winget not found.{NC} Install gh manually:")
            print("      https://cli.github.com/")
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
            print(f"    {DIM}Skipped. Install manually: https://cli.github.com/{NC}")
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


def check_jira(config_path: Path) -> bool:
    """Check and configure Jira credentials."""
    print(f"\n{BOLD}Jira:{NC}")

    all_ok = True

    token = os.environ.get("JIRA_API_TOKEN")
    if token:
        masked = f"...{token[-4:]}" if len(token) >= 4 else "set"
        print(f"  JIRA_API_TOKEN:   {GREEN}set{NC} (ending in {masked})")
    else:
        print(f"  JIRA_API_TOKEN:   {RED}NOT SET{NC}")
        print("    How to get it:")
        print(f"    1. Open {BOLD}https://id.atlassian.com/manage-profile/security/api-tokens{NC}")
        print('    2. Click "Create API token", copy the token')
        value = _prompt_value("Paste your Jira API token (or Enter to skip)", secret=True)
        if value:
            _append_env_var(config_path, "JIRA_API_TOKEN", value)
        else:
            all_ok = False

    email = os.environ.get("JIRA_USER_EMAIL")
    if email:
        print(f"  JIRA_USER_EMAIL:  {GREEN}{email}{NC}")
    else:
        print(f"  JIRA_USER_EMAIL:  {RED}NOT SET{NC} (Required for Jira Cloud)")
        value = _prompt_value("Enter your Atlassian account email (or Enter to skip)")
        if value:
            _append_env_var(config_path, "JIRA_USER_EMAIL", value)
        else:
            all_ok = False

    url = os.environ.get("JIRA_BASE_URL")
    if url:
        print(f"  JIRA_BASE_URL:    {GREEN}{url}{NC}")
    else:
        print(f"  JIRA_BASE_URL:    {YELLOW}NOT SET{NC} (Optional, recommended)")
        print("    Example: https://yourcompany.atlassian.net")
        value = _prompt_value("Enter your Jira base URL (or Enter to skip)")
        if value:
            _append_env_var(config_path, "JIRA_BASE_URL", value)

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


# --- Main ---


def main() -> None:
    skills = sys.argv[1:]
    if not skills:
        return

    needs_config = any(s in skills for s in ["gh-operations", "jira", "figma"])

    if not needs_config:
        return

    config_path = _detect_shell_config()
    print(f"\n{BOLD}=== Skills Dependency Check ==={NC}")
    print(f"  Shell config: {DIM}{config_path}{NC}")

    all_configured = True

    if "gh-operations" in skills:
        if not check_gh_operations(config_path):
            all_configured = False

    if "jira" in skills:
        if not check_jira(config_path):
            all_configured = False

    if "figma" in skills:
        if not check_figma(config_path):
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
