"""
config.py - Central configuration for the Discord Scheduler Bot.

All values can be overridden via environment variables in your .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Discord ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# ── Storage ────────────────────────────────────────────────────────────────────
# To switch backends, change STORAGE_BACKEND and add any connection config
# (e.g. DATABASE_URL) here. See storage/__init__.py for the factory.
STORAGE_BACKEND: str   = os.getenv("STORAGE_BACKEND", "json")
DATA_DIR: str          = os.getenv("DATA_DIR", "./data")
AVAILABILITY_FILE: str = os.path.join(DATA_DIR, "availability.json")
EVENTS_FILE: str       = os.path.join(DATA_DIR, "events.json")

# ── Calendar rendering ─────────────────────────────────────────────────────────
CALENDAR_OUTPUT_DIR: str = os.getenv("CALENDAR_OUTPUT_DIR", "./data/renders")
CALENDAR_DPI: int        = 150

# ── Timezone ───────────────────────────────────────────────────────────────────
DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "America/Los_Angeles")