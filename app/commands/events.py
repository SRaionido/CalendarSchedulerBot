"""
commands/events.py - Slash commands for creating and managing events.

Commands:
  /create_event – Create a titled event with a date and time window
  /delete_event – Delete an event by its ID
  /upcoming     – List all upcoming events with Google Calendar links
"""

import uuid
from datetime import date as date_cls, datetime
# Import timezone utilities
from datetime import timezone, timedelta
from urllib.parse import urlencode

import discord
from discord import app_commands
from discord.ext import commands

from storage.base import BaseStorage, Event
from utils.time_parser import parse_date, parse_time_range


# ── Google Calendar link ───────────────────────────────────────────────────────

def _gcal_link(event: Event) -> str:
    """
    Build a Google Calendar 'add event' URL pre-filled with the event details.
    Requires no OAuth or bot account access — the user clicks the link and
    Google prompts them to save it to their own calendar.

    Google's date/time format: YYYYMMDDTHHmmss (compact, no separators).
    """
    date_str  = event["date"].replace("-", "")           # 20250704
    start_str = event["start_time"].replace(":", "") + "00"  # 180000
    end_str   = event["end_time"].replace(":", "")   + "00"  # 200000

    params = {
        "action": "TEMPLATE",
        "text":   event["title"],
        "dates":  f"{date_str}T{start_str}/{date_str}T{end_str}",
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


# ── Embed builder ──────────────────────────────────────────────────────────────

def _event_embed(event: Event) -> discord.Embed:
    """Build a Discord embed for a single event."""
    dt            = datetime.strptime(event["date"], "%Y-%m-%d")
    friendly_date = dt.strftime("%A, %B %-d %Y")  # e.g. Friday, July 4 2025

    embed = discord.Embed(title=event["title"], color=discord.Color.blurple())
    embed.add_field(name="📅 Date", value=friendly_date, inline=True)
    embed.add_field(
        name="⏰ Time",
        value=f"{event['start_time']} – {event['end_time']}",
        inline=True,
    )
    embed.add_field(name="🆔 ID", value=f"`{event['id']}`", inline=False)
    embed.add_field(
        name="📆 Add to Google Calendar",
        value=f"[Click here]({_gcal_link(event)})",
        inline=False,
    )
    embed.set_footer(text=f"Created by {event['created_by_name']}")
    return embed


# ── Cog ───────────────────────────────────────────────────────────────────────

class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, storage: BaseStorage) -> None:
        self.bot     = bot
        self.storage = storage

    # ── /create_event ──────────────────────────────────────────────────────────

    @app_commands.command(
        name="create_event",
        description="Create a titled event with a date and time.",
    )
    @app_commands.describe(
        title      = "Event name, e.g. 'Game Night'",
        date       = "Date in YYYY-MM-DD format, e.g. 2025-07-04",
        start_time = "Start time — e.g. 18:00 or 6pm",
        end_time   = "End time   — e.g. 20:00 or 8pm",
    )
    async def create_event(
        self,
        interaction: discord.Interaction,
        title:      str,
        date:       str,
        start_time: str,
        end_time:   str,
    ) -> None:
        await interaction.response.defer()

        # Validate title
        title = title.strip()
        if not title:
            await interaction.followup.send("❌ Event title cannot be empty.")
            return
        if len(title) > 100:
            await interaction.followup.send("❌ Title must be 100 characters or fewer.")
            return

        # Validate date
        date_str = parse_date(date)
        if date_str is None:
            await interaction.followup.send(
                "❌ Invalid date. Use `YYYY-MM-DD`, e.g. `2025-07-04`."
            )
            return
        
        # FIX: Calculate "today" based on Pacific Time (UTC-7 for Daylight Savings)
        # Or change the offset to match your target audience's timezone
        pacific_offset = timezone(timedelta(hours=-7)) 
        today_local = datetime.now(pacific_offset).date().isoformat()

        if date_str < today_local:
            await interaction.followup.send(
                "❌ Event date must be today or in the future."
            )
            return

        # Validate time range
        tr = parse_time_range(start_time, end_time)
        if tr is None:
            await interaction.followup.send(
                "❌ Invalid times. Use HH:MM (24-hour) or 9am style, "
                "and end must be after start."
            )
            return

        event: Event = {
            "id":              str(uuid.uuid4())[:8],  # short 8-char ID for readability
            "title":           title,
            "date":            date_str,
            "start_time":      tr[0],
            "end_time":        tr[1],
            "created_by":      str(interaction.user.id),
            "created_by_name": interaction.user.display_name,
        }

        self.storage.create_event(str(interaction.guild_id), event)

        embed             = _event_embed(event)
        embed.description = "✅ Event created!"
        await interaction.followup.send(embed=embed)

    # ── /delete_event ──────────────────────────────────────────────────────────

    @app_commands.command(
        name="delete_event",
        description="Delete an event by its ID.",
    )
    @app_commands.describe(event_id="The 8-character ID shown when the event was created or in /upcoming")
    async def delete_event(
        self,
        interaction: discord.Interaction,
        event_id: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        event_id = event_id.strip()
        event    = self.storage.get_event_by_id(guild_id, event_id)

        if event is None:
            await interaction.followup.send(
                f"❌ No event found with ID `{event_id}`.", ephemeral=True
            )
            return

        self.storage.delete_event(guild_id, event_id)
        await interaction.followup.send(
            f"🗑️ Deleted event **{event['title']}** (`{event_id}`).",
            ephemeral=True,
        )

    # ── /upcoming ──────────────────────────────────────────────────────────────

    @app_commands.command(
        name="upcoming",
        description="List all upcoming events with Google Calendar links.",
    )
    async def upcoming(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        guild_id = str(interaction.guild_id)
        today    = date_cls.today().isoformat()
        events   = self.storage.get_upcoming_events(guild_id, today)

        if not events:
            await interaction.followup.send(
                "📭 No upcoming events. Create one with `/create_event`!"
            )
            return

        # Discord allows up to 10 embeds per message
        embeds = [_event_embed(e) for e in events[:10]]
        header = f"📅 **{len(events)} upcoming event(s)**"
        if len(events) > 10:
            header += f" *(showing first 10 of {len(events)})*"

        await interaction.followup.send(content=header, embeds=embeds)


async def setup(bot: commands.Bot, storage: BaseStorage) -> None:
    await bot.add_cog(EventsCog(bot, storage))