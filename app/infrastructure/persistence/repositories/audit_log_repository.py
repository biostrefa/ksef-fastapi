"""
Audit log repository.

This module provides:
- Audit log CRUD operations
- Event storage and retrieval
- Security event logging
- Audit query operations
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RepositoryError
from app.core.security import sanitize_headers, sanitize_mapping
from app.infrastructure.persistence.models.audit_log_model import (
    AuditEventCategory,
    AuditEventOutcome,
    AuditEventSeverity,
    AuditLogModel,
)


class AuditLogRepository:
    """
    Repository for persisting and querying audit log events.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(
        self,
        *,
        event_category: AuditEventCategory,
        event_name: str,
        message: str,
        severity: AuditEventSeverity = AuditEventSeverity.INFO,
        outcome: AuditEventOutcome = AuditEventOutcome.UNKNOWN,
        source: str = "app",
        component: str | None = None,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
        actor_ip: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        session_reference_number: str | None = None,
        invoice_reference_number: str | None = None,
        submission_id: str | None = None,
        http_method: str | None = None,
        http_path: str | None = None,
        http_status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload_json: dict[str, Any] | None = None,
        headers_json: dict[str, Any] | None = None,
        context_json: dict[str, Any] | None = None,
        tags_json: list[str] | None = None,
        event_time: datetime | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Create and persist an audit log entry.
        """
        model = AuditLogModel(
            event_time=event_time or datetime.utcnow(),
            event_category=event_category,
            event_name=event_name,
            severity=severity,
            outcome=outcome,
            source=source,
            component=component,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_ip=actor_ip,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            session_reference_number=session_reference_number,
            invoice_reference_number=invoice_reference_number,
            submission_id=submission_id,
            http_method=http_method,
            http_path=http_path,
            http_status_code=http_status_code,
            error_code=error_code,
            error_message=error_message,
            message=message,
            payload_json=sanitize_mapping(payload_json),
            headers_json=sanitize_headers(headers_json),
            context_json=sanitize_mapping(context_json),
            tags_json=tags_json,
        )

        try:
            self.db_session.add(model)

            if commit:
                await self.db_session.commit()
                await self.db_session.refresh(model)
            else:
                await self.db_session.flush()

            return model
        except SQLAlchemyError as exc:
            await self.db_session.rollback()
            raise RepositoryError(
                message="Failed to create audit log entry.",
                details={
                    "event_category": event_category.value,
                    "event_name": event_name,
                    "error": str(exc),
                },
            ) from exc

    async def get_by_id(self, audit_log_id: str) -> AuditLogModel | None:
        """
        Fetch a single audit log entry by ID.
        """
        stmt = select(AuditLogModel).where(AuditLogModel.id == audit_log_id)

        try:
            result = await self.db_session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise RepositoryError(
                message="Failed to fetch audit log entry by ID.",
                details={"audit_log_id": audit_log_id, "error": str(exc)},
            ) from exc

    async def list_events(
        self,
        *,
        event_category: AuditEventCategory | None = None,
        event_name: str | None = None,
        severity: AuditEventSeverity | None = None,
        outcome: AuditEventOutcome | None = None,
        source: str | None = None,
        component: str | None = None,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        session_reference_number: str | None = None,
        invoice_reference_number: str | None = None,
        submission_id: str | None = None,
        error_code: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogModel]:
        """
        Query audit log entries using common filters.
        """
        stmt = select(AuditLogModel)
        stmt = self._apply_filters(
            stmt=stmt,
            event_category=event_category,
            event_name=event_name,
            severity=severity,
            outcome=outcome,
            source=source,
            component=component,
            tenant_id=tenant_id,
            actor_id=actor_id,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            session_reference_number=session_reference_number,
            invoice_reference_number=invoice_reference_number,
            submission_id=submission_id,
            error_code=error_code,
            created_from=created_from,
            created_to=created_to,
        )
        stmt = stmt.order_by(
            desc(AuditLogModel.event_time), desc(AuditLogModel.created_at)
        )
        stmt = stmt.offset(offset).limit(limit)

        try:
            result = await self.db_session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            raise RepositoryError(
                message="Failed to list audit log entries.",
                details={"error": str(exc)},
            ) from exc

    async def get_recent_for_session(
        self,
        session_reference_number: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogModel]:
        """
        Return most recent audit events for a given KSeF session reference number.
        """
        return await self.list_events(
            session_reference_number=session_reference_number,
            limit=limit,
            offset=0,
        )

    async def get_recent_for_invoice(
        self,
        invoice_reference_number: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogModel]:
        """
        Return most recent audit events for a given KSeF invoice reference number.
        """
        return await self.list_events(
            invoice_reference_number=invoice_reference_number,
            limit=limit,
            offset=0,
        )

    async def get_recent_for_submission(
        self,
        submission_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogModel]:
        """
        Return most recent audit events for a local invoice submission ID.
        """
        return await self.list_events(
            submission_id=submission_id,
            limit=limit,
            offset=0,
        )

    async def log_auth_event(
        self,
        *,
        event_name: str,
        message: str,
        outcome: AuditEventOutcome,
        severity: AuditEventSeverity = AuditEventSeverity.INFO,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload_json: dict[str, Any] | None = None,
        context_json: dict[str, Any] | None = None,
        tags_json: list[str] | None = None,
    ) -> AuditLogModel:
        """
        Convenience method for authentication-related audit events.
        """
        return await self.create(
            event_category=AuditEventCategory.AUTH,
            event_name=event_name,
            message=message,
            outcome=outcome,
            severity=severity,
            tenant_id=tenant_id,
            actor_id=actor_id,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            error_code=error_code,
            error_message=error_message,
            payload_json=payload_json,
            context_json=context_json,
            tags_json=tags_json,
        )

    async def log_security_event(
        self,
        *,
        event_name: str,
        message: str,
        outcome: AuditEventOutcome,
        severity: AuditEventSeverity = AuditEventSeverity.WARNING,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        actor_ip: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        http_method: str | None = None,
        http_path: str | None = None,
        http_status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload_json: dict[str, Any] | None = None,
        headers_json: dict[str, Any] | None = None,
        context_json: dict[str, Any] | None = None,
        tags_json: list[str] | None = None,
    ) -> AuditLogModel:
        """
        Convenience method for security-related audit events.
        """
        return await self.create(
            event_category=AuditEventCategory.SECURITY,
            event_name=event_name,
            message=message,
            outcome=outcome,
            severity=severity,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_ip=actor_ip,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            http_method=http_method,
            http_path=http_path,
            http_status_code=http_status_code,
            error_code=error_code,
            error_message=error_message,
            payload_json=payload_json,
            headers_json=headers_json,
            context_json=context_json,
            tags_json=tags_json,
        )

    async def log_webhook_event(
        self,
        *,
        source: str,
        message: str,
        outcome: AuditEventOutcome,
        severity: AuditEventSeverity = AuditEventSeverity.INFO,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        http_method: str | None = None,
        http_path: str | None = None,
        http_status_code: int | None = None,
        payload_json: dict[str, Any] | None = None,
        headers_json: dict[str, Any] | None = None,
        context_json: dict[str, Any] | None = None,
        tags_json: list[str] | None = None,
    ) -> AuditLogModel:
        """
        Convenience method for webhook-related audit events.
        """
        return await self.create(
            event_category=AuditEventCategory.WEBHOOK,
            event_name="webhook_received",
            message=message,
            outcome=outcome,
            severity=severity,
            source=source,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            http_method=http_method,
            http_path=http_path,
            http_status_code=http_status_code,
            payload_json=payload_json,
            headers_json=headers_json,
            context_json=context_json,
            tags_json=tags_json,
        )

    async def delete_older_than(
        self,
        *,
        older_than: datetime,
        commit: bool = True,
    ) -> int:
        """
        Delete old audit logs older than the provided timestamp.

        Intended mainly for retention/maintenance jobs.
        """
        try:
            stmt = select(AuditLogModel).where(AuditLogModel.created_at < older_than)
            result = await self.db_session.execute(stmt)
            rows = list(result.scalars().all())

            deleted_count = 0
            for row in rows:
                await self.db_session.delete(row)
                deleted_count += 1

            if commit:
                await self.db_session.commit()
            else:
                await self.db_session.flush()

            return deleted_count
        except SQLAlchemyError as exc:
            await self.db_session.rollback()
            raise RepositoryError(
                message="Failed to delete old audit log entries.",
                details={"older_than": older_than.isoformat(), "error": str(exc)},
            ) from exc

    def _apply_filters(
        self,
        *,
        stmt: Select[tuple[AuditLogModel]],
        event_category: AuditEventCategory | None = None,
        event_name: str | None = None,
        severity: AuditEventSeverity | None = None,
        outcome: AuditEventOutcome | None = None,
        source: str | None = None,
        component: str | None = None,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        session_reference_number: str | None = None,
        invoice_reference_number: str | None = None,
        submission_id: str | None = None,
        error_code: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> Select[tuple[AuditLogModel]]:
        """
        Apply common filtering conditions to an audit log query.
        """
        if event_category is not None:
            stmt = stmt.where(AuditLogModel.event_category == event_category)

        if event_name is not None:
            stmt = stmt.where(AuditLogModel.event_name == event_name)

        if severity is not None:
            stmt = stmt.where(AuditLogModel.severity == severity)

        if outcome is not None:
            stmt = stmt.where(AuditLogModel.outcome == outcome)

        if source is not None:
            stmt = stmt.where(AuditLogModel.source == source)

        if component is not None:
            stmt = stmt.where(AuditLogModel.component == component)

        if tenant_id is not None:
            stmt = stmt.where(AuditLogModel.tenant_id == tenant_id)

        if actor_id is not None:
            stmt = stmt.where(AuditLogModel.actor_id == actor_id)

        if request_id is not None:
            stmt = stmt.where(AuditLogModel.request_id == request_id)

        if trace_id is not None:
            stmt = stmt.where(AuditLogModel.trace_id == trace_id)

        if correlation_id is not None:
            stmt = stmt.where(AuditLogModel.correlation_id == correlation_id)

        if session_reference_number is not None:
            stmt = stmt.where(
                AuditLogModel.session_reference_number == session_reference_number
            )

        if invoice_reference_number is not None:
            stmt = stmt.where(
                AuditLogModel.invoice_reference_number == invoice_reference_number
            )

        if submission_id is not None:
            stmt = stmt.where(AuditLogModel.submission_id == submission_id)

        if error_code is not None:
            stmt = stmt.where(AuditLogModel.error_code == error_code)

        if created_from is not None:
            stmt = stmt.where(AuditLogModel.created_at >= created_from)

        if created_to is not None:
            stmt = stmt.where(AuditLogModel.created_at <= created_to)

        return stmt
