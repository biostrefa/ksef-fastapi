"""
Audit log database model.

This module provides:
- Audit log table definition
- Event tracking fields
- Security event storage
- Audit metadata
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.db import Base


class AuditEventCategory(str, enum.Enum):
    """
    High-level audit event category.
    """

    AUTH = "auth"
    SESSION = "session"
    INVOICE = "invoice"
    STATUS = "status"
    WEBHOOK = "webhook"
    SECURITY = "security"
    REPOSITORY = "repository"
    SYSTEM = "system"


class AuditEventSeverity(str, enum.Enum):
    """
    Event severity level.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEventOutcome(str, enum.Enum):
    """
    Final event outcome.
    """

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    UNKNOWN = "unknown"


class AuditLogModel(Base):
    """
    Audit log table for operational and security events.

    Stores both business-process events and technical/security trace data
    related to KSeF integration.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
    )

    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
    )

    event_category: Mapped[AuditEventCategory] = mapped_column(
        Enum(
            AuditEventCategory,
            name="audit_event_category_enum",
            native_enum=True,
        ),
        nullable=False,
        index=True,
    )

    event_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    severity: Mapped[AuditEventSeverity] = mapped_column(
        Enum(
            AuditEventSeverity,
            name="audit_event_severity_enum",
            native_enum=True,
        ),
        nullable=False,
        default=AuditEventSeverity.INFO,
        index=True,
    )

    outcome: Mapped[AuditEventOutcome] = mapped_column(
        Enum(
            AuditEventOutcome,
            name="audit_event_outcome_enum",
            native_enum=True,
        ),
        nullable=False,
        default=AuditEventOutcome.UNKNOWN,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="app",
        index=True,
    )

    component: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    actor_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    actor_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    actor_ip: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    trace_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    session_reference_number: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    invoice_reference_number: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    submission_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    http_method: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )

    http_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    http_status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    payload_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    headers_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    context_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    tags_json: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_audit_logs_category_name_time",
            "event_category",
            "event_name",
            "event_time",
        ),
        Index("ix_audit_logs_tenant_time", "tenant_id", "event_time"),
        Index("ix_audit_logs_session_time", "session_reference_number", "event_time"),
        Index("ix_audit_logs_invoice_time", "invoice_reference_number", "event_time"),
        Index(
            "ix_audit_logs_outcome_severity_time", "outcome", "severity", "event_time"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"AuditLogModel(id={self.id!s}, event_name={self.event_name!r}, "
            f"category={self.event_category.value!r}, outcome={self.outcome.value!r})"
        )
