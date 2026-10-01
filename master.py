#!/usr/bin/env python3
"""
Legacy entrypoint for Cold-Emails-Automation.
Delegates to the modern, modular coldmail engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to path so this script can be executed directly without installation
sys.path.insert(0, str(Path(__file__).parent / "src"))

from coldmail.cli import app

if __name__ == "__main__":
    app()