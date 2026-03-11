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
    open_online_session(company_id: str) -> KsefSession: Open online session
    open_batch_session(company_id: str) -> KsefSession: Open batch session
    close_session(reference_number: str) -> KsefSession: Close session by reference number
    get_session(reference_number: str) -> KsefSession: Get session by reference number
    list_sessions(company_id: str) -> list[KsefSession]: List all sessions for company

Private Methods:
    _get_valid_access_token(company_id: str) -> str: Get valid access token for company
    _persist_opened_session(session: KsefSession) -> None: Persist opened session to storage
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.constants import KsefEnvironment, KsefSessionStatus, KsefSessionType
from app.core.exceptions import AuthenticationError, SessionNotFoundError
from app.domain.models.session import KsefSession
from app.schemas.sessions import (
    CloseSessionResponse,
    OpenBatchSessionRequest,
    OpenOnlineSessionRequest,
    OpenSessionResponse,
    SessionResponse,
)


class SessionService:
    """
    Finalny serwis sesji KSeF 2.x.

    Odpowiedzialność:
    - otwarcie sesji online
    - otwarcie sesji batch
    - zamknięcie sesji
    - odczyt sesji lokalnie
    - lista sesji lokalnie

    Uwaga:
    finalny kształt payloadu open_online_session / open_batch_session
    trzeba dopiąć 1:1 do OpenAPI KSeF. Serwis ma już przygotowane helpery
    pod ten cel.
    """

    def __init__(
        self,
        *,
        settings,
        ksef_http_client,
        token_repository,
        session_repository,
    ) -> None:
        self.settings = settings
        self.ksef_http_client = ksef_http_client
        self.token_repository = token_repository
        self.session_repository = session_repository

    async def open_online_session(
        self, request: OpenOnlineSessionRequest
    ) -> OpenSessionResponse:
        if request.reuse_open_session:
            existing = await self.session_repository.get_open_session_for_company(
                company_id=request.company_id,
                environment=request.environment,
                session_type=KsefSessionType.ONLINE,
            )
            if existing:
                return self._to_open_session_response(existing)

        access_token = await self._get_valid_access_token(
            company_id=request.company_id,
            environment=request.environment,
        )

        payload = self._build_online_session_payload(request)
        raw = await self.ksef_http_client.open_online_session(
            access_token=access_token,
            payload=payload,
        )

        now = datetime.now(timezone.utc)
        session = KsefSession(
            id=uuid4(),
            company_id=request.company_id,
            environment=request.environment,
            session_type=KsefSessionType.ONLINE,
            reference_number=raw["reference_number"],
            status=KsefSessionStatus.OPEN,
            opened_at=now,
            closed_at=None,
            last_checked_at=now,
            upo_reference_number=None,
            last_error_code=None,
            last_error_message=None,
        )

        saved = await self.session_repository.save(session)
        return self._to_open_session_response(saved)

    async def open_batch_session(
        self, request: OpenBatchSessionRequest
    ) -> OpenSessionResponse:
        access_token = await self._get_valid_access_token(
            company_id=request.company_id,
            environment=request.environment,
        )

        payload = self._build_batch_session_payload(request)
        raw = await self.ksef_http_client.open_batch_session(
            access_token=access_token,
            payload=payload,
        )

        now = datetime.now(timezone.utc)
        session = KsefSession(
            id=uuid4(),
            company_id=request.company_id,
            environment=request.environment,
            session_type=KsefSessionType.BATCH,
            reference_number=raw["reference_number"],
            status=KsefSessionStatus.OPEN,
            opened_at=now,
            closed_at=None,
            last_checked_at=now,
            upo_reference_number=None,
            last_error_code=None,
            last_error_message=None,
        )

        saved = await self.session_repository.save(session)
        return self._to_open_session_response(saved)

    async def close_session(self, reference_number: str) -> CloseSessionResponse:
        session = await self.session_repository.get_by_reference(reference_number)
        if not session:
            raise SessionNotFoundError(f"Session not found: {reference_number}")

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
            raise SessionNotFoundError(
                f"Unsupported session type for closing: {session.session_type}"
            )

        closed_at = datetime.now(timezone.utc)
        updated = await self.session_repository.close(
            reference_number=reference_number,
            status=KsefSessionStatus.CLOSED,
            closed_at=closed_at,
        )

        return CloseSessionResponse(
            reference_number=updated.reference_number,
            status=updated.status,
            closed_at=updated.closed_at,
        )

    async def get_session(self, reference_number: str) -> SessionResponse:
        session = await self.session_repository.get_by_reference(reference_number)
        if not session:
            raise SessionNotFoundError(f"Session not found: {reference_number}")
        return self._to_session_response(session)

    async def list_sessions(
        self,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> list[SessionResponse]:
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
        encryption: dict | None = None,
    ) -> KsefSession:
        existing = await self.session_repository.get_open_session_for_company(
            company_id=company_id,
            environment=environment,
            session_type=KsefSessionType.ONLINE,
        )
        if existing:
            return existing

        response = await self.open_online_session(
            OpenOnlineSessionRequest(
                company_id=company_id,
                environment=environment,
                reuse_open_session=True,
                encryption=encryption,  # jeśli tu przekażesz dict, trzeba wcześniej dopasować schemat
            )
        )
        created = await self.session_repository.get_by_reference(
            response.reference_number
        )
        if not created:
            raise SessionNotFoundError(
                f"Session created remotely but not found locally: {response.reference_number}"
            )
        return created

    async def _get_valid_access_token(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> str:
        tokens = await self.token_repository.get_by_company(
            company_id=company_id,
            environment=environment,
        )
        if not tokens or not tokens.access_token:
            raise AuthenticationError("No active access token for company/environment")
        return tokens.access_token

    def _build_online_session_payload(self, request: OpenOnlineSessionRequest) -> dict:
        """
        Payload otwarcia sesji online.

        Tu jest miejsce na finalne dopięcie requestu 1:1 do OpenAPI KSeF.
        Obecnie budujemy minimalny, czytelny payload konfigurowalny z settings.
        """
        form_code = {
            "systemCode": getattr(
                self.settings, "ksef_form_code_system_code", "FA (3)"
            ),
            "schemaVersion": getattr(
                self.settings, "ksef_form_code_schema_version", "1-0E"
            ),
            "value": getattr(self.settings, "ksef_form_code_value", "FA"),
        }

        payload: dict = {
            "formCode": form_code,
        }

        if request.encryption is not None:
            payload["encryption"] = request.encryption.model_dump(exclude_none=True)

        return payload

    def _build_batch_session_payload(self, request: OpenBatchSessionRequest) -> dict:
        """
        Payload otwarcia sesji batch.

        Tak samo jak wyżej: to miejsce na finalne dopasowanie do OpenAPI.
        """
        form_code = {
            "systemCode": getattr(
                self.settings, "ksef_form_code_system_code", "FA (3)"
            ),
            "schemaVersion": getattr(
                self.settings, "ksef_form_code_schema_version", "1-0E"
            ),
            "value": getattr(self.settings, "ksef_form_code_value", "FA"),
        }

        payload: dict = {
            "formCode": form_code,
        }

        if request.package_name:
            payload["batchFileName"] = request.package_name

        if request.encryption is not None:
            payload["encryption"] = request.encryption.model_dump(exclude_none=True)

        return payload

    @staticmethod
    def _to_open_session_response(session: KsefSession) -> OpenSessionResponse:
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
