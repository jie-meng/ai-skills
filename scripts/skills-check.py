#!/usr/bin/env python3
import os
import subprocess
import sys

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"


def check_gh_operations() -> bool:
    print(f"\n{BOLD}GitHub CLI (gh):{NC}")
    
    try:
        gh_version = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        if gh_version.returncode != 0:
            raise FileNotFoundError
    except FileNotFoundError:
        print(f"  Status:   {RED}NOT INSTALLED{NC}")
        print("  To install:")
        print("    macOS:   brew install gh")
        print("    Windows: winget install --id GitHub.cli")
        print("    Linux:   See https://github.com/cli/cli/blob/trunk/docs/install_linux.md")
        return False

    gh_auth = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if gh_auth.returncode != 0:
        print(f"  Status:   {RED}installed, NOT AUTHENTICATED{NC}")
        print("  To authenticate, run:")
        print(f"    {YELLOW}gh auth login{NC}")
        return False
    else:
        print(f"  Status:   {GREEN}installed, authenticated{NC}")
        print("  Config:   gh manages its own auth (run `gh auth status` to inspect)")
        return True


def check_jira() -> bool:
    print(f"\n{BOLD}Jira:{NC}")
    
    all_ok = True
    
    token = os.environ.get("JIRA_API_TOKEN")
    if token:
        masked_token = f"...{token[-4:]}" if len(token) >= 4 else "set"
        print(f"  JIRA_API_TOKEN:   {GREEN}set{NC} (token ending in {masked_token})")
    else:
        print(f"  JIRA_API_TOKEN:   {RED}NOT SET{NC}")
        print("    1. Open https://id.atlassian.com/manage-profile/security/api-tokens")
        print("    2. Create API token, copy it, and add to your shell config:")
        print(f"       {YELLOW}export JIRA_API_TOKEN=\"<token>\"{NC}")
        all_ok = False

    email = os.environ.get("JIRA_USER_EMAIL")
    if email:
        print(f"  JIRA_USER_EMAIL:  {GREEN}{email}{NC}")
    else:
        print(f"  JIRA_USER_EMAIL:  {RED}NOT SET{NC} (Required for Jira Cloud)")
        print("    Add to your shell config:")
        print(f"       {YELLOW}export JIRA_USER_EMAIL=\"<email>\"{NC}")
        all_ok = False

    url = os.environ.get("JIRA_BASE_URL")
    if url:
        print(f"  JIRA_BASE_URL:    {GREEN}{url}{NC}")
    else:
        print(f"  JIRA_BASE_URL:    {YELLOW}NOT SET{NC} (Optional but recommended)")
        print("    Add to your shell config:")
        print(f"       {YELLOW}export JIRA_BASE_URL=\"<url>\"{NC}")

    return all_ok


def check_figma() -> bool:
    print(f"\n{BOLD}Figma:{NC}")
    
    token = os.environ.get("FIGMA_ACCESS_TOKEN")
    if token:
        masked_token = f"...{token[-4:]}" if len(token) >= 4 else "set"
        print(f"  FIGMA_ACCESS_TOKEN:  {GREEN}set{NC} (token ending in {masked_token})")
        return True
    else:
        print(f"  FIGMA_ACCESS_TOKEN:  {RED}NOT SET{NC}")
        print("    1. Open https://www.figma.com/settings")
        print("    2. Generate new personal access token (File content -> Read only)")
        print("    3. Add to your shell config:")
        print(f"       {YELLOW}export FIGMA_ACCESS_TOKEN=\"<token>\"{NC}")
        return False


def main() -> None:
    skills = sys.argv[1:]
    if not skills:
        return

    needs_config = any(s in skills for s in ["gh-operations", "jira", "figma"])
    
    if needs_config:
        print(f"\n{BOLD}=== ai-skills Configuration Summary ==={NC}")

    all_configured = True

    if "gh-operations" in skills:
        if not check_gh_operations():
            all_configured = False

    if "jira" in skills:
        if not check_jira():
            all_configured = False

    if "figma" in skills:
        if not check_figma():
            all_configured = False

    if needs_config:
        print("")
        if all_configured:
            print("All configured. To update any value, edit the corresponding")
            print("line in your shell config file and run `source ~/.zshrc` (or equivalent).")
        else:
            print(f"{YELLOW}Some required dependencies or environment variables are missing.{NC}")
            print("Please follow the instructions above to configure them, then run:")
            print("`source ~/.zshrc` (or your corresponding shell config).")


if __name__ == "__main__":
    main()
