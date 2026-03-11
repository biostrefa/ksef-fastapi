"""
Main FastAPI application entry point.

This module contains the main application setup, router registration,
and lifespan management for startup and shutdown events.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager

# Import routers
from app.api.routers import (
    health_router,
    ksef_auth_router,
    ksef_session_router,
    ksef_invoice_router,
    ksef_status_router,
    webhook_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events including:
    - Database connections
    - Background workers
    - Resource cleanup
    """
    # Startup logic here
    yield
    # Shutdown logic here


app = FastAPI(
    title="KSeF FastAPI Integration",
    description="FastAPI service for KSeF (Krajowy System e-Faktur) integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router.router, prefix="/health", tags=["health"])
app.include_router(ksef_auth_router.router, prefix="/api/auth", tags=["ksef-auth"])
app.include_router(ksef_session_router.router, prefix="/api/sessions", tags=["ksef-sessions"])
app.include_router(ksef_invoice_router.router, prefix="/api/invoices", tags=["ksef-invoices"])
app.include_router(ksef_status_router.router, prefix="/api/status", tags=["ksef-status"])
app.include_router(webhook_router.router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/")
async def root():
    """Root endpoint for basic connectivity check."""
    return {"message": "KSeF FastAPI Integration Service"}
