"""
Token database model.

This module provides:
- Token table definition
- Auth context storage
- Token metadata fields
- Token relationships

ORM Classes:
    TokenModel(Base): Token database model

Fields:
    id: Primary key
    company_id: Company identifier
    environment: KSeF environment
    access_token: Access token value
    refresh_token: Refresh token value
    expires_at: Token expiration time
    created_at: Record creation time
    updated_at: Record update time
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import KsefEnvironment
from app.infrastructure.persistence.db import Base


class TokenModel(Base):
    __tablename__ = "ksef_tokens"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "environment", name="uq_ksef_tokens__company_environment"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    environment: Mapped[str] = mapped_column(String(20), nullable=False)

    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    access_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
