"""
Authentication domain model.

This module provides:
- Token domain entity
- Challenge domain entity
- Authentication context model
- Auth state management
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.constants import KsefAuthMode, KsefEnvironment


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )


class AuthChallenge(DomainModel):
    company_id: UUID
    environment: KsefEnvironment
    challenge: str
    challenge_timestamp: datetime
    challenge_timestamp_ms: int | None = None


class AuthTokens(DomainModel):
    access_token: str
    refresh_token: str | None = None
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None


class AuthContext(DomainModel):
    company_id: UUID
    environment: KsefEnvironment
    auth_mode: KsefAuthMode
    tokens: AuthTokens | None = None
