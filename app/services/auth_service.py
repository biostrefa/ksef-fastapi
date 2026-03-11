"""
Authentication service.

This module provides:
- Challenge generation and verification
- Token redemption and refresh
- Authentication lifecycle management
- Auth context handling

Classes:
    AuthService: Authentication service

Public Methods:
    start_challenge(company_id: str) -> AuthChallenge: Start authentication challenge
    redeem(company_id: str) -> AuthTokens: Redeem authentication tokens
    refresh(company_id: str) -> AuthTokens: Refresh authentication tokens
    get_auth_context(company_id: str) -> AuthContext: Get authentication context
    revoke(company_id: str) -> None: Revoke authentication

Private Methods:
    _select_strategy() -> AuthStrategyBase: Select appropriate authentication strategy
    _load_existing_tokens(company_id: str) -> AuthTokens | None: Load existing tokens from storage
    _save_tokens(company_id: str, tokens: AuthTokens) -> None: Save tokens to storage
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.constants import KsefAuthMode, KsefEnvironment
from app.core.exceptions import AuthenticationError
from app.domain.models.auth import AuthChallenge, AuthContext, AuthTokens
from app.schemas.auth import (
    AuthChallengeRequest,
    AuthContextResponse,
    AuthRefreshRequest,
    AuthRefreshResponse,
    AuthTokenRedeemRequest,
    AuthTokenRedeemResponse,
)


class AuthService:
    """
    Finalny serwis auth dla KSeF 2.x, spięty z:
    - TokenAuthStrategy
    - XadesAuthStrategy
    - KsefHttpClient
    - TokenRepository

    Flow:
    1. challenge
    2. init auth (token albo xades)
    3. polling statusu auth
    4. redeem access/refresh tokenów
    5. zapis lokalny
    """

    def __init__(
        self,
        *,
        settings,
        ksef_http_client,
        token_repository,
        token_auth_strategy=None,
        xades_strategy=None,
    ) -> None:
        self.settings = settings
        self.ksef_http_client = ksef_http_client
        self.token_repository = token_repository
        self.token_auth_strategy = token_auth_strategy
        self.xades_strategy = xades_strategy

    async def start_challenge(self, request: AuthChallengeRequest) -> AuthChallenge:
        payload = await self.ksef_http_client.get_challenge()

        return AuthChallenge(
            company_id=request.company_id,
            environment=request.environment,
            challenge=payload["challenge"],
            challenge_timestamp=payload["timestamp"],
        )

    async def redeem(self, request: AuthTokenRedeemRequest) -> AuthTokenRedeemResponse:
        """
        Główna metoda logowania:
        - inicjalizuje auth
        - czeka na sukces
        - redeemuje tokeny
        - zapisuje je lokalnie
        """
        if request.auth_mode == KsefAuthMode.TOKEN:
            init_result = await self._initialize_token_auth(
                company_id=request.company_id,
                environment=request.environment,
            )
        elif request.auth_mode == KsefAuthMode.XADES:
            init_result = await self._initialize_xades_auth(
                company_id=request.company_id,
                environment=request.environment,
            )
        else:
            raise AuthenticationError(
                "Unsupported auth mode",
                details={"auth_mode": str(request.auth_mode)},
            )

        await self._wait_for_authentication_success(
            reference_number=init_result["reference_number"],
            authentication_token=init_result["authentication_token"],
        )

        token_payload = await self.ksef_http_client.redeem_token(
            authentication_token=init_result["authentication_token"],
        )

        tokens = AuthTokens(
            access_token=token_payload["access_token"],
            refresh_token=token_payload.get("refresh_token"),
            access_token_expires_at=token_payload.get("access_token_expires_at"),
            refresh_token_expires_at=token_payload.get("refresh_token_expires_at"),
        )

        await self.token_repository.save(
            company_id=request.company_id,
            environment=request.environment,
            tokens=tokens,
        )

        return AuthTokenRedeemResponse(
            company_id=request.company_id,
            environment=request.environment,
            auth_mode=request.auth_mode,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            access_token_expires_at=tokens.access_token_expires_at,
            refresh_token_expires_at=tokens.refresh_token_expires_at,
        )

    async def refresh(self, request: AuthRefreshRequest) -> AuthRefreshResponse:
        stored = await self.token_repository.get_by_company(
            company_id=request.company_id,
            environment=request.environment,
        )

        refresh_token = request.refresh_token or (
            stored.refresh_token if stored else None
        )
        if not refresh_token:
            raise AuthenticationError("Refresh token is missing")

        token_payload = await self.ksef_http_client.refresh_token(
            refresh_token=refresh_token,
        )

        tokens = AuthTokens(
            access_token=token_payload["access_token"],
            refresh_token=token_payload.get("refresh_token") or refresh_token,
            access_token_expires_at=token_payload.get("access_token_expires_at"),
            refresh_token_expires_at=token_payload.get("refresh_token_expires_at")
            or (stored.refresh_token_expires_at if stored else None),
        )

        await self.token_repository.save(
            company_id=request.company_id,
            environment=request.environment,
            tokens=tokens,
        )

        return AuthRefreshResponse(
            company_id=request.company_id,
            environment=request.environment,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            access_token_expires_at=tokens.access_token_expires_at,
            refresh_token_expires_at=tokens.refresh_token_expires_at,
        )

    async def get_auth_context(
        self,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> AuthContextResponse:
        tokens = await self.token_repository.get_by_company(
            company_id=company_id,
            environment=environment,
        )

        context = AuthContext(
            company_id=company_id,
            environment=environment,
            auth_mode=self.settings.ksef_auth_mode,
            tokens=tokens,
        )

        return AuthContextResponse(
            company_id=context.company_id,
            environment=context.environment,
            auth_mode=context.auth_mode,
            has_active_access_token=bool(
                context.tokens and context.tokens.access_token
            ),
            has_refresh_token=bool(context.tokens and context.tokens.refresh_token),
            access_token_expires_at=context.tokens.access_token_expires_at
            if context.tokens
            else None,
            refresh_token_expires_at=context.tokens.refresh_token_expires_at
            if context.tokens
            else None,
        )

    async def revoke(self, company_id: UUID, environment: KsefEnvironment) -> None:
        stored = await self.token_repository.get_by_company(
            company_id=company_id,
            environment=environment,
        )

        if stored:
            token = stored.refresh_token or stored.access_token
            if token:
                await self.ksef_http_client.revoke_current_auth(
                    access_or_refresh_token=token,
                )

        await self.token_repository.delete_by_company(
            company_id=company_id,
            environment=environment,
        )

    async def get_valid_access_token(
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

    async def _initialize_token_auth(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> dict:
        if not self.token_auth_strategy:
            raise AuthenticationError("Token auth strategy is not configured")

        if not self.settings.ksef_context_identifier_value:
            raise AuthenticationError(
                "Missing ksef_context_identifier_value in configuration"
            )

        challenge_payload = await self.ksef_http_client.get_challenge()

        init_payload = self.token_auth_strategy.build_auth_init_payload(
            challenge=challenge_payload["challenge"],
            challenge_timestamp_ms=challenge_payload["timestamp_ms"],
            context_identifier_type=self.settings.ksef_context_identifier_type,
            context_identifier_value=self.settings.ksef_context_identifier_value,
        )

        return await self.ksef_http_client.init_auth_ksef_token(init_payload)

    async def _initialize_xades_auth(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> dict:
        if not self.xades_strategy:
            raise AuthenticationError("XAdES auth strategy is not configured")

        if not self.settings.ksef_context_identifier_value:
            raise AuthenticationError(
                "Missing ksef_context_identifier_value in configuration"
            )

        challenge_payload = await self.ksef_http_client.get_challenge()

        payload = self.xades_strategy.build_auth_init_payload(
            challenge=challenge_payload["challenge"],
            context_identifier_type=self.settings.ksef_context_identifier_type,
            context_identifier_value=self.settings.ksef_context_identifier_value,
        )

        return await self.ksef_http_client.init_auth_xades_signature(
            signed_xml=payload["signed_xml"],
        )

    async def _wait_for_authentication_success(
        self,
        *,
        reference_number: str,
        authentication_token: str,
    ) -> None:
        attempts = self.settings.ksef_auth_poll_attempts
        delay = self.settings.ksef_auth_poll_interval_seconds

        last_status: dict | None = None

        for _ in range(attempts):
            last_status = await self.ksef_http_client.get_auth_status(
                reference_number=reference_number,
                authentication_token=authentication_token,
            )

            status_code = last_status.get("status_code")

            if status_code == 200:
                return

            if status_code == 100:
                await asyncio.sleep(delay)
                continue

            raise AuthenticationError(
                "Authentication failed",
                details={
                    "reference_number": reference_number,
                    "status": last_status,
                },
            )

        raise AuthenticationError(
            "Authentication polling timed out",
            details={
                "reference_number": reference_number,
                "last_status": last_status,
            },
        )
