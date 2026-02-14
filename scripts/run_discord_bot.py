#!/usr/bin/env python3
"""Standalone launcher for the PULSAR SENTINEL Discord bot.

Usage:
    python scripts/run_discord_bot.py

Requires DISCORD_BOT_TOKEN in .env file.
Lightweight process (~30-50MB RAM), runs separately from the FastAPI server.
"""

import sys
from pathlib import Path

# Add project root and src to path (do NOT add config/ directly - it shadows stdlib logging)
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from discord_bot.bot import run_bot

if __name__ == "__main__":
    run_bot()
