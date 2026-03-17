"""
KSeF authentication endpoints.

This module provides:
- Internal KSeF authentication endpoints
- Challenge generation and verification
- Token management endpoints
- Authentication context handling

Endpoint Functions:
    start_challenge(...) -> AuthChallengeResponse: Start authentication challenge
    redeem_token(...) -> AuthTokenRedeemResponse: Redeem authentication token
    refresh_access_token(...) -> AuthRefreshResponse: Refresh access token
    get_auth_context(...) -> AuthContextResponse: Get authentication context
    revoke_auth(...) -> OperationResult: Revoke authentication
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_auth_service
from app.core.constants import KsefAuthMode, KsefEnvironment
from app.schemas.auth import (
    AuthChallengeRequest,
    AuthChallengeResponse,
    AuthContextResponse,
    AuthRefreshRequest,
    AuthRefreshResponse,
    AuthTokenRedeemRequest,
    AuthTokenRedeemResponse,
    RefreshTokenRequest,
    RevokeAuthRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/internal/ksef/auth",
    tags=["KSeF Auth"],
)


@router.post(
    "/challenge",
    response_model=AuthChallengeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create KSeF authentication challenge",
)
async def create_challenge(
    payload: AuthChallengeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthChallengeResponse:
    return await auth_service.start_challenge(payload)


@router.post(
    "/authenticate/token",
    response_model=AuthTokenRedeemResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate in KSeF using KSeF token strategy",
)
async def authenticate_with_token(
    payload: AuthChallengeRequest,
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
    "/authenticate/xades",
    response_model=AuthTokenRedeemResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate in KSeF using XAdES signature strategy",
)
async def authenticate_with_xades(
    payload: AuthChallengeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthTokenRedeemResponse:
    return await auth_service.redeem(
        AuthTokenRedeemRequest(
            company_id=payload.company_id,
            environment=payload.environment,
            auth_mode=KsefAuthMode.XADES,
        )
    )


@router.post(
    "/refresh",
    response_model=AuthRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh KSeF access token",
)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthRefreshResponse:
    return await auth_service.refresh(
        AuthRefreshRequest(
            company_id=payload.company_id,
            environment=payload.environment,
            refresh_token=payload.refresh_token,
        )
    )


@router.get(
    "/context",
    response_model=AuthContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current local KSeF auth context",
)
async def get_auth_context(
    company_id: str,
    environment: KsefEnvironment,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthContextResponse:
    from uuid import UUID

    return await auth_service.get_auth_context(
        company_id=UUID(company_id),
        environment=environment,
    )


@router.delete(
    "/context",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke local KSeF auth context",
)
async def revoke_auth_context(
    payload: RevokeAuthRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await auth_service.revoke(
        company_id=payload.company_id,
        environment=payload.environment,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
