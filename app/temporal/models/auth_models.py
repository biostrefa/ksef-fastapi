"""
Authentication workflow models.

This module provides:
- Authentication request/response models
- Token management models
- Challenge response models
- Auth context temporal models
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class EnsureAuthInput:
    company_id: str
    environment: str
    auth_mode: str = "token"


@dataclass
class EnsureAuthResult:
    auth_context_id: str
    access_token: str
    refresh_token: Optional[str]
    expires_at_utc: Optional[str]
    session_encryption: dict | None = None


@dataclass
class RefreshAuthInput:
    auth_context_id: str


@dataclass
class RefreshAuthResult:
    auth_context_id: str
    access_token: str
    expires_at_utc: Optional[str]
