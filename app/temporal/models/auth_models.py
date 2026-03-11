"""
Authentication workflow models.

This module provides:
- Authentication request/response models
- Token management models
- Challenge response models
- Auth context temporal models
"""

from __future__ import annotations

from pydantic import BaseModel


class EnsureAuthInput(BaseModel):
    company_id: str
    environment: str
    auth_mode: str = "token"


class EnsureAuthResult(BaseModel):
    auth_context_id: str
    access_token: str
    refresh_token: str | None = None
    expires_at_utc: str | None = None
    session_encryption: dict | None = None


class RefreshAuthInput(BaseModel):
    auth_context_id: str


class RefreshAuthResult(BaseModel):
    auth_context_id: str
    access_token: str
    expires_at_utc: str | None = None
