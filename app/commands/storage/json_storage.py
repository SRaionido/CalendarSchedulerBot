"""
storage/json_storage.py - Thread-safe JSON file storage backend.

Manages two files:

  availability.json
  {
    "<guild_id>": {
      "users": { "<user_id>": "<display_name>" },
      "availability": {
        "<user_id>": {
          "<YYYY-MM-DD>": [["HH:MM", "HH:MM"], ...]
        }
      }
    }
  }

  events.json
  {
    "<guild_id>": {
      "<event_id>": {
        "id":              "<8-char id>",
        "title":           "Game Night",
        "date":            "YYYY-MM-DD",
        "start_time":      "HH:MM",
        "end_time":        "HH:MM",
        "created_by":      "<user_id>",
        "created_by_name": "<display_name>"
      }
    }
  }

Writes are atomic (write to .tmp then os.replace) so a crash mid-write
cannot corrupt the data file.
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from commands.storage.base import BaseStorage, DateStr, Event, TimeRange, UserID
import app.config as config


class JsonStorage(BaseStorage):
    """Thread-safe JSON file storage backend."""

    def __init__(
        self,
        avail_filepath:  str = config.AVAILABILITY_FILE,
        events_filepath: str = config.EVENTS_FILE,
    ) -> None:
        self._avail_path  = avail_filepath
        self._events_path = events_filepath
        self._lock        = threading.Lock()

        for path in (self._avail_path, self._events_path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.exists(path):
                self._write_file(path, {})

    # ── File I/O ───────────────────────────────────────────────────────────────

    @staticmethod
    def _read_file(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_file(path: str, data: dict) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)  # atomic rename on POSIX

    # ── Availability helpers ───────────────────────────────────────────────────

    def _ensure_guild(self, data: dict, guild_id: str) -> None:
        if guild_id not in data:
            data[guild_id] = {"users": {}, "availability": {}}

    def _ensure_user(self, data: dict, guild_id: str, user_id: str) -> None:
        self._ensure_guild(data, guild_id)
        if user_id not in data[guild_id]["availability"]:
            data[guild_id]["availability"][user_id] = {}

    # ── Availability CRUD ──────────────────────────────────────────────────────

    def add_availability(
        self,
        guild_id: str,
        user_id: UserID,
        username: str,
        date: DateStr,
        time_ranges: List[TimeRange],
    ) -> None:
        with self._lock:
            data = self._read_file(self._avail_path)
            self._ensure_user(data, guild_id, user_id)
            data[guild_id]["users"][user_id] = username
            data[guild_id]["availability"][user_id][date] = [
                list(tr) for tr in time_ranges
            ]
            self._write_file(self._avail_path, data)

    def remove_availability(
        self,
        guild_id: str,
        user_id: UserID,
        date: DateStr,
    ) -> bool:
        with self._lock:
            data = self._read_file(self._avail_path)
            try:
                del data[guild_id]["availability"][user_id][date]
                self._write_file(self._avail_path, data)
                return True
            except KeyError:
                return False

    def get_availability_for_user(
        self,
        guild_id: str,
        user_id: UserID,
    ) -> Dict[DateStr, List[TimeRange]]:
        with self._lock:
            data = self._read_file(self._avail_path)
            return (
                data.get(guild_id, {})
                    .get("availability", {})
                    .get(user_id, {})
            )

    def get_availability_for_month(
        self,
        guild_id: str,
        year: int,
        month: int,
    ) -> Dict[UserID, Dict[DateStr, List[TimeRange]]]:
        prefix = f"{year}-{month:02d}-"
        with self._lock:
            data      = self._read_file(self._avail_path)
            all_avail = data.get(guild_id, {}).get("availability", {})
            result: Dict[UserID, Dict[DateStr, List[TimeRange]]] = {}
            for uid, days in all_avail.items():
                filtered = {
                    d: [tuple(tr) for tr in ranges]
                    for d, ranges in days.items()
                    if d.startswith(prefix)
                }
                if filtered:
                    result[uid] = filtered
            return result

    def get_usernames(self, guild_id: str) -> Dict[UserID, str]:
        with self._lock:
            data = self._read_file(self._avail_path)
            return data.get(guild_id, {}).get("users", {})

    def clear_user_month(
        self,
        guild_id: str,
        user_id: UserID,
        year: int,
        month: int,
    ) -> int:
        prefix = f"{year}-{month:02d}-"
        with self._lock:
            data      = self._read_file(self._avail_path)
            user_days = (
                data.get(guild_id, {})
                    .get("availability", {})
                    .get(user_id, {})
            )
            to_delete = [d for d in user_days if d.startswith(prefix)]
            for d in to_delete:
                del user_days[d]
            if to_delete:
                self._write_file(self._avail_path, data)
            return len(to_delete)

    # ── Events CRUD ────────────────────────────────────────────────────────────

    def create_event(self, guild_id: str, event: Event) -> None:
        with self._lock:
            data = self._read_file(self._events_path)
            if guild_id not in data:
                data[guild_id] = {}
            data[guild_id][event["id"]] = event
            self._write_file(self._events_path, data)

    def delete_event(self, guild_id: str, event_id: str) -> bool:
        with self._lock:
            data = self._read_file(self._events_path)
            try:
                del data[guild_id][event_id]
                self._write_file(self._events_path, data)
                return True
            except KeyError:
                return False

    def get_upcoming_events(self, guild_id: str, today: DateStr) -> List[Event]:
        with self._lock:
            data         = self._read_file(self._events_path)
            guild_events = data.get(guild_id, {}).values()
            upcoming     = [e for e in guild_events if e["date"] >= today]
            return sorted(upcoming, key=lambda e: (e["date"], e["start_time"]))

    def get_event_by_id(self, guild_id: str, event_id: str) -> Optional[Event]:
        with self._lock:
            data = self._read_file(self._events_path)
            return data.get(guild_id, {}).get(event_id)

    # ── Maintenance ────────────────────────────────────────────────────────────

    def purge_past_data(self, today: DateStr) -> Dict[str, int]:
        """Remove all availability entries and events with a date before today."""
        avail_count  = 0
        events_count = 0

        with self._lock:
            # Availability
            avail_data  = self._read_file(self._avail_path)
            avail_dirty = False
            for guild in avail_data.values():
                for days in guild.get("availability", {}).values():
                    old = [d for d in days if d < today]
                    for d in old:
                        del days[d]
                    avail_count += len(old)
                    if old:
                        avail_dirty = True
            if avail_dirty:
                self._write_file(self._avail_path, avail_data)

            # Events
            events_data  = self._read_file(self._events_path)
            events_dirty = False
            for guild_events in events_data.values():
                old_ids = [eid for eid, e in guild_events.items() if e["date"] < today]
                for eid in old_ids:
                    del guild_events[eid]
                events_count += len(old_ids)
                if old_ids:
                    events_dirty = True
            if events_dirty:
                self._write_file(self._events_path, events_data)

        return {"availability": avail_count, "events": events_count}