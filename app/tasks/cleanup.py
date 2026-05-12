"""
tasks/cleanup.py - Background task that purges past data every 24 hours.

Fires immediately on startup (so stale data from any downtime is cleared
right away), then repeats every 24 hours. Results are logged each run.
"""

import logging
from datetime import date

from discord.ext import commands, tasks

from storage.base import BaseStorage

log = logging.getLogger("scheduler-bot.cleanup")


class CleanupTask(commands.Cog):
    def __init__(self, bot: commands.Bot, storage: BaseStorage) -> None:
        self.bot     = bot
        self.storage = storage
        self.daily_purge.start()

    def cog_unload(self) -> None:
        self.daily_purge.cancel()

    @tasks.loop(hours=24)
    async def daily_purge(self) -> None:
        today = date.today().isoformat()
        try:
            counts = self.storage.purge_past_data(today)
            log.info(
                f"Daily purge complete — removed {counts['availability']} "
                f"availability entry/entries and {counts['events']} past event(s) "
                f"(cutoff: {today})."
            )
        except Exception as exc:
            log.error(f"Daily purge failed: {exc}", exc_info=True)

    @daily_purge.before_loop
    async def before_purge(self) -> None:
        """Wait for the bot to be fully connected before the first run."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot, storage: BaseStorage) -> None:
    await bot.add_cog(CleanupTask(bot, storage))