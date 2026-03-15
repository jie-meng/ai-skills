#!/usr/bin/env python3
"""Backward-compatible wrapper. Prefer: skills-clean-cache (after pip install)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mythril_agent_skills.cli.skills_clean_cache import main  # noqa: E402

if __name__ == "__main__":
    main()
