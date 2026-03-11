"""
Persistence-related activities.

This module provides:
- Database read/write activities
- Repository operation activities
- Transaction management activities
- Data consistency activities
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from temporalio import activity
from temporalio.exceptions import ApplicationError


@runtime_checkable
class SubmissionRepositoryProtocol(Protocol):
    async def create_submission_if_absent(
        self,
        *,
        invoice_id: str,
        company_id: str,
        workflow_id: str,
        correlation_id: str,
        requested_by: str | None,
        environment: str,
    ) -> str: ...

    async def mark_submission_started(
        self,
        *,
        submission_id: str,
        session_reference_number: str,
    ) -> None: ...

    async def attach_invoice_reference_number(
        self,
        *,
        submission_id: str,
        invoice_reference_number: str,
    ) -> None: ...

    async def mark_submission_terminal(
        self,
        *,
        submission_id: str,
        final_status: str,
        error_code: str | None,
        error_message: str | None,
    ) -> None: ...

    async def load_pending_submissions_for_reconciliation(
        self,
        *,
        company_id: str | None,
        environment: str,
        limit: int,
    ) -> list[dict[str, Any]]: ...

    async def mark_submission_reconciled(
        self,
        *,
        submission_id: str,
        final_status: str,
    ) -> None: ...


class PersistenceActivities:
    def __init__(self, *, submission_repository: SubmissionRepositoryProtocol) -> None:
        self.submission_repository = submission_repository

    @activity.defn(name="create_submission_record")
    async def create_submission_record(self, input: dict[str, Any]) -> str:
        required_keys = {
            "invoice_id",
            "company_id",
            "workflow_id",
            "correlation_id",
            "environment",
        }
        missing = required_keys - set(input.keys())
        if missing:
            raise ApplicationError(
                f"Missing required fields: {sorted(missing)}",
                type="InvalidPersistenceInput",
                non_retryable=True,
            )

        return await self.submission_repository.create_submission_if_absent(
            invoice_id=str(input["invoice_id"]),
            company_id=str(input["company_id"]),
            workflow_id=str(input["workflow_id"]),
            correlation_id=str(input["correlation_id"]),
            requested_by=str(input["requested_by"])
            if input.get("requested_by") is not None
            else None,
            environment=str(input["environment"]),
        )

    @activity.defn(name="mark_submission_started")
    async def mark_submission_started(self, input: dict[str, Any]) -> None:
        submission_id = input.get("submission_id")
        session_reference_number = input.get("session_reference_number")
        if not submission_id or not session_reference_number:
            raise ApplicationError(
                "submission_id and session_reference_number are required",
                type="InvalidPersistenceInput",
                non_retryable=True,
            )
        await self.submission_repository.mark_submission_started(
            submission_id=str(submission_id),
            session_reference_number=str(session_reference_number),
        )

    @activity.defn(name="attach_invoice_reference_number")
    async def attach_invoice_reference_number(self, input: dict[str, Any]) -> None:
        submission_id = input.get("submission_id")
        invoice_reference_number = input.get("invoice_reference_number")
        if not submission_id or not invoice_reference_number:
            raise ApplicationError(
                "submission_id and invoice_reference_number are required",
                type="InvalidPersistenceInput",
                non_retryable=True,
            )
        await self.submission_repository.attach_invoice_reference_number(
            submission_id=str(submission_id),
            invoice_reference_number=str(invoice_reference_number),
        )

    @activity.defn(name="mark_submission_terminal")
    async def mark_submission_terminal(self, input: dict[str, Any]) -> None:
        submission_id = input.get("submission_id")
        final_status = input.get("final_status")
        if not submission_id or not final_status:
            raise ApplicationError(
                "submission_id and final_status are required",
                type="InvalidPersistenceInput",
                non_retryable=True,
            )

        await self.submission_repository.mark_submission_terminal(
            submission_id=str(submission_id),
            final_status=str(final_status),
            error_code=str(input["error_code"])
            if input.get("error_code") is not None
            else None,
            error_message=str(input["error_message"])
            if input.get("error_message") is not None
            else None,
        )

    @activity.defn(name="load_pending_submissions_for_reconciliation")
    async def load_pending_submissions_for_reconciliation(
        self, input: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return await self.submission_repository.load_pending_submissions_for_reconciliation(
            company_id=input.get("company_id"),
            environment=str(input["environment"]),
            limit=int(input.get("limit", 100)),
        )

    @activity.defn(name="mark_submission_reconciled")
    async def mark_submission_reconciled(self, input: dict[str, Any]) -> None:
        await self.submission_repository.mark_submission_reconciled(
            submission_id=str(input["submission_id"]),
            final_status=str(input["final_status"]),
        )
