"""
Status monitoring service.

This module provides:
- Session status retrieval
- Invoice status tracking
- UPO status monitoring
- Status polling logic

Classes:
    StatusService: Status monitoring service

Public Methods:
    get_session_status(reference_number: str) -> SessionStatusSnapshot: Get session status
    get_invoice_status(submission_id: str) -> InvoiceSubmission: Get invoice status
    download_session_upo(reference_number: str) -> str: Download session UPO
    download_invoice_upo(submission_id: str) -> str: Download invoice UPO
    poll_and_update_session(reference_number: str) -> SessionStatusSnapshot: Poll and update session status
    poll_and_update_invoice(submission_id: str) -> InvoiceSubmission: Poll and update invoice status

Private Methods:
    _get_access_token_for_session(reference_number: str) -> str: Get access token for session
    _update_local_session_status(snapshot: SessionStatusSnapshot) -> None: Update local session status
    _update_local_invoice_status(submission: InvoiceSubmission) -> None: Update local invoice status
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.constants import InvoiceSubmissionStatus, KsefSessionStatus
from app.core.exceptions import (
    InvoiceNotFoundError,
    KsefBusinessError,
    SessionNotFoundError,
)
from app.schemas.invoices import InvoiceStatusResponse, UpoResponse
from app.schemas.sessions import SessionStatusResponse


class StatusService:
    def __init__(
        self,
        *,
        ksef_http_client,
        token_repository,
        session_repository,
        invoice_repository,
    ) -> None:
        self.ksef_http_client = ksef_http_client
        self.token_repository = token_repository
        self.session_repository = session_repository
        self.invoice_repository = invoice_repository

    async def _get_access_token_for_company(self, company_id, environment) -> str:
        tokens = await self.token_repository.get_by_company(
            company_id=company_id,
            environment=environment,
        )
        if not tokens or not tokens.access_token:
            raise SessionNotFoundError("No valid access token found")
        return tokens.access_token

    def _map_session_status_code(self, status_code: int | None) -> KsefSessionStatus:
        if status_code == 200:
            return KsefSessionStatus.CLOSED
        if status_code == 100:
            return KsefSessionStatus.PROCESSING
        if status_code and status_code >= 400:
            return KsefSessionStatus.FAILED
        return KsefSessionStatus.PROCESSING

    def _map_invoice_status_code(
        self, status_code: int | None
    ) -> InvoiceSubmissionStatus:
        if status_code == 200:
            return InvoiceSubmissionStatus.ACCEPTED
        if status_code == 100:
            return InvoiceSubmissionStatus.PROCESSING
        if status_code and status_code >= 400:
            return InvoiceSubmissionStatus.REJECTED
        return InvoiceSubmissionStatus.PROCESSING

    async def get_session_status(self, reference_number: str) -> SessionStatusResponse:
        session = await self.session_repository.get_by_reference(reference_number)
        if not session:
            raise SessionNotFoundError(f"Session not found: {reference_number}")

        access_token = await self._get_access_token_for_company(
            session.company_id, session.environment
        )
        raw = await self.ksef_http_client.get_session_status(
            access_token=access_token,
            reference_number=reference_number,
        )

        mapped_status = self._map_session_status_code(raw.get("status_code"))
        last_checked_at = datetime.now(timezone.utc)

        await self.session_repository.update_status_snapshot(
            reference_number=reference_number,
            snapshot=type(
                "SessionSnapshot",
                (),
                {
                    "status": mapped_status,
                    "last_checked_at": last_checked_at,
                    "upo_available": raw.get("upo_available", False),
                    "upo_reference_number": raw.get("upo_reference_number"),
                    "last_error_code": str(raw.get("status_code"))
                    if raw.get("status_code") and raw.get("status_code") >= 400
                    else None,
                    "last_error_message": raw.get("status_description"),
                },
            )(),
        )

        return SessionStatusResponse(
            reference_number=reference_number,
            status=mapped_status,
            last_checked_at=last_checked_at,
            upo_available=raw.get("upo_available", False),
            upo_reference_number=raw.get("upo_reference_number"),
            last_error_code=str(raw.get("status_code"))
            if raw.get("status_code") and raw.get("status_code") >= 400
            else None,
            last_error_message=raw.get("status_description"),
        )

    async def get_invoice_status(self, submission_id) -> InvoiceStatusResponse:
        submission = await self.invoice_repository.get_by_id(submission_id)
        if not submission:
            raise InvoiceNotFoundError(f"Submission not found: {submission_id}")

        session = await self.session_repository.get_by_reference(
            submission.session_reference_number
        )
        if not session:
            raise SessionNotFoundError(
                f"Session not found for submission: {submission.session_reference_number}"
            )

        if not submission.ksef_invoice_reference:
            raise KsefBusinessError(
                "Submission does not yet have ksef_invoice_reference"
            )

        access_token = await self._get_access_token_for_company(
            session.company_id, session.environment
        )
        raw = await self.ksef_http_client.get_invoice_status(
            access_token=access_token,
            reference_number=session.reference_number,
            invoice_reference_number=submission.ksef_invoice_reference,
        )

        mapped_status = self._map_invoice_status_code(raw.get("status_code"))
        last_checked_at = datetime.now(timezone.utc)

        await self.invoice_repository.update_status(
            submission_id=submission_id,
            status=mapped_status,
            error_code=str(raw.get("status_code"))
            if raw.get("status_code") and raw.get("status_code") >= 400
            else None,
            error_message=raw.get("status_description"),
        )

        return InvoiceStatusResponse(
            submission_id=submission_id,
            ksef_invoice_reference=raw.get("reference_number")
            or submission.ksef_invoice_reference,
            status=mapped_status,
            last_checked_at=last_checked_at,
            error_code=str(raw.get("status_code"))
            if raw.get("status_code") and raw.get("status_code") >= 400
            else None,
            error_message=raw.get("status_description"),
        )

    async def download_session_upo(self, reference_number: str) -> UpoResponse:
        session = await self.session_repository.get_by_reference(reference_number)
        if not session:
            raise SessionNotFoundError(f"Session not found: {reference_number}")

        current_status = await self.get_session_status(reference_number)
        if not current_status.upo_reference_number:
            raise KsefBusinessError(
                "Session UPO is not yet available",
                details={
                    "reference_number": reference_number,
                    "status": current_status.status,
                },
            )

        access_token = await self._get_access_token_for_company(
            session.company_id, session.environment
        )
        raw = await self.ksef_http_client.download_session_upo(
            access_token=access_token,
            reference_number=reference_number,
            upo_reference_number=current_status.upo_reference_number,
        )

        return UpoResponse(
            session_reference_number=reference_number,
            upo_content=raw["upo_content"],
            content_type=raw.get("content_type", "application/xml"),
            downloaded_at=datetime.now(timezone.utc),
        )

    async def download_invoice_upo(self, submission_id) -> UpoResponse:
        submission = await self.invoice_repository.get_by_id(submission_id)
        if not submission:
            raise InvoiceNotFoundError(f"Submission not found: {submission_id}")

        session = await self.session_repository.get_by_reference(
            submission.session_reference_number
        )
        if not session:
            raise SessionNotFoundError(
                f"Session not found for submission: {submission.session_reference_number}"
            )

        if not submission.ksef_invoice_reference:
            raise KsefBusinessError(
                "Submission does not yet have ksef_invoice_reference"
            )

        access_token = await self._get_access_token_for_company(
            session.company_id, session.environment
        )
        raw = await self.ksef_http_client.download_invoice_upo(
            access_token=access_token,
            reference_number=session.reference_number,
            invoice_reference_number=submission.ksef_invoice_reference,
        )

        await self.invoice_repository.save_upo(
            submission_id=submission_id,
            upo_content=raw["upo_content"],
        )

        return UpoResponse(
            submission_id=submission_id,
            upo_content=raw["upo_content"],
            content_type=raw.get("content_type", "application/xml"),
            downloaded_at=datetime.now(timezone.utc),
        )
