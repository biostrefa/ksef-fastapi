"""
KSeF API routers package.

This package contains all FastAPI routers for the KSeF integration service.
Each router handles a specific functional domain of the API.

Available Routers:
    auth_testing_router: Testing endpoints for authentication flow debugging
    health_router: Health check and monitoring endpoints
    ksef_auth_router: KSeF authentication endpoints
    ksef_session_router: KSeF session management endpoints
    ksef_invoice_router: Invoice submission and management endpoints
    ksef_status_router: Status monitoring and polling endpoints
    webhook_router: Webhook and callback handling endpoints
"""

from __future__ import annotations

from app.api.routers import (
    auth_testing_router,
    health_router,
    ksef_auth_router,
    ksef_invoice_router,
    ksef_session_router,
    ksef_status_router,
    webhook_router,
)

__all__ = [
    "auth_testing_router",
    "health_router",
    "ksef_auth_router",
    "ksef_invoice_router",
    "ksef_session_router",
    "ksef_status_router",
    "webhook_router",
]
