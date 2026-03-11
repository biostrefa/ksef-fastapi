"""
KSeF invoice endpoints.

This module provides:
- Invoice submission endpoints
- Invoice retrieval endpoints
- Invoice status endpoints
- UPO generation endpoints

Endpoint Functions:
    send_invoice(...) -> SendInvoiceResponse: Send invoice
    get_invoice_submission(...) -> InvoiceSubmissionResponse: Get invoice submission details
    list_invoice_submissions(...) -> list[InvoiceSubmissionResponse]: List invoice submissions
    resend_invoice(...) -> SendInvoiceResponse: Resend invoice
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_invoice_service
from app.schemas.invoices import (
    InvoiceDetailsResponse,
    InvoiceListResponse,
    InvoiceXmlResponse,
    ResubmitInvoiceResponse,
    SubmitInvoiceRequest,
    SubmitInvoiceResponse,
)
from app.services.invoice_service import InvoiceService

router = APIRouter(
    prefix="/internal/ksef/invoices",
    tags=["KSeF Invoices"],
)


@router.post(
    "/submit",
    response_model=SubmitInvoiceResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit invoice to KSeF",
)
async def submit_invoice(
    payload: SubmitInvoiceRequest,
    invoice_service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> SubmitInvoiceResponse:
    return await invoice_service.submit_invoice(payload)


@router.get(
    "/{submission_id}",
    response_model=InvoiceDetailsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get local invoice submission details",
)
async def get_invoice_submission(
    submission_id: Annotated[str, Path(description="Local invoice submission ID")],
    invoice_service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetailsResponse:
    return await invoice_service.get_submission(submission_id)


@router.get(
    "/{submission_id}/xml",
    response_model=InvoiceXmlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get generated invoice XML from local storage",
)
async def get_invoice_xml(
    submission_id: Annotated[str, Path(description="Local invoice submission ID")],
    invoice_service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceXmlResponse:
    return await invoice_service.get_submission_xml(submission_id)


@router.post(
    "/{submission_id}/resubmit",
    response_model=ResubmitInvoiceResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resubmit previously failed invoice",
)
async def resubmit_invoice(
    submission_id: Annotated[str, Path(description="Local invoice submission ID")],
    invoice_service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> ResubmitInvoiceResponse:
    return await invoice_service.resubmit_invoice(submission_id)


@router.get(
    "",
    response_model=InvoiceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List local invoice submissions",
)
async def list_invoice_submissions(
    session_reference_number: str | None = Query(default=None),
    local_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    invoice_service: Annotated[InvoiceService, Depends(get_invoice_service)] = None,
) -> InvoiceListResponse:
    return await invoice_service.list_submissions(
        session_reference_number=session_reference_number,
        local_status=local_status,
        limit=limit,
        offset=offset,
    )
