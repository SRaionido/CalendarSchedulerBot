"""
utils/time_parser.py - Parse and validate date/time strings from Discord input.

Accepts flexible user input:
  Times  → "HH:MM" (24-hour), "9am", "2pm", "11:30am"
  Dates  → "YYYY-MM-DD"
  Months → "YYYY-MM"
"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

TimeRange = Tuple[str, str]  # ("HH:MM", "HH:MM")


def parse_time(raw: str) -> Optional[str]:
    """
    Parse a time string and return a normalised "HH:MM" 24-hour string,
    or None if the input cannot be understood.

    Accepts: "9:00", "09:00", "9am", "2pm", "11:30am", "2:30pm"
    """
    raw = raw.strip().lower()

    # 12-hour with optional minutes: "9am", "2pm", "11:30am", "2:30pm"
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", raw)
    if match:
        h      = int(match.group(1))
        m      = int(match.group(2) or 0)
        suffix = match.group(3)
        if suffix == "pm" and h != 12:
            h += 12
        if suffix == "am" and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
        return None

    # 24-hour: "9:00", "09:00", "14:30"
    match = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", raw)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"

    return None


def parse_date(raw: str) -> Optional[str]:
    """
    Parse a date string and return "YYYY-MM-DD", or None on failure.
    Validates that the date is a real calendar date (e.g. not Feb 30).
    """
    raw = raw.strip()
    if not re.match(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$", raw):
        return None
    try:
        datetime.strptime(raw, "%Y-%m-%d")
        return raw
    except ValueError:
        return None


def parse_time_range(start_raw: str, end_raw: str) -> Optional[TimeRange]:
    """
    Parse and validate a time range.
    Returns ("HH:MM", "HH:MM") or None if either time is invalid or
    end is not strictly after start.
    """
    start = parse_time(start_raw)
    end   = parse_time(end_raw)
    if start is None or end is None or start >= end:
        return None
    return (start, end)


def parse_year_month(raw: str) -> Optional[Tuple[int, int]]:
    """
    Parse "YYYY-MM" and return (year, month) as ints, or None on failure.
    """
    raw   = raw.strip()
    match = re.match(r"^(\d{4})-(0[1-9]|1[0-2])$", raw)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def format_time_ranges(ranges: List[TimeRange]) -> str:
    """
    Format a list of time ranges for display.
    e.g. [("09:00", "12:00"), ("14:00", "17:00")] → "09:00–12:00, 14:00–17:00"
    """
    return ", ".join(f"{s}–{e}" for s, e in ranges)


def time_to_float(t: str) -> float:
    """Convert "HH:MM" to fractional hours — e.g. "09:30" → 9.5"""
    h, m = map(int, t.split(":"))
    return h + m / 60.0