"""
KSeF session management endpoints.

This module provides:
- Online session endpoints
- Batch session endpoints
- Session lifecycle management
- Reference number handling

Endpoint Functions:
    open_online_session(...) -> OpenSessionResponse: Open online session
    close_online_session(...) -> CloseSessionResponse: Close online session
    get_session(...) -> SessionResponse: Get session details
    list_sessions(...) -> list[SessionResponse]: List all sessions
    open_batch_session(...) -> OpenSessionResponse: Open batch session
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import get_session_service
from app.schemas.sessions import (
    CloseSessionResponse,
    CreateBatchSessionRequest,
    CreateOnlineSessionRequest,
    SessionResponse,
)
from app.services.session_service import SessionService

router = APIRouter(
    prefix="/internal/ksef/sessions",
    tags=["KSeF Sessions"],
)


@router.post(
    "/online",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create online KSeF session",
)
async def create_online_session(
    payload: CreateOnlineSessionRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    return await session_service.create_online_session(payload)


@router.post(
    "/batch",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create batch KSeF session",
)
async def create_batch_session(
    payload: CreateBatchSessionRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    return await session_service.create_batch_session(payload)


@router.get(
    "/{reference_number}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get local KSeF session details",
)
async def get_session(
    reference_number: Annotated[str, Path(description="KSeF session reference number")],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    return await session_service.get_session(reference_number)


@router.post(
    "/{reference_number}/close",
    response_model=CloseSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Close KSeF session",
)
async def close_session(
    reference_number: Annotated[str, Path(description="KSeF session reference number")],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> CloseSessionResponse:
    return await session_service.close_session(reference_number)
