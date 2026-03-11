"""
Session management service.

This module provides:
- Session opening and closing
- Reference number management
- Session lifecycle handling
- Session state tracking

Classes:
    SessionService: Session management service

Public Methods:
    open_online_session(request: OpenOnlineSessionRequest) -> OpenSessionResponse:
        Open online session
    open_batch_session(request: OpenBatchSessionRequest) -> OpenSessionResponse:
        Open batch session
    close_session(reference_number: str) -> CloseSessionResponse:
        Close session by reference number
    get_session(reference_number: str) -> SessionResponse:
        Get session by reference number
    list_sessions(company_id: UUID, environment: KsefEnvironment) -> list[SessionResponse]:
        List all sessions for company/environment
    get_or_open_online_session(...) -> KsefSession:
        Reuse open online session or open a new one

Private Methods:
    _get_valid_access_token(company_id: UUID, environment: KsefEnvironment) -> str:
        Get valid access token for company/environment
    _persist_opened_session(...) -> KsefSession:
        Persist opened session to storage

Assumes your session_repository can eventually persist valid_until, session_encryption_context_json,
and remote_response_json. The service already degrades gracefully to a plain save(session) call,
but the full KSeF 2.x flow only becomes complete once the repository/model layer
stores that extra session metadata.

"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.core.constants import KsefEnvironment, KsefSessionStatus, KsefSessionType
from app.core.exceptions import (
    AuthenticationError,
    SessionNotFoundError,
    ValidationError,
)
from app.core.logging import get_bound_logger, log_timed_operation
from app.domain.models.session import KsefSession
from app.infrastructure.persistence.models.audit_log_model import (
    AuditEventOutcome,
    AuditEventSeverity,
)
from app.schemas.sessions import (
    CloseSessionResponse,
    CreateBatchSessionRequest,
    CreateOnlineSessionRequest,
    OpenSessionResponse,
    SessionResponse,
)
from app.utils.datetime_utils import from_iso, is_expired, utc_now


class SessionService:
    """
    KSeF 2.x session management service.

    Responsibilities:
    - open online session
    - open batch session
    - close session
    - fetch locally persisted session
    - list locally persisted sessions
    - own online-session encryption material generation and persistence

    Important:
    For online and batch sessions this service generates the KSeF encryption
    material itself via EncryptionService and persists the local protected
    session encryption context, so the same session can later be used by
    InvoiceService.
    """

    def __init__(
        self,
        *,
        settings: Any,
        ksef_http_client: Any,
        token_repository: Any,
        session_repository: Any,
        encryption_service: Any,
        audit_service: Any,
    ) -> None:
        self.settings = settings
        self.ksef_http_client = ksef_http_client
        self.token_repository = token_repository
        self.session_repository = session_repository
        self.encryption_service = encryption_service
        self.audit_service = audit_service

        self.logger = get_bound_logger(__name__, component="session_service")

    async def create_online_session(
        self,
        request: CreateOnlineSessionRequest,
    ) -> OpenSessionResponse:
        """
        Backward-compatible alias.
        """
        return await self.open_online_session(request)

    async def create_batch_session(
        self,
        request: CreateBatchSessionRequest,
    ) -> OpenSessionResponse:
        """
        Backward-compatible alias.
        """
        return await self.open_batch_session(request)

    async def open_online_session(
        self,
        request: CreateOnlineSessionRequest,
    ) -> OpenSessionResponse:
        """
        Open KSeF online session.

        The service generates the session encryption material locally,
        sends only the API-facing encryption object to KSeF, and persists
        the protected local session encryption context.
        """
        with log_timed_operation(
            self.logger,
            "open_online_session",
            company_id=str(request.company_id),
            environment=str(request.environment),
        ):
            if request.reuse_open_session:
                existing = await self.session_repository.get_open_session_for_company(
                    company_id=request.company_id,
                    environment=request.environment,
                    session_type=KsefSessionType.ONLINE,
                )
                if existing:
                    return self._to_open_session_response(existing)

            if getattr(request, "encryption", None) is not None:
                raise ValidationError(
                    message=(
                        "External encryption override is not supported. "
                        "SessionService must generate and persist session encryption material."
                    ),
                    details={"field": "encryption"},
                )

            access_token = await self._get_valid_access_token(
                company_id=request.company_id,
                environment=request.environment,
            )

            session_material = self.encryption_service.create_session_encryption_material()
            payload = self._build_online_session_payload(
                request=request,
                session_material=session_material,
            )

            raw_response = await self.ksef_http_client.open_online_session(
                access_token=access_token,
                payload=payload,
            )

            reference_number = self._extract_reference_number(raw_response)
            valid_until = self._extract_valid_until(raw_response)

            session = KsefSession(
                id=uuid4(),
                company_id=request.company_id,
                environment=request.environment,
                session_type=KsefSessionType.ONLINE,
                reference_number=reference_number,
                status=KsefSessionStatus.OPEN,
                opened_at=utc_now(),
                closed_at=None,
                last_checked_at=utc_now(),
                upo_reference_number=None,
                last_error_code=None,
                last_error_message=None,
            )

            saved = await self._persist_opened_session(
                session=session,
                valid_until=valid_until,
                session_encryption_context=self.encryption_service.export_session_material(session_material),
                remote_response_json=self._model_dump(raw_response),
            )

            await self.audit_service.log_session_event(
                event_name="online_session_opened",
                message="KSeF online session opened successfully.",
                outcome=AuditEventOutcome.SUCCESS,
                severity=AuditEventSeverity.INFO,
                tenant_id=str(request.company_id),
                session_reference_number=reference_number,
                context={
                    "environment": str(request.environment),
                    "valid_until": valid_until.isoformat() if valid_until else None,
                },
            )

            return self._to_open_session_response(saved)

    async def open_batch_session(
        self,
        request: CreateBatchSessionRequest,
    ) -> OpenSessionResponse:
        """
        Open KSeF batch session.

        Batch session requires a batchFile object in addition to formCode and encryption.
        """
        with log_timed_operation(
            self.logger,
            "open_batch_session",
            company_id=str(request.company_id),
            environment=str(request.environment),
        ):
            if getattr(request, "encryption", None) is not None:
                raise ValidationError(
                    message=(
                        "External encryption override is not supported. "
                        "SessionService must generate and persist session encryption material."
                    ),
                    details={"field": "encryption"},
                )

            access_token = await self._get_valid_access_token(
                company_id=request.company_id,
                environment=request.environment,
            )

            session_material = self.encryption_service.create_session_encryption_material()
            payload = self._build_batch_session_payload(
                request=request,
                session_material=session_material,
            )

            raw_response = await self.ksef_http_client.open_batch_session(
                access_token=access_token,
                payload=payload,
            )

            reference_number = self._extract_reference_number(raw_response)
            valid_until = self._extract_valid_until(raw_response)

            session = KsefSession(
                id=uuid4(),
                company_id=request.company_id,
                environment=request.environment,
                session_type=KsefSessionType.BATCH,
                reference_number=reference_number,
                status=KsefSessionStatus.OPEN,
                opened_at=utc_now(),
                closed_at=None,
                last_checked_at=utc_now(),
                upo_reference_number=None,
                last_error_code=None,
                last_error_message=None,
            )

            saved = await self._persist_opened_session(
                session=session,
                valid_until=valid_until,
                session_encryption_context=self.encryption_service.export_session_material(session_material),
                remote_response_json=self._model_dump(raw_response),
            )

            await self.audit_service.log_session_event(
                event_name="batch_session_opened",
                message="KSeF batch session opened successfully.",
                outcome=AuditEventOutcome.SUCCESS,
                severity=AuditEventSeverity.INFO,
                tenant_id=str(request.company_id),
                session_reference_number=reference_number,
                context={
                    "environment": str(request.environment),
                    "valid_until": valid_until.isoformat() if valid_until else None,
                },
            )

            return self._to_open_session_response(saved)

    async def close_session(self, reference_number: str) -> CloseSessionResponse:
        """
        Close KSeF session by reference number.

        The transport call itself is expected to return 204 No Content.
        """
        with log_timed_operation(
            self.logger,
            "close_session",
            reference_number=reference_number,
        ):
            session = await self.session_repository.get_by_reference(reference_number)
            if not session:
                raise SessionNotFoundError(
                    message="Session not found.",
                    details={"reference_number": reference_number},
                )

            access_token = await self._get_valid_access_token(
                company_id=session.company_id,
                environment=session.environment,
            )

            if session.session_type == KsefSessionType.ONLINE:
                await self.ksef_http_client.close_online_session(
                    access_token=access_token,
                    reference_number=reference_number,
                )
            elif session.session_type == KsefSessionType.BATCH:
                await self.ksef_http_client.close_batch_session(
                    access_token=access_token,
                    reference_number=reference_number,
                )
            else:
                raise ValidationError(
                    message="Unsupported session type for closing.",
                    details={"session_type": str(session.session_type)},
                )

            closed_at = utc_now()
            updated = await self.session_repository.close(
                reference_number=reference_number,
                status=KsefSessionStatus.CLOSED,
                closed_at=closed_at,
            )

            await self.audit_service.log_session_event(
                event_name="session_closed",
                message="KSeF session closed successfully.",
                outcome=AuditEventOutcome.SUCCESS,
                severity=AuditEventSeverity.INFO,
                tenant_id=str(session.company_id),
                session_reference_number=reference_number,
            )

            return CloseSessionResponse(
                reference_number=updated.reference_number,
                status=updated.status,
                closed_at=updated.closed_at,
            )

    async def get_session(self, reference_number: str) -> SessionResponse:
        """
        Get locally persisted session by reference number.
        """
        session = await self.session_repository.get_by_reference(reference_number)
        if not session:
            raise SessionNotFoundError(
                message="Session not found.",
                details={"reference_number": reference_number},
            )
        return self._to_session_response(session)

    async def list_sessions(
        self,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> list[SessionResponse]:
        """
        List locally persisted sessions for company/environment.
        """
        sessions = await self.session_repository.list_by_company(
            company_id=company_id,
            environment=environment,
        )
        return [self._to_session_response(item) for item in sessions]

    async def get_or_open_online_session(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> KsefSession:
        """
        Reuse currently open online session or create a new one.
        """
        existing = await self.session_repository.get_open_session_for_company(
            company_id=company_id,
            environment=environment,
            session_type=KsefSessionType.ONLINE,
        )
        if existing:
            return existing

        response = await self.open_online_session(
            CreateOnlineSessionRequest(
                company_id=company_id,
                environment=environment,
                reuse_open_session=True,
                encryption=None,
            ),
        )

        created = await self.session_repository.get_by_reference(response.reference_number)
        if not created:
            raise SessionNotFoundError(
                message="Session created remotely but not found locally.",
                details={"reference_number": response.reference_number},
            )
        return created

    async def _get_valid_access_token(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> str:
        """
        Load valid access token for company/environment.

        This method validates local presence and expiry only.
        Token refresh should be handled by AuthService.
        """
        tokens = await self.token_repository.get_by_company(
            company_id=company_id,
            environment=environment,
        )

        if not tokens:
            raise AuthenticationError(
                message="No auth context found for company/environment.",
                details={
                    "company_id": str(company_id),
                    "environment": str(environment),
                },
            )

        access_token = getattr(tokens, "access_token", None)
        if not access_token:
            raise AuthenticationError(
                message="No active access token for company/environment.",
                details={
                    "company_id": str(company_id),
                    "environment": str(environment),
                },
            )

        valid_until = (
            getattr(tokens, "access_token_valid_until", None)
            or getattr(tokens, "valid_until", None)
            or getattr(tokens, "expires_at", None)
        )
        if isinstance(valid_until, str):
            valid_until = from_iso(valid_until)

        if isinstance(valid_until, datetime) and is_expired(valid_until):
            raise AuthenticationError(
                message="Stored KSeF access token is expired.",
                details={
                    "company_id": str(company_id),
                    "environment": str(environment),
                    "valid_until": valid_until.isoformat(),
                },
            )

        return access_token

    def _build_online_session_payload(
        self,
        *,
        request: CreateOnlineSessionRequest,
        session_material: Any,
    ) -> dict[str, Any]:
        """
        Build CreateOnlineSessionRequest payload for KSeF.
        """
        payload: dict[str, Any] = {
            "formCode": self._build_form_code(),
            "encryption": session_material.to_open_session_encryption_dict(),
        }

        if hasattr(request, "offline_mode") and request.offline_mode is not None:
            payload["offlineMode"] = request.offline_mode

        return payload

    def _build_batch_session_payload(
        self,
        *,
        request: CreateBatchSessionRequest,
        session_material: Any,
    ) -> dict[str, Any]:
        """
        Build CreateBatchSessionRequest payload for KSeF.
        """
        batch_file = getattr(request, "batch_file", None)
        if batch_file is None:
            raise ValidationError(
                message="Batch session requires batch_file metadata.",
                details={"field": "batch_file"},
            )

        payload: dict[str, Any] = {
            "formCode": self._build_form_code(),
            "batchFile": self._model_dump(batch_file),
            "encryption": session_material.to_open_session_encryption_dict(),
        }

        if hasattr(request, "offline_mode") and request.offline_mode is not None:
            payload["offlineMode"] = request.offline_mode

        return payload

    def _build_form_code(self) -> dict[str, str]:
        """
        Build KSeF formCode from settings.
        """
        return {
            "systemCode": getattr(self.settings, "ksef_form_code_system_code", "FA (3)"),
            "schemaVersion": getattr(
                self.settings,
                "ksef_form_code_schema_version",
                "1-0E",
            ),
            "value": getattr(self.settings, "ksef_form_code_value", "FA"),
        }

    async def _persist_opened_session(
        self,
        *,
        session: KsefSession,
        valid_until: datetime | None,
        session_encryption_context: dict[str, Any] | None,
        remote_response_json: dict[str, Any],
    ) -> KsefSession:
        """
        Persist opened session together with remote metadata and protected
        local encryption context, if repository supports it.
        """
        if hasattr(self.session_repository, "save_opened_session"):
            return await self.session_repository.save_opened_session(
                session=session,
                valid_until=valid_until,
                session_encryption_context_json=session_encryption_context,
                remote_response_json=remote_response_json,
            )

        # Backward-compatible fallback
        return await self.session_repository.save(session)

    @staticmethod
    def _extract_reference_number(raw_response: Any) -> str:
        """
        Extract referenceNumber from KSeF response.
        """
        data = SessionService._model_dump(raw_response)
        reference_number = data.get("referenceNumber") or data.get("reference_number")
        if not reference_number:
            raise ValidationError(
                message="KSeF response does not contain reference number.",
                details={"response": data},
            )
        return str(reference_number)

    @staticmethod
    def _extract_valid_until(raw_response: Any) -> datetime | None:
        """
        Extract validUntil from KSeF response if present.
        """
        data = SessionService._model_dump(raw_response)
        raw_value = data.get("validUntil") or data.get("valid_until")
        if raw_value is None:
            return None
        if isinstance(raw_value, datetime):
            return raw_value
        return from_iso(str(raw_value))

    @staticmethod
    def _to_open_session_response(session: KsefSession) -> OpenSessionResponse:
        """
        Map domain session to OpenSessionResponse.
        """
        return OpenSessionResponse(
            company_id=session.company_id,
            environment=session.environment,
            session_type=session.session_type,
            reference_number=session.reference_number,
            status=session.status,
            opened_at=session.opened_at,
        )

    @staticmethod
    def _to_session_response(session: KsefSession) -> SessionResponse:
        """
        Map domain session to SessionResponse.
        """
        return SessionResponse(
            id=session.id,
            company_id=session.company_id,
            environment=session.environment,
            session_type=session.session_type,
            reference_number=session.reference_number,
            status=session.status,
            opened_at=session.opened_at,
            closed_at=session.closed_at,
            last_checked_at=session.last_checked_at,
            last_error_code=session.last_error_code,
            last_error_message=session.last_error_message,
        )

    @staticmethod
    def _model_dump(value: Any) -> dict[str, Any]:
        """
        Convert Pydantic model or dict-like value into plain dict.
        """
        if value is None:
            return {}

        if isinstance(value, dict):
            return value

        if isinstance(value, BaseModel):
            return value.model_dump(mode="json", exclude_none=True)

        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json", exclude_none=True)

        if hasattr(value, "dict"):
            return value.dict(exclude_none=True)

        if hasattr(value, "__dict__"):
            return {key: val for key, val in vars(value).items() if not key.startswith("_")}

        raise ValidationError(
            message="Unsupported object type for serialization.",
            details={"type": type(value).__name__},
        )
