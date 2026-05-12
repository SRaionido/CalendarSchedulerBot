"""
bot.py - Entry point for the Discord Scheduler Bot.

Run with:
  python bot.py

Environment variables (set in .env):
  DISCORD_TOKEN   – your bot token (required)
  STORAGE_BACKEND – "json" (default) | future: "sqlite", "postgres"
  DATA_DIR        – directory for data files (default: ./data)
"""

import asyncio
import logging
import sys

import discord
from discord.ext import commands

import config as config
from storage import get_storage
from commands.availability import setup as setup_availability
from commands.calendar_view import setup as setup_calendar
from commands.events        import setup as setup_events
from tasks.cleanup          import setup as setup_cleanup

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("scheduler-bot")

# ── Bot setup ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot     = commands.Bot(command_prefix="!", intents=intents)
storage = get_storage()


@bot.event
async def on_ready() -> None:
    log.info(f"Logged in as {bot.user} (id={bot.user.id})")
    log.info(f"Storage backend: {config.STORAGE_BACKEND}")
    try:
        # Global sync — commands appear in all servers within ~1 hour.
        # For instant dev testing, pass guild=discord.Object(id=YOUR_GUILD_ID)
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash command(s) globally.")
    except Exception as exc:
        log.error(f"Failed to sync commands: {exc}")


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    log.info(f"Joined guild: {guild.name} (id={guild.id})")


# ── Main ───────────────────────────────────────────────────────────────────────
async def main() -> None:
    if not config.DISCORD_TOKEN:
        log.error(
            "DISCORD_TOKEN is not set. "
            "Copy .env.example to .env and fill in your bot token."
        )
        sys.exit(1)

    async with bot:
        await setup_availability(bot, storage)
        await setup_calendar(bot, storage)
        await setup_events(bot, storage)
        await setup_cleanup(bot, storage)
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())