"""
KSeF session domain model.

This module provides:
- KSeF session domain entity
- Session lifecycle management
- Session state tracking
- Session validation rules

Classes:
    KsefSession: KSeF session domain entity
        - id: Session identifier
        - reference_number: KSeF reference number
        - session_type: Type of session (online/batch)
        - status: Current session status
        - opened_at: Session opening timestamp
        - closed_at: Session closing timestamp
    SessionStatusSnapshot: Session status snapshot entity
        - reference_number: KSeF reference number
        - status: Session status at snapshot time
        - last_checked_at: Last status check timestamp
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.core.constants import KsefEnvironment, KsefSessionStatus, KsefSessionType
from app.domain.models.auth import DomainModel


class KsefSession(DomainModel):
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


class SessionStatusSnapshot(DomainModel):
    reference_number: str
    status: KsefSessionStatus
    last_checked_at: datetime
    upo_available: bool = False
    last_error_code: str | None = None
    last_error_message: str | None = None
