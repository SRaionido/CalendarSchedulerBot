"""
commands/calendar_view.py - Slash command that renders and posts a monthly
calendar image showing all members' availability as coloured hour blocks.

Commands:
  /view_month – Generate and post the calendar image for a given month
"""

import os
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from storage.base import BaseStorage
from utils.time_parser import parse_year_month
from utils.calendar_render import render_month


class CalendarViewCog(commands.Cog):
    def __init__(self, bot: commands.Bot, storage: BaseStorage) -> None:
        self.bot     = bot
        self.storage = storage

    @app_commands.command(
        name="view_month",
        description="Post a calendar image showing everyone's availability for a month.",
    )
    @app_commands.describe(
        month="Month in YYYY-MM format — defaults to the current month"
    )
    async def view_month(
        self,
        interaction: discord.Interaction,
        month: Optional[str] = None,
    ) -> None:
        await interaction.response.defer()

        if month:
            ym = parse_year_month(month)
            if ym is None:
                await interaction.followup.send(
                    "❌ Invalid month. Use `YYYY-MM`, e.g. `2025-07`."
                )
                return
            year, mon = ym
        else:
            now  = datetime.utcnow()
            year = now.year
            mon  = now.month

        guild_id  = str(interaction.guild_id)
        avail     = self.storage.get_availability_for_month(guild_id, year, mon)
        usernames = self.storage.get_usernames(guild_id)

        month_label = f"{year}-{mon:02d}"

        if not avail:
            await interaction.followup.send(
                f"ℹ️ No availability data found for **{month_label}**. "
                "Members can add theirs with `/add_availability`."
            )
            return

        # Render the PNG (synchronous — acceptable for small servers;
        # wrap in asyncio.to_thread() if you need fully non-blocking rendering)
        img_path = render_month(year, mon, avail, usernames)

        try:
            with open(img_path, "rb") as f:
                await interaction.followup.send(
                    content=f"📅 **Availability for {month_label}**",
                    file=discord.File(f, filename=f"availability_{month_label}.png"),
                )
        finally:
            try:
                os.remove(img_path)
            except OSError:
                pass


async def setup(bot: commands.Bot, storage: BaseStorage) -> None:
    await bot.add_cog(CalendarViewCog(bot, storage))