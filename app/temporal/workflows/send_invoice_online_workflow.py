"""
Online invoice submission workflow.

This module provides:
- End-to-end online invoice submission
- Session management integration
- Invoice validation and processing
- Status tracking and UPO generation
"""

from __future__ import annotations

from temporalio import workflow
from temporalio.exceptions import ActivityError, ApplicationError

from app.temporal.models.common import (
    DEFAULT_ACTIVITY_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
    POLL_INTERVAL,
    SHORT_ACTIVITY_TIMEOUT,
)
from app.temporal.models.invoice_models import (
    SendInvoiceOnlineInput,
    SendInvoiceOnlineResult,
)


@workflow.defn
class SendInvoiceOnlineWorkflow:
    MAX_POLL_ATTEMPTS = 60

    def __init__(self) -> None:
        self._current_step = "created"
        self._submission_id: str | None = None
        self._session_reference_number: str | None = None
        self._invoice_reference_number: str | None = None
        self._cancel_requested = False
        self._cancel_reason: str | None = None

    @workflow.run
    async def run(self, input: SendInvoiceOnlineInput) -> SendInvoiceOnlineResult:
        try:
            self._current_step = "create_submission_record"
            self._submission_id = await workflow.execute_activity(
                "create_submission_record",
                {
                    "invoice_id": input.invoice_id,
                    "company_id": input.company_id,
                    "workflow_id": workflow.info().workflow_id,
                    "correlation_id": input.correlation_id,
                    "requested_by": input.requested_by,
                    "environment": input.environment,
                },
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            await workflow.execute_activity(
                "append_audit_event",
                {
                    "entity_type": "invoice_submission",
                    "entity_id": self._submission_id,
                    "event_type": "workflow_started",
                    "payload": {"invoice_id": input.invoice_id},
                },
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "load_invoice_for_send"
            invoice_payload = await workflow.execute_activity(
                "load_invoice_for_send",
                input.invoice_id,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "validate_invoice_for_send"
            await workflow.execute_activity(
                "validate_invoice_for_send",
                invoice_payload,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "ensure_auth_context"
            auth_context = await workflow.execute_activity(
                "ensure_auth_context",
                {
                    "company_id": input.company_id,
                    "environment": input.environment,
                    "auth_mode": "token",
                },
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            access_token = str(auth_context["access_token"])

            self._current_step = "open_online_session"
            session_result = await workflow.execute_activity(
                "open_online_session",
                {
                    "company_id": input.company_id,
                    "environment": input.environment,
                    "access_token": access_token,
                    "form_code": {
                        "systemCode": "FA (3)",
                        "schemaVersion": "1-0E",
                        "value": "FA",
                    },
                    "encryption": auth_context["session_encryption"],
                },
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )
            self._session_reference_number = str(session_result["referenceNumber"])

            self._current_step = "mark_submission_started"
            await workflow.execute_activity(
                "mark_submission_started",
                {
                    "submission_id": self._submission_id,
                    "session_reference_number": self._session_reference_number,
                },
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "build_fa3_xml"
            xml_text = await workflow.execute_activity(
                "build_fa3_xml",
                invoice_payload,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "encrypt_invoice_xml"
            encrypted_payload = await workflow.execute_activity(
                "encrypt_invoice_xml",
                {
                    "xml_text": xml_text,
                    "company_id": input.company_id,
                    "environment": input.environment,
                },
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "send_invoice_online"
            send_result = await workflow.execute_activity(
                "send_invoice_online",
                {
                    "session_reference_number": self._session_reference_number,
                    "access_token": access_token,
                    **encrypted_payload,
                },
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )
            self._invoice_reference_number = str(send_result["referenceNumber"])

            self._current_step = "attach_invoice_reference_number"
            await workflow.execute_activity(
                "attach_invoice_reference_number",
                {
                    "submission_id": self._submission_id,
                    "invoice_reference_number": self._invoice_reference_number,
                },
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "close_online_session"
            await workflow.execute_activity(
                "close_online_session",
                {
                    "session_reference_number": self._session_reference_number,
                    "access_token": access_token,
                },
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "poll_invoice_status"
            final_status_response = await self._poll_invoice_status(
                access_token=access_token,
                session_reference_number=self._session_reference_number,
                invoice_reference_number=self._invoice_reference_number,
            )
            final_status = self._normalize_terminal_status(final_status_response)

            self._current_step = "mark_submission_terminal"
            await workflow.execute_activity(
                "mark_submission_terminal",
                {
                    "submission_id": self._submission_id,
                    "final_status": final_status,
                    "error_code": None,
                    "error_message": None,
                },
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            await workflow.execute_activity(
                "append_audit_event",
                {
                    "entity_type": "invoice_submission",
                    "entity_id": self._submission_id,
                    "event_type": "workflow_completed",
                    "payload": {"final_status": final_status},
                },
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            self._current_step = "completed"
            return SendInvoiceOnlineResult(
                invoice_id=input.invoice_id,
                submission_id=self._submission_id,
                session_reference_number=self._session_reference_number,
                invoice_reference_number=self._invoice_reference_number,
                final_status=final_status,
                upo_storage_key=None,
            )

        except ActivityError as exc:
            error_message = self._render_activity_error(exc)

            if self._submission_id:
                await workflow.execute_activity(
                    "mark_submission_terminal",
                    {
                        "submission_id": self._submission_id,
                        "final_status": "failed",
                        "error_code": "activity_error",
                        "error_message": error_message,
                    },
                    start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                    retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                )
                await workflow.execute_activity(
                    "append_audit_event",
                    {
                        "entity_type": "invoice_submission",
                        "entity_id": self._submission_id,
                        "event_type": "workflow_failed",
                        "payload": {"error": error_message},
                    },
                    start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                    retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                )

            raise ApplicationError(
                f"Invoice send workflow failed: {error_message}",
                non_retryable=True,
            ) from exc

    async def _poll_invoice_status(
        self,
        *,
        access_token: str,
        session_reference_number: str,
        invoice_reference_number: str,
    ) -> dict:
        last_status: dict | None = None

        for _ in range(self.MAX_POLL_ATTEMPTS):
            if self._cancel_requested:
                raise ApplicationError(
                    f"Workflow cancelled: {self._cancel_reason or 'no reason'}",
                    non_retryable=True,
                )

            last_status = await workflow.execute_activity(
                "get_invoice_status",
                {
                    "access_token": access_token,
                    "session_reference_number": session_reference_number,
                    "invoice_reference_number": invoice_reference_number,
                },
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )

            if self._is_terminal_status(last_status):
                return last_status

            await workflow.sleep(POLL_INTERVAL)

        raise ApplicationError(
            f"Invoice status did not reach terminal state. last_status={last_status}",
            non_retryable=True,
        )

    @staticmethod
    def _is_terminal_status(status_response: dict) -> bool:
        if "isTerminal" in status_response:
            return bool(status_response["isTerminal"])

        status = status_response.get("status") or {}
        code = status.get("code")
        return code not in {100, 110, 120, 150}

    @staticmethod
    def _normalize_terminal_status(status_response: dict) -> str:
        status = status_response.get("status") or {}
        code = status.get("code")

        if code == 200:
            return "accepted"
        if code in {100, 110, 120, 150}:
            return "processing"
        return "failed"

    @staticmethod
    def _render_activity_error(exc: ActivityError) -> str:
        cause = exc.cause
        if cause:
            return f"{type(cause).__name__}: {cause}"
        return str(exc)

    @workflow.query
    def current_step(self) -> str:
        return self._current_step

    @workflow.query
    def local_submission_id(self) -> str | None:
        return self._submission_id

    @workflow.query
    def session_reference_number(self) -> str | None:
        return self._session_reference_number

    @workflow.query
    def invoice_reference_number(self) -> str | None:
        return self._invoice_reference_number

    @workflow.signal
    async def cancel_submission(self, reason: str) -> None:
        self._cancel_requested = True
        self._cancel_reason = reason
