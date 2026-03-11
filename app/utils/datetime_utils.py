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
