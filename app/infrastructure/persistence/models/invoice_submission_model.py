"""
Invoice submission database model.

This module provides:
- Invoice submission table definition
- Status tracking fields
- UPO storage
- Submission metadata

ORM Classes:
    InvoiceSubmissionModel(Base): Invoice submission database model

Fields:
    id: Primary key
    company_id: Company identifier
    session_reference_number: KSeF session reference number
    local_invoice_number: Local invoice number
    ksef_invoice_reference: KSeF invoice reference number
    status: Submission status
    xml_hash: XML content hash
    upo_content: UPO content
    error_code: Error code if any
    error_message: Error message if any
    created_at: Record creation time
    updated_at: Record update time
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.db import Base


class InvoiceSubmissionModel(Base):
    __tablename__ = "ksef_invoice_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    environment: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    session_reference_number: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "ksef_sessions.reference_number",
            name="fk_ksef_invoice_submissions__session_reference_number__ksef_sessions",
        ),
        index=True,
        nullable=False,
    )

    local_invoice_number: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )
    ksef_invoice_reference: Mapped[str | None] = mapped_column(
        String(255), index=True, nullable=True
    )

    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    xml_hash_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)

    upo_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
