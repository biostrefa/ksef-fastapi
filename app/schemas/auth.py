"""
Authentication request/response models.

This module provides:
- Authentication request models
- Authentication response models
- Token models
- Challenge models

Pydantic Classes:
    AuthChallengeRequest: Authentication challenge request
    AuthChallengeResponse: Authentication challenge response
    AuthTokenRedeemRequest: Token redemption request
    AuthTokenRedeemResponse: Token redemption response
    AuthRefreshRequest: Token refresh request
    AuthRefreshResponse: Token refresh response
    AuthContextResponse: Authentication context response
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.constants import KsefAuthMode, KsefEnvironment
from app.schemas.common import ApiModel


class AuthChallengeRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment


class AuthChallengeResponse(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    challenge: str
    challenge_timestamp: datetime


class AuthTokenRedeemRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    auth_mode: KsefAuthMode


class AuthTokenRedeemResponse(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    auth_mode: KsefAuthMode
    access_token: str
    refresh_token: str | None = None
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None


class AuthRefreshRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    refresh_token: str | None = None


class AuthRefreshResponse(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    access_token: str
    refresh_token: str | None = None
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None


class RevokeAuthRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment


class AuthContextResponse(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    auth_mode: KsefAuthMode
    has_active_access_token: bool
    has_refresh_token: bool
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None
