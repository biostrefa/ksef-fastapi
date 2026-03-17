"""
KSeF authentication testing endpoints.

This router is focused on executable debug endpoints that use the real
AuthService methods. It exposes both:
- high-level service-driven flow checks
- low-level auth status/redeem probes for incremental debugging
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import Field

from app.api.deps import get_auth_service
from app.core.constants import KsefAuthMode, KsefEnvironment
from app.domain.strategies.xades_auth_strategy import XadesAuthStrategy
from app.schemas.auth import (
    AuthChallengeRequest,
    AuthContextResponse,
    AuthRefreshRequest,
    AuthRefreshResponse,
    AuthTokenRedeemRequest,
    AuthTokenRedeemResponse,
    RevokeAuthRequest,
)
from app.schemas.common import ApiModel
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/testing/ksef/auth",
    tags=["KSeF Auth Testing"],
)


class AuthStatusProbeRequest(ApiModel):
    reference_number: str
    authentication_token: str


class AuthTokenProbeRequest(ApiModel):
    authentication_token: str


class XadesInitRequest(ApiModel):
    challenge: str
    context_identifier_type: str = "Nip"
    context_identifier_value: str
    verify_certificate_chain: bool | None = None


class TokenInitRequest(ApiModel):
    challenge: str
    timestamp_ms: int
    ksef_token: str
    context_identifier_type: str = "Nip"
    context_identifier_value: str


class KsefTokenCreateRequest(ApiModel):
    access_token: str
    permissions: list[str] = Field(default_factory=lambda: ["InvoiceRead", "InvoiceWrite"])
    description: str = "Wystawianie i przeglądanie faktur."


class KsefTokenStatusRequest(ApiModel):
    access_token: str
    reference_number: str


class KsefTokenPollRequest(ApiModel):
    access_token: str
    reference_number: str
    attempts: int = 10
    delay_seconds: float = 1.0


class ServiceContextRequest(ApiModel):
    company_id: UUID
    environment: KsefEnvironment


class TestResult(ApiModel):
    step: str
    data: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/step1/challenge",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 1: challenge",
)
async def test_step1_challenge(
    payload: ServiceContextRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    challenge = await auth_service.start_challenge(
        AuthChallengeRequest(
            company_id=payload.company_id,
            environment=payload.environment,
        )
    )
    return TestResult(
        step="step1.challenge",
        data={
            "company_id": str(challenge.company_id),
            "environment": challenge.environment.value,
            "challenge": challenge.challenge,
            "challenge_timestamp": challenge.challenge_timestamp,
        },
    )


@router.post(
    "/step1/init/xades-signature",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 1: init auth with XAdES signature",
)
async def test_step1_init_xades_signature(
    payload: XadesInitRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    xades_strategy = auth_service.xades_strategy
    if not isinstance(xades_strategy, XadesAuthStrategy):
        raise ValueError("XAdES strategy is not configured")

    try:
        signed_xml = xades_strategy.build_signed_auth_request_xml(
            challenge=payload.challenge,
            context_identifier_type=payload.context_identifier_type,
            context_identifier_value=payload.context_identifier_value,
        )

        init_result = await auth_service.ksef_http_client.init_auth_xades_signature(
            signed_xml=signed_xml,
            verify_certificate_chain=payload.verify_certificate_chain,
        )
        return TestResult(step="step1.init_xades_signature", data=init_result)
    except Exception as e:
        return TestResult(step="step1.init_xades_signature", data={"error": str(e), "type": type(e).__name__})


@router.post(
    "/step1/status",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 1: check authentication status",
)
async def test_step1_status(
    payload: AuthStatusProbeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    try:
        result = await auth_service.ksef_http_client.get_auth_status(
            reference_number=payload.reference_number,
            authentication_token=payload.authentication_token,
        )
        return TestResult(step="step1.status", data=result)
    except Exception as e:
        return TestResult(step="step1.status", data={"error": str(e), "type": type(e).__name__})


@router.post(
    "/step1/redeem",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 1: redeem temporary auth token",
)
async def test_step1_redeem(
    payload: AuthTokenProbeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    result = await auth_service.ksef_http_client.redeem_token(authentication_token=payload.authentication_token)
    return TestResult(step="step1.redeem", data=result)


@router.post(
    "/step1/redeem/xades",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 1: full XAdES bootstrap via AuthService",
)
async def test_step1_redeem_xades(
    payload: ServiceContextRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    try:
        result = await auth_service.redeem(
            AuthTokenRedeemRequest(
                company_id=payload.company_id,
                environment=payload.environment,
                auth_mode=KsefAuthMode.XADES,
            )
        )
        return TestResult(step="step1.redeem_xades", data={"result": result.model_dump()})
    except Exception as e:
        return TestResult(step="step1.redeem_xades", data={"error": str(e), "type": type(e).__name__})


@router.post(
    "/step2/create-ksef-token",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 2: create reusable KSeF token",
)
async def test_step2_create_ksef_token(
    payload: KsefTokenCreateRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    result = await auth_service.ksef_http_client.create_ksef_token(
        access_token=payload.access_token,
        permissions=payload.permissions,
        description=payload.description,
    )
    return TestResult(step="step2.create_ksef_token", data=result)


@router.post(
    "/step3/token-status",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 3: check KSeF token status",
)
async def test_step3_token_status(
    payload: KsefTokenStatusRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    result = await auth_service.ksef_http_client.get_ksef_token_status(
        access_token=payload.access_token,
        reference_number=payload.reference_number,
    )
    return TestResult(step="step3.token_status", data=result)


@router.post(
    "/step3/token-status/poll",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 3: poll token status until Active",
)
async def test_step3_token_status_poll(
    payload: KsefTokenPollRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    history: list[dict[str, Any]] = []
    for _ in range(payload.attempts):
        current = await auth_service.ksef_http_client.get_ksef_token_status(
            access_token=payload.access_token,
            reference_number=payload.reference_number,
        )
        history.append(current)
        if str(current.get("status_description", "")).lower() == "active":
            return TestResult(step="step3.token_status_poll", data={"active": True, "history": history})
        await asyncio.sleep(payload.delay_seconds)
    return TestResult(step="step3.token_status_poll", data={"active": False, "history": history})


@router.post(
    "/step4/init/ksef-token",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 4: init auth using reusable KSeF token",
)
async def test_step4_init_ksef_token(
    payload: TokenInitRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    if auth_service.token_auth_strategy is None:
        raise ValueError("Token auth strategy is not configured")

    encrypted_token = auth_service.token_auth_strategy.encrypt_token_with_timestamp(
        token_value=payload.ksef_token,
        challenge_timestamp_ms=payload.timestamp_ms,
    )
    init_payload = {
        "challenge": payload.challenge,
        "contextIdentifier": {
            "type": payload.context_identifier_type,
            "value": payload.context_identifier_value,
        },
        "encryptedToken": encrypted_token,
    }
    result = await auth_service.ksef_http_client.init_auth_ksef_token(init_payload)
    return TestResult(step="step4.init_ksef_token", data=result)


@router.post(
    "/step4/status",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 4: check authentication status",
)
async def test_step4_status(
    payload: AuthStatusProbeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    result = await auth_service.ksef_http_client.get_auth_status(
        reference_number=payload.reference_number,
        authentication_token=payload.authentication_token,
    )
    return TestResult(step="step4.status", data=result)


@router.post(
    "/step4/redeem",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Step 4: redeem temporary auth token",
)
async def test_step4_redeem(
    payload: AuthTokenProbeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    result = await auth_service.ksef_http_client.redeem_token(authentication_token=payload.authentication_token)
    return TestResult(step="step4.redeem", data=result)


@router.post(
    "/step4/redeem/token",
    response_model=AuthTokenRedeemResponse,
    status_code=status.HTTP_200_OK,
    summary="Step 4: full token login via AuthService",
)
async def test_step4_redeem_token(
    payload: ServiceContextRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthTokenRedeemResponse:
    return await auth_service.redeem(
        AuthTokenRedeemRequest(
            company_id=payload.company_id,
            environment=payload.environment,
            auth_mode=KsefAuthMode.TOKEN,
        )
    )


@router.post(
    "/stepX/probe/auth-status",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Probe: raw GET /auth/{referenceNumber}",
)
async def probe_auth_status(
    payload: AuthStatusProbeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    result = await auth_service.ksef_http_client.get_auth_status(
        reference_number=payload.reference_number,
        authentication_token=payload.authentication_token,
    )
    return TestResult(step="probe.auth_status", data=result)


@router.post(
    "/stepX/probe/token-redeem",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Probe: raw POST /auth/token/redeem",
)
async def probe_token_redeem(
    payload: AuthTokenProbeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    result = await auth_service.ksef_http_client.redeem_token(authentication_token=payload.authentication_token)
    return TestResult(step="probe.token_redeem", data=result)


@router.post(
    "/refresh",
    response_model=AuthRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token via AuthService",
)
async def test_refresh(
    payload: AuthRefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthRefreshResponse:
    return await auth_service.refresh(payload)


@router.post(
    "/context",
    response_model=AuthContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Read stored auth context via AuthService",
)
async def test_get_context(
    payload: ServiceContextRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthContextResponse:
    return await auth_service.get_auth_context(
        company_id=payload.company_id,
        environment=payload.environment,
    )


@router.post(
    "/context/revoke",
    response_model=TestResult,
    status_code=status.HTTP_200_OK,
    summary="Revoke stored auth context via AuthService",
)
async def test_revoke_context(
    payload: RevokeAuthRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TestResult:
    await auth_service.revoke(
        company_id=payload.company_id,
        environment=payload.environment,
    )
    return TestResult(step="context.revoke", data={"revoked": True})
