"""
Session request/response models.

This module provides:
- Online session models
- Batch session models
- Session status models
- Reference number models

Pydantic Classes:
    OpenOnlineSessionRequest: Request to open online session
    OpenBatchSessionRequest: Request to open batch session
    OpenSessionResponse: Response for opening session
    CloseSessionRequest: Request to close session
    CloseSessionResponse: Response for closing session
    SessionResponse: Session details response
    SessionStatusResponse: Session status response
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.constants import KsefEnvironment, KsefSessionStatus, KsefSessionType
from app.schemas.common import ApiModel


class SessionEncryptionInfo(ApiModel):
    encryption_method: str = Field(default="AES")
    key_size: int = Field(default=256, ge=128)
    checksum_algorithm: str = Field(default="SHA-256")


class OpenOnlineSessionRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    reuse_open_session: bool = True
    encryption: SessionEncryptionInfo | None = None


class OpenBatchSessionRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    package_name: str | None = None
    encryption: SessionEncryptionInfo | None = None


class CreateBatchSessionRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    package_name: str | None = None
    encryption: SessionEncryptionInfo | None = None


class CreateOnlineSessionRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    reuse_open_session: bool = True
    encryption: SessionEncryptionInfo | None = None


class OpenSessionResponse(ApiModel):
    company_id: UUID
    environment: KsefEnvironment
    session_type: KsefSessionType
    reference_number: str
    status: KsefSessionStatus
    opened_at: datetime | None = None


class CloseSessionRequest(ApiModel):
    reference_number: str


class CloseSessionResponse(ApiModel):
    reference_number: str
    status: KsefSessionStatus
    closed_at: datetime | None = None


class SessionResponse(ApiModel):
    id: UUID
    company_id: UUID
    environment: KsefEnvironment
    session_type: KsefSessionType
    reference_number: str
    status: KsefSessionStatus
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


class SessionStatusResponse(ApiModel):
    reference_number: str
    status: KsefSessionStatus
    last_checked_at: datetime
    upo_available: bool = False
    upo_reference_number: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


class SessionUpoResponse(ApiModel):
    reference_number: str
    upo_content: str
    content_type: str = "application/xml"
    downloaded_at: datetime


class SyncPendingStatusesResponse(ApiModel):
    processed_sessions: int
    processed_invoices: int
    errors: list[str] = []
