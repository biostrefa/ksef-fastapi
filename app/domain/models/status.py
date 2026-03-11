"""
Status domain models and enums.

This module provides:
- Status enums and constants
- Local status models
- Status transition logic
- Status validation rules

Enums / Classes:
    LocalInvoiceStatus: Local invoice status enumeration
    LocalSessionStatus: Local session status enumeration
    KsefProcessingStatus: KSEF processing status enumeration
    StatusTransitionRule: Status transition validation rules
"""

from __future__ import annotations

from datetime import datetime

from app.core.constants import InvoiceSubmissionStatus, KsefSessionStatus
from app.domain.models.auth import DomainModel


class KsefErrorDetail(DomainModel):
    code: str
    message: str
    context: dict | None = None


class InvoiceStatusSnapshot(DomainModel):
    ksef_invoice_reference: str | None = None
    status: InvoiceSubmissionStatus
    last_checked_at: datetime
    error: KsefErrorDetail | None = None


class SessionTransitionRule(DomainModel):
    from_status: KsefSessionStatus
    to_status: KsefSessionStatus
    allowed: bool = True


class InvoiceTransitionRule(DomainModel):
    from_status: InvoiceSubmissionStatus
    to_status: InvoiceSubmissionStatus
    allowed: bool = True
