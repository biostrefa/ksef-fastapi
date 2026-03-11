"""
Webhook and callback endpoints.

This module provides:
- Optional callback endpoints
- Internal event handling
- Webhook management
- Event processing
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.deps import get_audit_service, get_status_service
from app.services.audit_service import AuditService
from app.services.status_service import StatusService

router = APIRouter(
    prefix="/internal/webhooks",
    tags=["Webhooks"],
)


@router.post(
    "/ksef/status-update",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive KSeF-related status callback",
)
async def receive_ksef_status_update(
    request: Request,
    x_webhook_signature: str | None = Header(default=None),
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
    audit_service: Annotated[AuditService, Depends(get_audit_service)] = None,
) -> dict[str, Any]:
    payload = await request.json()

    # Replace this with real signature validation when you decide
    # how callbacks are authenticated in your environment.
    if x_webhook_signature is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook signature header.",
        )

    await audit_service.log_webhook_received(
        source="ksef",
        payload=payload,
        headers=dict(request.headers),
    )
    await status_service.handle_external_status_callback(payload)

    return {"accepted": True}


@router.post(
    "/jobs/retry-finished",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive internal retry worker callback",
)
async def receive_retry_finished(
    request: Request,
    audit_service: Annotated[AuditService, Depends(get_audit_service)] = None,
) -> dict[str, Any]:
    payload = await request.json()

    await audit_service.log_webhook_received(
        source="retry-worker",
        payload=payload,
        headers=dict(request.headers),
    )

    return {"accepted": True}


@router.post(
    "/storage/upo-ready",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive storage callback when UPO artifact is ready",
)
async def receive_upo_ready(
    request: Request,
    status_service: Annotated[StatusService, Depends(get_status_service)] = None,
    audit_service: Annotated[AuditService, Depends(get_audit_service)] = None,
) -> dict[str, Any]:
    payload = await request.json()

    await audit_service.log_webhook_received(
        source="storage",
        payload=payload,
        headers=dict(request.headers),
    )
    await status_service.handle_upo_storage_callback(payload)

    return {"accepted": True}
