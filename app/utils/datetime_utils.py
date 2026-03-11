"""
Date and time utilities.

This module provides:
- Time zone handling
- Date formatting functions
- Time conversion utilities
- Timestamp generation

Functions:
    utc_now() -> datetime: Get current UTC time
    to_iso(dt: datetime) -> str: Convert datetime to ISO format
    from_iso(value: str) -> datetime: Parse ISO format to datetime
    is_expired(expires_at: datetime) -> bool: Check if datetime is expired
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


UTC = timezone.utc


def utc_now() -> datetime:
    """
    Return current timezone-aware UTC datetime.
    """
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """
    Normalize datetime to timezone-aware UTC.

    Rules:
    - naive datetime is treated as UTC
    - aware datetime is converted to UTC
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_iso(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 string in UTC.

    Example:
        2026-03-11T12:34:56Z
    """
    normalized = ensure_utc(dt)
    return normalized.isoformat().replace("+00:00", "Z")


def from_iso(value: str) -> datetime:
    """
    Parse ISO 8601 string into timezone-aware UTC datetime.

    Supported examples:
    - 2026-03-11T12:34:56Z
    - 2026-03-11T12:34:56+00:00
    - 2026-03-11T13:34:56+01:00

    Naive input is treated as UTC.
    """
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    parsed = datetime.fromisoformat(normalized)
    return ensure_utc(parsed)


def is_expired(expires_at: datetime) -> bool:
    """
    Return True if the provided datetime is in the past.
    """
    return ensure_utc(expires_at) <= utc_now()


def utc_timestamp() -> int:
    """
    Return current UTC Unix timestamp in seconds.
    """
    return int(utc_now().timestamp())


def to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp in seconds.
    """
    return int(ensure_utc(dt).timestamp())


def from_timestamp(value: int | float) -> datetime:
    """
    Convert Unix timestamp to timezone-aware UTC datetime.
    """
    return datetime.fromtimestamp(value, tz=UTC)


def add_seconds(dt: datetime, seconds: int) -> datetime:
    """
    Return datetime shifted by the given number of seconds.
    """
    return ensure_utc(dt) + timedelta(seconds=seconds)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    Return datetime shifted by the given number of minutes.
    """
    return ensure_utc(dt) + timedelta(minutes=minutes)


def add_hours(dt: datetime, hours: int) -> datetime:
    """
    Return datetime shifted by the given number of hours.
    """
    return ensure_utc(dt) + timedelta(hours=hours)


def seconds_until(dt: datetime) -> int:
    """
    Return number of whole seconds until target datetime.

    Negative result means the datetime is already in the past.
    """
    delta = ensure_utc(dt) - utc_now()
    return int(delta.total_seconds())
