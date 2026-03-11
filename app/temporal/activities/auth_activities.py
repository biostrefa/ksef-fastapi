"""
Authentication-related activities.

This module provides:
- Challenge generation activities
- Token redemption activities
- Authentication validation activities
- Token refresh activities
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, runtime_checkable

from temporalio import activity
from temporalio.exceptions import ApplicationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@runtime_checkable
class AuthContextRepositoryProtocol(Protocol):
    async def get_current_auth_context(
        self,
        *,
        company_id: str,
        environment: str,
    ) -> dict[str, Any] | None: ...

    async def create_or_replace_auth_context(self, payload: dict[str, Any]) -> str: ...

    async def update_auth_context_tokens(
        self,
        *,
        auth_context_id: str,
        access_token: str,
        access_token_valid_until: str | None,
        refresh_token: str | None = None,
        refresh_token_valid_until: str | None = None,
    ) -> None: ...

    async def get_auth_context_by_id(
        self, auth_context_id: str
    ) -> dict[str, Any] | None: ...


@runtime_checkable
class CredentialProviderProtocol(Protocol):
    async def get_token_auth_material(
        self,
        *,
        company_id: str,
        environment: str,
    ) -> dict[str, Any]: ...

    async def get_xades_auth_material(
        self,
        *,
        company_id: str,
        environment: str,
    ) -> dict[str, Any]: ...


@runtime_checkable
class TokenEncryptionServiceProtocol(Protocol):
    async def encrypt_ksef_token_with_challenge(
        self,
        *,
        ksef_token: str,
        challenge_timestamp_ms: int,
    ) -> str: ...


@runtime_checkable
class KsefHttpClientProtocol(Protocol):
    async def get_auth_challenge(self) -> dict[str, Any]: ...

    async def init_ksef_token_auth(
        self, *, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def init_xades_auth(
        self,
        *,
        signed_xml: str,
        verify_certificate_chain: bool | None = None,
    ) -> dict[str, Any]: ...

    async def get_auth_status(
        self,
        *,
        authentication_token: str,
        reference_number: str,
    ) -> dict[str, Any]: ...

    async def redeem_access_tokens(
        self, *, authentication_token: str
    ) -> dict[str, Any]: ...

    async def refresh_access_token(self, *, refresh_token: str) -> dict[str, Any]: ...


class AuthActivities:
    REFRESH_SAFETY_WINDOW = timedelta(seconds=90)
    POLL_INTERVAL_SECONDS = 3
    MAX_STATUS_POLLS = 40

    def __init__(
        self,
        *,
        auth_context_repository: AuthContextRepositoryProtocol,
        credential_provider: CredentialProviderProtocol,
        token_encryption_service: TokenEncryptionServiceProtocol,
        ksef_http_client: KsefHttpClientProtocol,
    ) -> None:
        self.auth_context_repository = auth_context_repository
        self.credential_provider = credential_provider
        self.token_encryption_service = token_encryption_service
        self.ksef_http_client = ksef_http_client

    @activity.defn(name="ensure_auth_context")
    async def ensure_auth_context(self, input: dict[str, Any]) -> dict[str, Any]:
        company_id = str(input["company_id"])
        environment = str(input["environment"])
        auth_mode = str(input.get("auth_mode", "token")).lower()

        current = await self.auth_context_repository.get_current_auth_context(
            company_id=company_id,
            environment=environment,
        )

        if current and self._has_valid_access_token(current):
            return self._to_workflow_result(current)

        if current and self._can_refresh(current):
            refreshed = await self.ksef_http_client.refresh_access_token(
                refresh_token=str(current["refresh_token"])
            )
            access_token_obj = refreshed.get("accessToken") or {}
            access_token = str(access_token_obj["token"])
            access_token_valid_until = access_token_obj.get("validUntil")

            await self.auth_context_repository.update_auth_context_tokens(
                auth_context_id=str(current["id"]),
                access_token=access_token,
                access_token_valid_until=access_token_valid_until,
            )

            current["access_token"] = access_token
            current["access_token_valid_until"] = access_token_valid_until
            return self._to_workflow_result(current)

        challenge = await self.ksef_http_client.get_auth_challenge()
        challenge_value = str(challenge["challenge"])
        challenge_timestamp_ms = int(challenge["timestampMs"])

        if auth_mode == "token":
            material = await self.credential_provider.get_token_auth_material(
                company_id=company_id,
                environment=environment,
            )
            encrypted_token = (
                await self.token_encryption_service.encrypt_ksef_token_with_challenge(
                    ksef_token=str(material["ksef_token"]),
                    challenge_timestamp_ms=challenge_timestamp_ms,
                )
            )
            init_result = await self.ksef_http_client.init_ksef_token_auth(
                payload={
                    "challenge": challenge_value,
                    "contextIdentifier": material["context_identifier"],
                    "encryptedToken": encrypted_token,
                }
            )
            passthrough_session_encryption = material.get("session_encryption")

        elif auth_mode == "xades":
            material = await self.credential_provider.get_xades_auth_material(
                company_id=company_id,
                environment=environment,
            )
            init_result = await self.ksef_http_client.init_xades_auth(
                signed_xml=str(material["signed_xml"]),
                verify_certificate_chain=material.get("verify_certificate_chain"),
            )
            passthrough_session_encryption = material.get("session_encryption")
        else:
            raise ApplicationError(
                f"Unsupported auth_mode={auth_mode}",
                type="UnsupportedAuthMode",
                non_retryable=True,
            )

        authentication_token = str(init_result["authenticationToken"]["token"])
        reference_number = str(init_result["referenceNumber"])

        final_auth_status = await self._wait_for_auth_terminal_status(
            authentication_token=authentication_token,
            reference_number=reference_number,
        )

        status = final_auth_status.get("status") or {}
        if status.get("code") != 200:
            raise ApplicationError(
                f"Authentication failed, status={status}",
                type="AuthenticationFailed",
                non_retryable=True,
            )

        tokens = await self.ksef_http_client.redeem_access_tokens(
            authentication_token=authentication_token
        )

        access_token_obj = tokens.get("accessToken") or {}
        refresh_token_obj = tokens.get("refreshToken") or {}

        access_token = str(access_token_obj["token"])
        refresh_token = (
            str(refresh_token_obj["token"]) if refresh_token_obj.get("token") else None
        )
        access_token_valid_until = access_token_obj.get("validUntil")
        refresh_token_valid_until = refresh_token_obj.get("validUntil")

        auth_context_id = (
            await self.auth_context_repository.create_or_replace_auth_context(
                {
                    "company_id": company_id,
                    "environment": environment,
                    "auth_mode": auth_mode,
                    "authentication_reference_number": reference_number,
                    "authentication_method": auth_mode,
                    "access_token": access_token,
                    "access_token_valid_until": access_token_valid_until,
                    "refresh_token": refresh_token,
                    "refresh_token_valid_until": refresh_token_valid_until,
                    "session_encryption": passthrough_session_encryption,
                }
            )
        )

        return {
            "auth_context_id": auth_context_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at_utc": access_token_valid_until,
            "session_encryption": passthrough_session_encryption,
        }

    @activity.defn(name="refresh_auth_context")
    async def refresh_auth_context(self, auth_context_id: str) -> dict[str, Any]:
        current = await self.auth_context_repository.get_auth_context_by_id(
            auth_context_id
        )
        if not current:
            raise ApplicationError(
                f"Auth context {auth_context_id} not found",
                type="AuthContextNotFound",
                non_retryable=True,
            )

        refresh_token = current.get("refresh_token")
        if not refresh_token:
            raise ApplicationError(
                "Refresh token missing",
                type="RefreshTokenMissing",
                non_retryable=True,
            )

        refreshed = await self.ksef_http_client.refresh_access_token(
            refresh_token=str(refresh_token)
        )

        access_token_obj = refreshed.get("accessToken") or {}
        access_token = str(access_token_obj["token"])
        access_token_valid_until = access_token_obj.get("validUntil")

        await self.auth_context_repository.update_auth_context_tokens(
            auth_context_id=auth_context_id,
            access_token=access_token,
            access_token_valid_until=access_token_valid_until,
        )

        return {
            "auth_context_id": auth_context_id,
            "access_token": access_token,
            "expires_at_utc": access_token_valid_until,
        }

    async def _wait_for_auth_terminal_status(
        self,
        *,
        authentication_token: str,
        reference_number: str,
    ) -> dict[str, Any]:
        last_status: dict[str, Any] | None = None

        for _ in range(self.MAX_STATUS_POLLS):
            last_status = await self.ksef_http_client.get_auth_status(
                authentication_token=authentication_token,
                reference_number=reference_number,
            )
            status = last_status.get("status") or {}
            code = status.get("code")

            if code != 100:
                return last_status

            await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

        raise ApplicationError(
            f"Authentication timeout, last_status={last_status}",
            type="AuthenticationTimeout",
            non_retryable=True,
        )

    def _has_valid_access_token(self, auth_context: dict[str, Any]) -> bool:
        access_token = auth_context.get("access_token")
        valid_until = _parse_dt(auth_context.get("access_token_valid_until"))
        if not access_token or not valid_until:
            return False
        return valid_until - self.REFRESH_SAFETY_WINDOW > _utc_now()

    def _can_refresh(self, auth_context: dict[str, Any]) -> bool:
        refresh_token = auth_context.get("refresh_token")
        refresh_valid_until = _parse_dt(auth_context.get("refresh_token_valid_until"))

        if not refresh_token:
            return False
        if refresh_valid_until is None:
            return True
        return refresh_valid_until > _utc_now()

    @staticmethod
    def _to_workflow_result(auth_context: dict[str, Any]) -> dict[str, Any]:
        return {
            "auth_context_id": str(auth_context["id"]),
            "access_token": str(auth_context["access_token"]),
            "refresh_token": auth_context.get("refresh_token"),
            "expires_at_utc": auth_context.get("access_token_valid_until"),
            "session_encryption": auth_context.get("session_encryption"),
        }
