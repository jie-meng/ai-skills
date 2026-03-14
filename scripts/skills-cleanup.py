#!/usr/bin/env python3
"""Backward-compatible wrapper. Prefer: skills-cleanup (after pip install)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mythril_agent_skills.cli.skills_cleanup import main  # noqa: E402

if __name__ == "__main__":
    main()
