"""
Retry and retry service.

This module provides:
- Retry logic and scheduling
- Polling mechanisms
- Timeout handling
- Dead-letter queue decisions
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.exceptions import (
    InvoiceNotFoundError,
    SessionNotFoundError,
    ValidationError,
)
from app.core.logging import get_bound_logger, log_timed_operation
from app.infrastructure.persistence.models.audit_log_model import (
    AuditEventOutcome,
    AuditEventSeverity,
)


class RetryService:
    """
    Service responsible for retrying failed invoice submissions and polling
    pending KSeF session/invoice statuses.

    Expected collaborators:
    - invoice_repository
    - session_repository
    - invoice_service
    - status_service
    - audit_service
    - settings
    """

    TERMINAL_INVOICE_STATUSES = {
        "accepted",
        "rejected",
        "dead_letter",
        "archived",
    }

    TERMINAL_SESSION_STATUSES = {
        "closed",
        "failed",
        "dead_letter",
        "archived",
    }

    DEFAULT_SUBMISSION_RETRY_LIMIT = 5
    DEFAULT_SESSION_POLL_RETRY_LIMIT = 20
    DEFAULT_RETRY_BASE_SECONDS = 60
    DEFAULT_MAX_RETRY_DELAY_SECONDS = 3600
    DEFAULT_SUBMISSION_TIMEOUT_SECONDS = 6 * 3600
    DEFAULT_SESSION_TIMEOUT_SECONDS = 6 * 3600

    def __init__(
        self,
        *,
        settings: Any,
        invoice_repository: Any,
        session_repository: Any,
        invoice_service: Any,
        status_service: Any,
        audit_service: Any,
    ) -> None:
        self.settings = settings
        self.invoice_repository = invoice_repository
        self.session_repository = session_repository
        self.invoice_service = invoice_service
        self.status_service = status_service
        self.audit_service = audit_service

        self.logger = get_bound_logger(__name__, component="retry_service")

    async def retry_failed_submissions(self, *, limit: int = 100) -> dict[str, Any]:
        """
        Retry failed or retryable invoice submissions.

        Expected repository contract:
        - invoice_repository.list_retry_candidates(limit=...)
        - invoice_repository.update_retry_state(...)
        - invoice_repository.mark_dead_letter(...)
        """
        with log_timed_operation(self.logger, "retry_failed_submissions", limit=limit):
            candidates = await self.invoice_repository.list_retry_candidates(
                limit=limit
            )

            summary = {
                "scanned": len(candidates),
                "retried": 0,
                "skipped": 0,
                "dead_lettered": 0,
                "failed": 0,
                "items": [],
            }

            for record in candidates:
                item_result = await self._process_submission_retry_candidate(record)
                summary["items"].append(item_result)
                self._increment_summary(summary, item_result["result"])

            return summary

    async def poll_pending_statuses(self, *, limit: int = 100) -> dict[str, Any]:
        """
        Poll KSeF status for pending sessions and invoices.

        Expected repository contract:
        - session_repository.list_poll_candidates(limit=...)
        - invoice_repository.list_status_poll_candidates(limit=...)
        """
        with log_timed_operation(self.logger, "poll_pending_statuses", limit=limit):
            session_candidates = await self.session_repository.list_poll_candidates(
                limit=limit
            )
            invoice_candidates = (
                await self.invoice_repository.list_status_poll_candidates(limit=limit)
            )

            summary = {
                "sessions_scanned": len(session_candidates),
                "sessions_polled": 0,
                "sessions_skipped": 0,
                "sessions_dead_lettered": 0,
                "sessions_failed": 0,
                "invoices_scanned": len(invoice_candidates),
                "invoices_polled": 0,
                "invoices_skipped": 0,
                "invoices_dead_lettered": 0,
                "invoices_failed": 0,
                "session_items": [],
                "invoice_items": [],
            }

            for session_record in session_candidates:
                item_result = await self._process_session_poll_candidate(session_record)
                summary["session_items"].append(item_result)
                self._increment_poll_summary(summary, "sessions", item_result["result"])

            for invoice_record in invoice_candidates:
                item_result = await self._process_invoice_poll_candidate(invoice_record)
                summary["invoice_items"].append(item_result)
                self._increment_poll_summary(summary, "invoices", item_result["result"])

            return summary

    async def sync_pending(self, *, limit: int = 100) -> dict[str, Any]:
        """
        Combined synchronization entry point:
        - poll pending statuses
        - retry failed invoice submissions
        """
        with log_timed_operation(self.logger, "sync_pending", limit=limit):
            poll_summary = await self.poll_pending_statuses(limit=limit)
            retry_summary = await self.retry_failed_submissions(limit=limit)

            return {
                "polled": poll_summary,
                "retried": retry_summary,
            }

    async def retry_submission(self, submission_id: str) -> dict[str, Any]:
        """
        Retry a single submission by ID.
        """
        record = await self.invoice_repository.get_by_id(submission_id)
        if record is None:
            raise InvoiceNotFoundError(
                message="Invoice submission not found.",
                details={"submission_id": submission_id},
            )

        return await self._process_submission_retry_candidate(record)

    async def poll_session(self, reference_number: str) -> dict[str, Any]:
        """
        Poll a single session by reference number.
        """
        record = await self.session_repository.get_by_reference_number(reference_number)
        if record is None:
            raise SessionNotFoundError(
                message="KSeF session not found.",
                details={"reference_number": reference_number},
            )

        return await self._process_session_poll_candidate(record)

    async def poll_invoice(self, submission_id: str) -> dict[str, Any]:
        """
        Poll status for a single invoice submission.
        """
        record = await self.invoice_repository.get_by_id(submission_id)
        if record is None:
            raise InvoiceNotFoundError(
                message="Invoice submission not found.",
                details={"submission_id": submission_id},
            )

        return await self._process_invoice_poll_candidate(record)

    async def _process_submission_retry_candidate(self, record: Any) -> dict[str, Any]:
        """
        Process one retryable invoice submission candidate.
        """
        submission_id = str(self._read_attr(record, "id"))
        tenant_id = self._read_attr(record, "tenant_id")
        local_status = self._string_or_none(self._read_attr(record, "local_status"))

        if local_status in self.TERMINAL_INVOICE_STATUSES:
            return {
                "type": "submission_retry",
                "submission_id": submission_id,
                "result": "skipped",
                "reason": f"terminal_status:{local_status}",
            }

        if self._is_submission_timeout_exceeded(record):
            await self._mark_submission_dead_letter(
                record,
                reason="timeout_exceeded",
            )
            return {
                "type": "submission_retry",
                "submission_id": submission_id,
                "result": "dead_lettered",
                "reason": "timeout_exceeded",
            }

        if not self._should_retry_submission(record):
            return {
                "type": "submission_retry",
                "submission_id": submission_id,
                "result": "skipped",
                "reason": "not_due_or_retry_limit_exceeded",
            }

        try:
            await self.invoice_repository.update_retry_state(
                submission_id=submission_id,
                retry_count=self._submission_retry_count(record) + 1,
                last_retry_at=self._now(),
                next_retry_at=self._compute_next_retry_at(
                    retry_count=self._submission_retry_count(record) + 1,
                    base_seconds=self._submission_retry_base_seconds(),
                    max_delay_seconds=self._max_retry_delay_seconds(),
                ),
                updated_at=self._now(),
            )

            response = await self.invoice_service.resubmit_invoice(submission_id)

            await self.audit_service.log_invoice_event(
                event_name="invoice_retry_succeeded",
                message="Invoice retry completed successfully.",
                outcome=AuditEventOutcome.SUCCESS,
                severity=AuditEventSeverity.INFO,
                tenant_id=tenant_id,
                submission_id=submission_id,
                invoice_reference_number=self._read_attr(
                    response, "invoice_reference_number"
                ),
                session_reference_number=self._read_attr(
                    response, "session_reference_number"
                ),
                context={"response": self._serialize(response)},
            )

            return {
                "type": "submission_retry",
                "submission_id": submission_id,
                "result": "retried",
            }
        except Exception as exc:
            await self.audit_service.log_invoice_event(
                event_name="invoice_retry_failed",
                message="Invoice retry failed.",
                outcome=AuditEventOutcome.FAILURE,
                severity=AuditEventSeverity.ERROR,
                tenant_id=tenant_id,
                submission_id=submission_id,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

            if (
                self._submission_retry_count(record) + 1
                >= self._submission_retry_limit()
            ):
                await self._mark_submission_dead_letter(
                    record,
                    reason="retry_limit_exceeded_after_failure",
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                )
                return {
                    "type": "submission_retry",
                    "submission_id": submission_id,
                    "result": "dead_lettered",
                    "reason": "retry_limit_exceeded_after_failure",
                }

            return {
                "type": "submission_retry",
                "submission_id": submission_id,
                "result": "failed",
                "reason": str(exc),
            }

    async def _process_session_poll_candidate(self, record: Any) -> dict[str, Any]:
        """
        Process one session polling candidate.
        """
        reference_number = self._string_or_none(
            self._read_attr(record, "reference_number")
        )
        tenant_id = self._read_attr(record, "tenant_id")
        local_status = self._string_or_none(self._read_attr(record, "local_status"))

        if not reference_number:
            raise ValidationError(
                message="Session record does not contain reference number.",
                details={"record": self._serialize(record)},
            )

        if local_status in self.TERMINAL_SESSION_STATUSES:
            return {
                "type": "session_poll",
                "reference_number": reference_number,
                "result": "skipped",
                "reason": f"terminal_status:{local_status}",
            }

        if self._is_session_timeout_exceeded(record):
            await self._mark_session_dead_letter(
                record,
                reason="timeout_exceeded",
            )
            return {
                "type": "session_poll",
                "reference_number": reference_number,
                "result": "dead_lettered",
                "reason": "timeout_exceeded",
            }

        if not self._should_poll_session(record):
            return {
                "type": "session_poll",
                "reference_number": reference_number,
                "result": "skipped",
                "reason": "not_due_or_retry_limit_exceeded",
            }

        try:
            await self.session_repository.update_poll_state(
                reference_number=reference_number,
                poll_retry_count=self._session_poll_retry_count(record) + 1,
                last_polled_at=self._now(),
                next_poll_at=self._compute_next_retry_at(
                    retry_count=self._session_poll_retry_count(record) + 1,
                    base_seconds=self._session_poll_base_seconds(),
                    max_delay_seconds=self._max_retry_delay_seconds(),
                ),
                updated_at=self._now(),
            )

            response = await self.status_service.poll_session_status(reference_number)

            await self.audit_service.log_status_event(
                event_name="session_poll_succeeded",
                message="Session status polling completed successfully.",
                outcome=AuditEventOutcome.SUCCESS,
                severity=AuditEventSeverity.INFO,
                tenant_id=tenant_id,
                session_reference_number=reference_number,
                context={"response": self._serialize(response)},
            )

            return {
                "type": "session_poll",
                "reference_number": reference_number,
                "result": "polled",
            }
        except Exception as exc:
            await self.audit_service.log_status_event(
                event_name="session_poll_failed",
                message="Session status polling failed.",
                outcome=AuditEventOutcome.FAILURE,
                severity=AuditEventSeverity.ERROR,
                tenant_id=tenant_id,
                session_reference_number=reference_number,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

            if (
                self._session_poll_retry_count(record) + 1
                >= self._session_poll_retry_limit()
            ):
                await self._mark_session_dead_letter(
                    record,
                    reason="retry_limit_exceeded_after_failure",
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                )
                return {
                    "type": "session_poll",
                    "reference_number": reference_number,
                    "result": "dead_lettered",
                    "reason": "retry_limit_exceeded_after_failure",
                }

            return {
                "type": "session_poll",
                "reference_number": reference_number,
                "result": "failed",
                "reason": str(exc),
            }

    async def _process_invoice_poll_candidate(self, record: Any) -> dict[str, Any]:
        """
        Process one invoice status polling candidate.
        """
        submission_id = str(self._read_attr(record, "id"))
        tenant_id = self._read_attr(record, "tenant_id")
        invoice_reference_number = self._string_or_none(
            self._read_attr(record, "invoice_reference_number")
        )
        local_status = self._string_or_none(self._read_attr(record, "local_status"))

        if local_status in self.TERMINAL_INVOICE_STATUSES:
            return {
                "type": "invoice_poll",
                "submission_id": submission_id,
                "result": "skipped",
                "reason": f"terminal_status:{local_status}",
            }

        if not invoice_reference_number:
            return {
                "type": "invoice_poll",
                "submission_id": submission_id,
                "result": "skipped",
                "reason": "missing_invoice_reference_number",
            }

        if self._is_submission_timeout_exceeded(record):
            await self._mark_submission_dead_letter(
                record,
                reason="timeout_exceeded",
            )
            return {
                "type": "invoice_poll",
                "submission_id": submission_id,
                "result": "dead_lettered",
                "reason": "timeout_exceeded",
            }

        if not self._should_poll_invoice(record):
            return {
                "type": "invoice_poll",
                "submission_id": submission_id,
                "result": "skipped",
                "reason": "not_due_or_retry_limit_exceeded",
            }

        try:
            await self.invoice_repository.update_status_poll_state(
                submission_id=submission_id,
                poll_retry_count=self._invoice_poll_retry_count(record) + 1,
                last_polled_at=self._now(),
                next_poll_at=self._compute_next_retry_at(
                    retry_count=self._invoice_poll_retry_count(record) + 1,
                    base_seconds=self._invoice_poll_base_seconds(),
                    max_delay_seconds=self._max_retry_delay_seconds(),
                ),
                updated_at=self._now(),
            )

            response = await self.status_service.poll_invoice_status(
                invoice_reference_number
            )

            await self.audit_service.log_status_event(
                event_name="invoice_poll_succeeded",
                message="Invoice status polling completed successfully.",
                outcome=AuditEventOutcome.SUCCESS,
                severity=AuditEventSeverity.INFO,
                tenant_id=tenant_id,
                invoice_reference_number=invoice_reference_number,
                submission_id=submission_id,
                context={"response": self._serialize(response)},
            )

            return {
                "type": "invoice_poll",
                "submission_id": submission_id,
                "result": "polled",
            }
        except Exception as exc:
            await self.audit_service.log_status_event(
                event_name="invoice_poll_failed",
                message="Invoice status polling failed.",
                outcome=AuditEventOutcome.FAILURE,
                severity=AuditEventSeverity.ERROR,
                tenant_id=tenant_id,
                invoice_reference_number=invoice_reference_number,
                submission_id=submission_id,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

            if (
                self._invoice_poll_retry_count(record) + 1
                >= self._submission_retry_limit()
            ):
                await self._mark_submission_dead_letter(
                    record,
                    reason="poll_retry_limit_exceeded_after_failure",
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                )
                return {
                    "type": "invoice_poll",
                    "submission_id": submission_id,
                    "result": "dead_lettered",
                    "reason": "poll_retry_limit_exceeded_after_failure",
                }

            return {
                "type": "invoice_poll",
                "submission_id": submission_id,
                "result": "failed",
                "reason": str(exc),
            }

    async def _mark_submission_dead_letter(
        self,
        record: Any,
        *,
        reason: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Mark invoice submission as dead-lettered.
        """
        submission_id = str(self._read_attr(record, "id"))
        tenant_id = self._read_attr(record, "tenant_id")

        await self.invoice_repository.mark_dead_letter(
            submission_id=submission_id,
            local_status="dead_letter",
            transport_status="dead_letter",
            dead_letter_reason=reason,
            error_code=error_code,
            error_message=error_message,
            updated_at=self._now(),
        )

        await self.audit_service.log_invoice_event(
            event_name="invoice_dead_lettered",
            message="Invoice submission moved to dead-letter state.",
            outcome=AuditEventOutcome.FAILURE,
            severity=AuditEventSeverity.WARNING,
            tenant_id=tenant_id,
            submission_id=submission_id,
            error_code=error_code,
            error_message=error_message,
            context={"reason": reason},
        )

    async def _mark_session_dead_letter(
        self,
        record: Any,
        *,
        reason: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Mark session as dead-lettered.
        """
        reference_number = self._string_or_none(
            self._read_attr(record, "reference_number")
        )
        tenant_id = self._read_attr(record, "tenant_id")

        await self.session_repository.mark_dead_letter(
            reference_number=reference_number,
            local_status="dead_letter",
            dead_letter_reason=reason,
            error_code=error_code,
            error_message=error_message,
            updated_at=self._now(),
        )

        await self.audit_service.log_session_event(
            event_name="session_dead_lettered",
            message="KSeF session moved to dead-letter state.",
            outcome=AuditEventOutcome.FAILURE,
            severity=AuditEventSeverity.WARNING,
            tenant_id=tenant_id,
            session_reference_number=reference_number,
            error_code=error_code,
            error_message=error_message,
            context={"reason": reason},
        )

    def _should_retry_submission(self, record: Any) -> bool:
        """
        Decide whether invoice submission should be retried now.
        """
        retry_count = self._submission_retry_count(record)
        if retry_count >= self._submission_retry_limit():
            return False

        next_retry_at = self._read_attr(record, "next_retry_at")
        if next_retry_at is None:
            return True

        return self._normalize_dt(next_retry_at) <= self._now()

    def _should_poll_session(self, record: Any) -> bool:
        """
        Decide whether session status should be polled now.
        """
        retry_count = self._session_poll_retry_count(record)
        if retry_count >= self._session_poll_retry_limit():
            return False

        next_poll_at = self._read_attr(record, "next_poll_at")
        if next_poll_at is None:
            return True

        return self._normalize_dt(next_poll_at) <= self._now()

    def _should_poll_invoice(self, record: Any) -> bool:
        """
        Decide whether invoice status should be polled now.
        """
        retry_count = self._invoice_poll_retry_count(record)
        if retry_count >= self._submission_retry_limit():
            return False

        next_poll_at = self._read_attr(record, "next_poll_at")
        if next_poll_at is None:
            return True

        return self._normalize_dt(next_poll_at) <= self._now()

    def _is_submission_timeout_exceeded(self, record: Any) -> bool:
        """
        Check whether invoice submission exceeded configured timeout.
        """
        started_at = (
            self._read_attr(record, "created_at")
            or self._read_attr(record, "submitted_at")
            or self._read_attr(record, "updated_at")
        )
        if started_at is None:
            return False

        timeout_seconds = int(
            getattr(
                self.settings,
                "ksef_submission_timeout_seconds",
                self.DEFAULT_SUBMISSION_TIMEOUT_SECONDS,
            )
        )
        deadline = self._normalize_dt(started_at) + timedelta(seconds=timeout_seconds)
        return self._now() > deadline

    def _is_session_timeout_exceeded(self, record: Any) -> bool:
        """
        Check whether session polling exceeded configured timeout.
        """
        started_at = (
            self._read_attr(record, "opened_at")
            or self._read_attr(record, "created_at")
            or self._read_attr(record, "updated_at")
        )
        if started_at is None:
            return False

        timeout_seconds = int(
            getattr(
                self.settings,
                "ksef_session_timeout_seconds",
                self.DEFAULT_SESSION_TIMEOUT_SECONDS,
            )
        )
        deadline = self._normalize_dt(started_at) + timedelta(seconds=timeout_seconds)
        return self._now() > deadline

    def _compute_next_retry_at(
        self,
        *,
        retry_count: int,
        base_seconds: int,
        max_delay_seconds: int,
    ) -> datetime:
        """
        Compute next retry time using capped exponential backoff.
        """
        exponent = max(retry_count - 1, 0)
        delay_seconds = min(base_seconds * (2**exponent), max_delay_seconds)
        return self._now() + timedelta(seconds=delay_seconds)

    def _submission_retry_limit(self) -> int:
        return int(
            getattr(
                self.settings,
                "ksef_submission_retry_limit",
                self.DEFAULT_SUBMISSION_RETRY_LIMIT,
            )
        )

    def _session_poll_retry_limit(self) -> int:
        return int(
            getattr(
                self.settings,
                "ksef_session_poll_retry_limit",
                self.DEFAULT_SESSION_POLL_RETRY_LIMIT,
            )
        )

    def _submission_retry_base_seconds(self) -> int:
        return int(
            getattr(
                self.settings,
                "ksef_submission_retry_base_seconds",
                self.DEFAULT_RETRY_BASE_SECONDS,
            )
        )

    def _session_poll_base_seconds(self) -> int:
        return int(
            getattr(
                self.settings,
                "ksef_session_poll_base_seconds",
                self.DEFAULT_RETRY_BASE_SECONDS,
            )
        )

    def _invoice_poll_base_seconds(self) -> int:
        return int(
            getattr(
                self.settings,
                "ksef_invoice_poll_base_seconds",
                self.DEFAULT_RETRY_BASE_SECONDS,
            )
        )

    def _max_retry_delay_seconds(self) -> int:
        return int(
            getattr(
                self.settings,
                "ksef_max_retry_delay_seconds",
                self.DEFAULT_MAX_RETRY_DELAY_SECONDS,
            )
        )

    def _submission_retry_count(self, record: Any) -> int:
        return int(self._read_attr(record, "retry_count", 0) or 0)

    def _session_poll_retry_count(self, record: Any) -> int:
        return int(self._read_attr(record, "poll_retry_count", 0) or 0)

    def _invoice_poll_retry_count(self, record: Any) -> int:
        return int(self._read_attr(record, "poll_retry_count", 0) or 0)

    def _serialize(self, value: Any) -> Any:
        """
        Convert objects into plain JSON-friendly structures.
        """
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {key: self._serialize(val) for key, val in value.items()}

        if isinstance(value, list):
            return [self._serialize(item) for item in value]

        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")

        if hasattr(value, "dict"):
            return value.dict()

        if hasattr(value, "__dict__"):
            return {
                key: self._serialize(val)
                for key, val in vars(value).items()
                if not key.startswith("_")
            }

        return value

    def _read_attr(self, obj: Any, name: str, default: Any = None) -> Any:
        """
        Safe dict/attribute reader.
        """
        if obj is None:
            return default

        if isinstance(obj, dict):
            return obj.get(name, default)

        return getattr(obj, name, default)

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_dt(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _increment_summary(summary: dict[str, Any], result: str) -> None:
        if result == "retried":
            summary["retried"] += 1
        elif result == "skipped":
            summary["skipped"] += 1
        elif result == "dead_lettered":
            summary["dead_lettered"] += 1
        else:
            summary["failed"] += 1

    @staticmethod
    def _increment_poll_summary(
        summary: dict[str, Any], prefix: str, result: str
    ) -> None:
        if result == "polled":
            summary[f"{prefix}_polled"] += 1
        elif result == "skipped":
            summary[f"{prefix}_skipped"] += 1
        elif result == "dead_lettered":
            summary[f"{prefix}_dead_lettered"] += 1
        else:
            summary[f"{prefix}_failed"] += 1
