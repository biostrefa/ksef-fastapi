"""
Audit service.

This module provides:
- High-level audit event logging
- Event category helpers
- Webhook audit logging
- Security and operational audit logging
- Audit query helpers
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.infrastructure.persistence.models.audit_log_model import (
    AuditEventCategory,
    AuditEventOutcome,
    AuditEventSeverity,
    AuditLogModel,
)
from app.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)


class AuditService:
    """
    High-level service for writing and querying audit events.

    This service is intentionally thin:
    - repository handles persistence,
    - service provides semantic methods for application layers.
    """

    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self.audit_log_repository = audit_log_repository

    async def log_event(
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
        payload: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        event_time: datetime | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Log a generic audit event.
        """
        return await self.audit_log_repository.create(
            event_category=event_category,
            event_name=event_name,
            message=message,
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
            payload_json=payload,
            headers_json=headers,
            context_json=context,
            tags_json=tags,
            event_time=event_time,
            commit=commit,
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
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Log authentication-related event.
        """
        return await self.audit_log_repository.log_auth_event(
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
            payload_json=payload,
            context_json=context,
            tags_json=tags,
        )

    async def log_session_event(
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
        session_reference_number: str | None = None,
        http_status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Log KSeF session-related event.
        """
        return await self.log_event(
            event_category=AuditEventCategory.SESSION,
            event_name=event_name,
            message=message,
            outcome=outcome,
            severity=severity,
            component="session_service",
            tenant_id=tenant_id,
            actor_id=actor_id,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            session_reference_number=session_reference_number,
            http_status_code=http_status_code,
            error_code=error_code,
            error_message=error_message,
            payload=payload,
            context=context,
            tags=tags,
            commit=commit,
        )

    async def log_invoice_event(
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
        session_reference_number: str | None = None,
        invoice_reference_number: str | None = None,
        submission_id: str | None = None,
        http_status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Log invoice lifecycle event.
        """
        return await self.log_event(
            event_category=AuditEventCategory.INVOICE,
            event_name=event_name,
            message=message,
            outcome=outcome,
            severity=severity,
            component="invoice_service",
            tenant_id=tenant_id,
            actor_id=actor_id,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            session_reference_number=session_reference_number,
            invoice_reference_number=invoice_reference_number,
            submission_id=submission_id,
            http_status_code=http_status_code,
            error_code=error_code,
            error_message=error_message,
            payload=payload,
            context=context,
            tags=tags,
            commit=commit,
        )

    async def log_status_event(
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
        session_reference_number: str | None = None,
        invoice_reference_number: str | None = None,
        submission_id: str | None = None,
        http_status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Log status polling / UPO / monitoring event.
        """
        return await self.log_event(
            event_category=AuditEventCategory.STATUS,
            event_name=event_name,
            message=message,
            outcome=outcome,
            severity=severity,
            component="status_service",
            tenant_id=tenant_id,
            actor_id=actor_id,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            session_reference_number=session_reference_number,
            invoice_reference_number=invoice_reference_number,
            submission_id=submission_id,
            http_status_code=http_status_code,
            error_code=error_code,
            error_message=error_message,
            payload=payload,
            context=context,
            tags=tags,
            commit=commit,
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
        payload: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Log security-related event.
        """
        return await self.audit_log_repository.log_security_event(
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
            payload_json=payload,
            headers_json=headers,
            context_json=context,
            tags_json=tags,
        )

    async def log_webhook_received(
        self,
        *,
        source: str,
        payload: dict[str, Any] | None,
        headers: dict[str, Any] | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        http_method: str | None = None,
        http_path: str | None = None,
        http_status_code: int | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> AuditLogModel:
        """
        Log incoming webhook/callback receipt.

        This method matches the webhook_router usage.
        """
        return await self.audit_log_repository.log_webhook_event(
            source=source,
            message="Webhook received.",
            outcome=AuditEventOutcome.SUCCESS,
            severity=AuditEventSeverity.INFO,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            http_method=http_method,
            http_path=http_path,
            http_status_code=http_status_code,
            payload_json=payload,
            headers_json=headers,
            context_json=context,
            tags_json=tags,
        )

    async def log_repository_error(
        self,
        *,
        event_name: str,
        message: str,
        error_code: str | None = None,
        error_message: str | None = None,
        component: str | None = None,
        tenant_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        commit: bool = True,
    ) -> AuditLogModel:
        """
        Log repository/persistence failure.
        """
        return await self.log_event(
            event_category=AuditEventCategory.REPOSITORY,
            event_name=event_name,
            message=message,
            outcome=AuditEventOutcome.FAILURE,
            severity=AuditEventSeverity.ERROR,
            component=component,
            tenant_id=tenant_id,
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            error_code=error_code,
            error_message=error_message,
            context=context,
            tags=tags,
            commit=commit,
        )

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
        Query audit events.
        """
        return await self.audit_log_repository.list_events(
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
            limit=limit,
            offset=offset,
        )

    async def get_recent_for_session(
        self,
        session_reference_number: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogModel]:
        """
        Return recent audit events for a KSeF session.
        """
        return await self.audit_log_repository.get_recent_for_session(
            session_reference_number=session_reference_number,
            limit=limit,
        )

    async def get_recent_for_invoice(
        self,
        invoice_reference_number: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogModel]:
        """
        Return recent audit events for a KSeF invoice reference number.
        """
        return await self.audit_log_repository.get_recent_for_invoice(
            invoice_reference_number=invoice_reference_number,
            limit=limit,
        )

    async def get_recent_for_submission(
        self,
        submission_id: str,
        *,
        limit: int = 50,
    ) -> list[AuditLogModel]:
        """
        Return recent audit events for a local submission ID.
        """
        return await self.audit_log_repository.get_recent_for_submission(
            submission_id=submission_id,
            limit=limit,
        )

    async def delete_older_than(
        self,
        *,
        older_than: datetime,
        commit: bool = True,
    ) -> int:
        """
        Delete audit entries older than the provided timestamp.
        """
        return await self.audit_log_repository.delete_older_than(
            older_than=older_than,
            commit=commit,
        )
