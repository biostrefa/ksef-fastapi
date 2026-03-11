"""
Session database model.

This module provides:
- KSeF session table definition
- Session metadata storage
- Session state tracking
- Session relationships

ORM Classes:
    SessionModel(Base): Session database model

Fields:
    id: Primary key
    company_id: Company identifier
    reference_number: KSeF reference number
    session_type: Session type (online/batch)
    status: Session status
    opened_at: Session opening time
    closed_at: Session closing time
    last_checked_at: Last status check time
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.db import Base


class SessionModel(Base):
    __tablename__ = "ksef_sessions"
    __table_args__ = (
        UniqueConstraint("reference_number", name="uq_ksef_sessions__reference_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    environment: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    session_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    reference_number: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    upo_reference_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

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
