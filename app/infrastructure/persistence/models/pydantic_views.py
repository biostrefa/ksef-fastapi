"""
Ten plik nie jest obowiązkowy, ale praktycznie bardzo się przydaje jako warstwa pośrednia między ORM a API.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.constants import (
    InvoiceSubmissionStatus,
    KsefEnvironment,
    KsefSessionStatus,
    KsefSessionType,
)


class OrmReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenReadModel(OrmReadModel):
    id: UUID
    company_id: UUID
    environment: KsefEnvironment
    access_token: str
    refresh_token: str | None = None
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SessionReadModel(OrmReadModel):
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


class InvoiceSubmissionReadModel(OrmReadModel):
    id: UUID
    company_id: UUID
    session_reference_number: str
    local_invoice_number: str
    ksef_invoice_reference: str | None = None
    status: InvoiceSubmissionStatus
    xml_hash_sha256: str | None = None
    upo_content: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
