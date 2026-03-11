"""
Session workflow models.

This module provides:
- Session creation models
- Session lifecycle models
- Session status tracking models
- Session management temporal models
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenOnlineSessionInput:
    company_id: str
    environment: str
    access_token: str
    form_code: dict
    encryption: dict


@dataclass
class OpenOnlineSessionResult:
    reference_number: str
    status_code: int | None = None
    status_description: str | None = None


@dataclass
class CloseOnlineSessionInput:
    session_reference_number: str
    access_token: str


@dataclass
class SessionStatusInput:
    session_reference_number: str
    access_token: str


@dataclass
class SessionStatusResult:
    reference_number: str
    status_code: int | None = None
    status_description: str | None = None
