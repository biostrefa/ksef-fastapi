"""
Reconciliation workflow models.

This module provides:
- Reconciliation task models
- Status synchronization models
- Error handling models
- Reconciliation result models
"""

from __future__ import annotations

from pydantic import BaseModel


class ReconcilePendingInput(BaseModel):
    company_id: str | None = None
    environment: str
    limit: int = 100


class ReconcilePendingResult(BaseModel):
    scanned: int
    updated: int
    failed: int
