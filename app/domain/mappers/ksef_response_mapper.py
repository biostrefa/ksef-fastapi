"""
KSeF response mapping.

This module provides:
- KSeF API response mapping
- Response to domain model mapping
- Error response mapping
- Status response mapping

Classes:
    KsefResponseMapper: KSeF response mapper

Methods:
    map_auth_tokens(payload: dict) -> AuthTokens: Map authentication tokens from KSeF response
    map_session_open_response(payload: dict) -> KsefSession: Map session opening response to domain model
    map_session_status_response(payload: dict) -> SessionStatusSnapshot: Map session status response
    map_invoice_send_response(payload: dict) -> InvoiceSubmission: Map invoice send response
    map_invoice_status_response(payload: dict) -> InvoiceSubmission: Map invoice status response
    map_upo_response(payload: dict) -> str: Map UPO response to string
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.constants import (
    InvoiceSubmissionStatus,
    KsefAuthMode,
    KsefEnvironment,
    KsefSessionStatus,
    KsefSessionType,
)
from app.domain.models.auth import AuthChallenge, AuthContext, AuthTokens
from app.domain.models.invoice import InvoiceSubmission
from app.domain.models.session import KsefSession, SessionStatusSnapshot
from app.domain.models.status import InvoiceStatusSnapshot, KsefErrorDetail


class KsefResponseMapper:
    @staticmethod
    def map_auth_challenge(
        company_id,
        environment: KsefEnvironment,
        payload: dict,
    ) -> AuthChallenge:
        return AuthChallenge(
            company_id=company_id,
            environment=environment,
            challenge=payload["challenge"],
            challenge_timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def map_auth_tokens(payload: dict) -> AuthTokens:
        return AuthTokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            access_token_expires_at=payload.get("access_token_expires_at"),
            refresh_token_expires_at=payload.get("refresh_token_expires_at"),
        )

    @staticmethod
    def map_auth_context(
        company_id, environment, auth_mode, tokens: AuthTokens | None
    ) -> AuthContext:
        return AuthContext(
            company_id=company_id,
            environment=environment,
            auth_mode=auth_mode,
            tokens=tokens,
        )

    @staticmethod
    def map_open_session(
        company_id, environment, session_type, payload: dict
    ) -> KsefSession:
        return KsefSession(
            id=uuid4(),
            company_id=company_id,
            environment=environment,
            session_type=session_type,
            reference_number=payload["reference_number"],
            status=payload.get("status", KsefSessionStatus.OPEN),
            opened_at=payload.get("opened_at"),
            closed_at=None,
            last_checked_at=None,
            last_error_code=None,
            last_error_message=None,
        )

    @staticmethod
    def map_session_status(payload: dict) -> SessionStatusSnapshot:
        return SessionStatusSnapshot(
            reference_number=payload["reference_number"],
            status=payload["status"],
            last_checked_at=payload.get("last_checked_at")
            or datetime.now(timezone.utc),
            upo_available=payload.get("upo_available", False),
            last_error_code=payload.get("last_error_code"),
            last_error_message=payload.get("last_error_message"),
        )

    @staticmethod
    def map_invoice_send_result(
        company_id,
        session_reference_number: str,
        local_invoice_number: str,
        payload: dict,
    ) -> InvoiceSubmission:
        now = datetime.now(timezone.utc)
        return InvoiceSubmission(
            submission_id=uuid4(),
            company_id=company_id,
            session_reference_number=session_reference_number,
            local_invoice_number=local_invoice_number,
            ksef_invoice_reference=payload.get("ksef_invoice_reference"),
            status=payload.get("status", InvoiceSubmissionStatus.SENT),
            xml_hash_sha256=payload.get("xml_hash_sha256"),
            upo_content=None,
            error_code=payload.get("error_code"),
            error_message=payload.get("error_message"),
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def map_invoice_status(payload: dict) -> InvoiceStatusSnapshot:
        error = None
        if payload.get("error_code") or payload.get("error_message"):
            error = KsefErrorDetail(
                code=payload.get("error_code", "unknown"),
                message=payload.get("error_message", "unknown error"),
                context=payload.get("error_context"),
            )

        return InvoiceStatusSnapshot(
            ksef_invoice_reference=payload.get("ksef_invoice_reference"),
            status=payload["status"],
            last_checked_at=payload.get("last_checked_at")
            or datetime.now(timezone.utc),
            error=error,
        )
