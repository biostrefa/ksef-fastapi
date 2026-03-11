"""
Healthcheck endpoints.

This module provides:
- Health check endpoints
- Readiness probes
- Liveness probes
- System status monitoring
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "message": "Service is running"}
