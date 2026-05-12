"""
commands/availability.py - Slash commands for managing personal availability.

Commands:
  /add_availability    – Save available time windows for a specific date
  /remove_availability – Remove availability for a date
  /my_availability     – View your own saved availability
  /clear_month         – Wipe all your availability for a whole month
"""

from datetime import date as date_cls
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from storage.base import BaseStorage
from utils.time_parser import (
    format_time_ranges,
    parse_date,
    parse_time_range,
    parse_year_month,
)


class AvailabilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot, storage: BaseStorage) -> None:
        self.bot     = bot
        self.storage = storage

    # ── /add_availability ──────────────────────────────────────────────────────

    @app_commands.command(
        name="add_availability",
        description="Save your available hours for a date (up to 3 time windows).",
    )
    @app_commands.describe(
        date   = "Date in YYYY-MM-DD format, e.g. 2025-07-04",
        start1 = "First window start — e.g. 09:00 or 9am",
        end1   = "First window end   — e.g. 12:00 or noon",
        start2 = "(Optional) Second window start",
        end2   = "(Optional) Second window end",
        start3 = "(Optional) Third window start",
        end3   = "(Optional) Third window end",
    )
    async def add_availability(
        self,
        interaction: discord.Interaction,
        date:   str,
        start1: str,
        end1:   str,
        start2: Optional[str] = None,
        end2:   Optional[str] = None,
        start3: Optional[str] = None,
        end3:   Optional[str] = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        date_str = parse_date(date)
        if date_str is None:
            await interaction.followup.send(
                "❌ Invalid date. Use `YYYY-MM-DD`, e.g. `2025-07-04`.",
                ephemeral=True,
            )
            return

        if date_str < date_cls.today().isoformat():
            await interaction.followup.send(
                "❌ Date must be today or in the future.", ephemeral=True
            )
            return

        raw_pairs = [(start1, end1)]
        if start2 and end2:
            raw_pairs.append((start2, end2))
        if start3 and end3:
            raw_pairs.append((start3, end3))

        time_ranges = []
        for s, e in raw_pairs:
            tr = parse_time_range(s, e)
            if tr is None:
                await interaction.followup.send(
                    f"❌ Invalid time range `{s}` – `{e}`. "
                    "Use HH:MM (24-hour) or 9am style, and end must be after start.",
                    ephemeral=True,
                )
                return
            time_ranges.append(tr)

        self.storage.add_availability(
            guild_id    = str(interaction.guild_id),
            user_id     = str(interaction.user.id),
            username    = interaction.user.display_name,
            date        = date_str,
            time_ranges = time_ranges,
        )

        await interaction.followup.send(
            f"✅ Saved availability for **{date_str}**: {format_time_ranges(time_ranges)}",
            ephemeral=True,
        )

    # ── /remove_availability ───────────────────────────────────────────────────

    @app_commands.command(
        name="remove_availability",
        description="Remove all your availability for a specific date.",
    )
    @app_commands.describe(date="Date in YYYY-MM-DD format")
    async def remove_availability(
        self,
        interaction: discord.Interaction,
        date: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        date_str = parse_date(date)
        if date_str is None:
            await interaction.followup.send(
                "❌ Invalid date. Use `YYYY-MM-DD`.", ephemeral=True
            )
            return

        removed = self.storage.remove_availability(
            guild_id = str(interaction.guild_id),
            user_id  = str(interaction.user.id),
            date     = date_str,
        )

        if removed:
            await interaction.followup.send(
                f"🗑️ Removed your availability for **{date_str}**.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"ℹ️ No availability found for **{date_str}**.", ephemeral=True
            )

    # ── /my_availability ───────────────────────────────────────────────────────

    @app_commands.command(
        name="my_availability",
        description="View your saved availability, optionally filtered to a month.",
    )
    @app_commands.describe(month="Optional: YYYY-MM to filter, e.g. 2025-07")
    async def my_availability(
        self,
        interaction: discord.Interaction,
        month: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        guild_id  = str(interaction.guild_id)
        user_id   = str(interaction.user.id)
        all_avail = self.storage.get_availability_for_user(guild_id, user_id)

        if month:
            ym = parse_year_month(month)
            if ym is None:
                await interaction.followup.send(
                    "❌ Invalid month. Use `YYYY-MM`.", ephemeral=True
                )
                return
            prefix    = f"{ym[0]}-{ym[1]:02d}-"
            all_avail = {d: v for d, v in all_avail.items() if d.startswith(prefix)}

        if not all_avail:
            suffix = f" for **{month}**" if month else ""
            await interaction.followup.send(
                f"ℹ️ No availability saved{suffix}.", ephemeral=True
            )
            return

        lines = ["**Your availability:**"]
        for day in sorted(all_avail):
            lines.append(f"• **{day}**: {format_time_ranges(all_avail[day])}")

        msg = "\n".join(lines)
        if len(msg) > 1900:
            msg = msg[:1900] + "\n…(truncated)"

        await interaction.followup.send(msg, ephemeral=True)

    # ── /clear_month ───────────────────────────────────────────────────────────

    @app_commands.command(
        name="clear_month",
        description="Clear all your availability entries for an entire month.",
    )
    @app_commands.describe(month="Month in YYYY-MM format, e.g. 2025-07")
    async def clear_month(
        self,
        interaction: discord.Interaction,
        month: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        ym = parse_year_month(month)
        if ym is None:
            await interaction.followup.send(
                "❌ Invalid month. Use `YYYY-MM`.", ephemeral=True
            )
            return

        count = self.storage.clear_user_month(
            guild_id = str(interaction.guild_id),
            user_id  = str(interaction.user.id),
            year     = ym[0],
            month    = ym[1],
        )

        if count:
            await interaction.followup.send(
                f"🗑️ Removed {count} day(s) of availability for **{month}**.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"ℹ️ No availability found for **{month}**.", ephemeral=True
            )


async def setup(bot: commands.Bot, storage: BaseStorage) -> None:
    await bot.add_cog(AvailabilityCog(bot, storage))