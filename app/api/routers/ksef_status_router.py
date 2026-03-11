"""
KSeF status monitoring endpoints.

This module provides:
- Session status endpoints
- Invoice status endpoints
- UPO status endpoints
- Process monitoring endpoints

Endpoint Functions:
    get_session_status(...) -> SessionStatusResponse: Get session status
    get_invoice_status(...) -> InvoiceStatusResponse: Get invoice status
    download_session_upo(...) -> UpoResponse: Download session UPO
    download_invoice_upo(...) -> UpoResponse: Download invoice UPO
    poll_status_now(...) -> OperationResult: Poll status immediately
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_status_service
from app.schemas.invoices import InvoiceStatusResponse, InvoiceUpoResponse
from app.schemas.sessions import (
    SessionStatusResponse,
    SessionUpoResponse,
    SyncPendingStatusesResponse,
)
from app.services.status_service import StatusService

router = APIRouter(
    prefix="/internal/ksef/status",
    tags=["KSeF Status"],
)


@router.get(
    "/sessions/{reference_number}",
    response_model=SessionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get session status",
)
async def get_session_status(
    reference_number: Annotated[str, Path(description="KSeF session reference number")],
    force_refresh: bool = Query(default=False),
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
) -> SessionStatusResponse:
    return await status_service.get_session_status(
        reference_number=reference_number,
        force_refresh=force_refresh,
    )


@router.post(
    "/sessions/{reference_number}/poll",
    response_model=SessionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Poll session status from KSeF immediately",
)
async def poll_session_status(
    reference_number: Annotated[str, Path(description="KSeF session reference number")],
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
) -> SessionStatusResponse:
    return await status_service.poll_session_status(reference_number)


@router.get(
    "/sessions/{reference_number}/upo",
    response_model=SessionUpoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get session UPO",
)
async def get_session_upo(
    reference_number: Annotated[str, Path(description="KSeF session reference number")],
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
) -> SessionUpoResponse:
    return await status_service.get_session_upo(reference_number)


@router.get(
    "/invoices/{invoice_reference_number}",
    response_model=InvoiceStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get invoice status",
)
async def get_invoice_status(
    invoice_reference_number: Annotated[
        str, Path(description="KSeF invoice reference number")
    ],
    force_refresh: bool = Query(default=False),
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
) -> InvoiceStatusResponse:
    return await status_service.get_invoice_status(
        invoice_reference_number=invoice_reference_number,
        force_refresh=force_refresh,
    )


@router.post(
    "/invoices/{invoice_reference_number}/poll",
    response_model=InvoiceStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Poll invoice status from KSeF immediately",
)
async def poll_invoice_status(
    invoice_reference_number: Annotated[
        str, Path(description="KSeF invoice reference number")
    ],
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
) -> InvoiceStatusResponse:
    return await status_service.poll_invoice_status(invoice_reference_number)


@router.get(
    "/invoices/{invoice_reference_number}/upo",
    response_model=InvoiceUpoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get invoice UPO",
)
async def get_invoice_upo(
    invoice_reference_number: Annotated[
        str, Path(description="KSeF invoice reference number")
    ],
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
) -> InvoiceUpoResponse:
    return await status_service.get_invoice_upo(invoice_reference_number)


@router.post(
    "/sync-pending",
    response_model=SyncPendingStatusesResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize statuses for pending sessions and invoices",
)
async def sync_pending_statuses(
    limit: int = Query(default=100, ge=1, le=1000),
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
) -> SyncPendingStatusesResponse:
    return await status_service.sync_pending(limit=limit)
