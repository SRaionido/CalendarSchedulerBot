"""
storage/base.py - Abstract interface for all storage backends.

To add a new backend (e.g. PostgreSQL):
  1. Create storage/postgres_storage.py and implement every method below
  2. Add a branch in storage/__init__.py get_storage()
  3. Set STORAGE_BACKEND=postgres in your .env
  4. Add any connection settings to config.py

Nothing outside the storage/ package needs to change.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


# ── Type aliases ───────────────────────────────────────────────────────────────

UserID    = str               # Discord user ID stored as a string
DateStr   = str               # ISO date string: "YYYY-MM-DD"
TimeRange = Tuple[str, str]   # 24-hour time pair: ("HH:MM", "HH:MM")

# Shape of an event record:
# {
#   "id":              str,   # 8-character unique ID
#   "title":           str,
#   "date":            str,   # "YYYY-MM-DD"
#   "start_time":      str,   # "HH:MM"
#   "end_time":        str,   # "HH:MM"
#   "created_by":      str,   # user_id
#   "created_by_name": str,   # display name at time of creation
# }
Event = Dict[str, Any]


class BaseStorage(ABC):
    """Abstract base class — every storage backend must implement all methods."""

    # ── Availability ───────────────────────────────────────────────────────────

    @abstractmethod
    def add_availability(
        self,
        guild_id: str,
        user_id: UserID,
        username: str,
        date: DateStr,
        time_ranges: List[TimeRange],
    ) -> None:
        """
        Save (or replace) availability for user_id on date.
        time_ranges is a list of (start, end) 24-hour pairs,
        e.g. [("09:00", "12:00"), ("14:00", "17:00")].
        """

    @abstractmethod
    def remove_availability(
        self,
        guild_id: str,
        user_id: UserID,
        date: DateStr,
    ) -> bool:
        """
        Remove availability for user_id on date.
        Returns True if an entry existed and was deleted, False otherwise.
        """

    @abstractmethod
    def get_availability_for_user(
        self,
        guild_id: str,
        user_id: UserID,
    ) -> Dict[DateStr, List[TimeRange]]:
        """Return all saved availability for a single user, keyed by date."""

    @abstractmethod
    def get_availability_for_month(
        self,
        guild_id: str,
        year: int,
        month: int,
    ) -> Dict[UserID, Dict[DateStr, List[TimeRange]]]:
        """
        Return all availability in a guild for the given month,
        keyed by user_id then date.
        """

    @abstractmethod
    def get_usernames(self, guild_id: str) -> Dict[UserID, str]:
        """Return a mapping of user_id → display name for a guild."""

    @abstractmethod
    def clear_user_month(
        self,
        guild_id: str,
        user_id: UserID,
        year: int,
        month: int,
    ) -> int:
        """
        Delete all availability entries for user_id in the given month.
        Returns the number of entries removed.
        """

    # ── Events ─────────────────────────────────────────────────────────────────

    @abstractmethod
    def create_event(self, guild_id: str, event: Event) -> None:
        """Persist a new event. The event dict must contain a unique 'id' key."""

    @abstractmethod
    def delete_event(self, guild_id: str, event_id: str) -> bool:
        """
        Delete an event by ID.
        Returns True if found and deleted, False if not found.
        """

    @abstractmethod
    def get_upcoming_events(self, guild_id: str, today: DateStr) -> List[Event]:
        """
        Return all events whose date >= today, sorted by date then start_time.
        """

    @abstractmethod
    def get_event_by_id(self, guild_id: str, event_id: str) -> Optional[Event]:
        """Return a single event by its ID, or None if not found."""

    # ── Maintenance ────────────────────────────────────────────────────────────

    @abstractmethod
    def purge_past_data(self, today: DateStr) -> Dict[str, int]:
        """
        Delete all availability entries and events whose date is before today,
        across every guild.
        Returns {"availability": <n_deleted>, "events": <n_deleted>}.
        """