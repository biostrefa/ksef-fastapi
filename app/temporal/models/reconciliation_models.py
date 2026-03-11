"""
Reconciliation workflow models.

This module provides:
- Reconciliation task models
- Status synchronization models
- Error handling models
- Reconciliation result models
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReconcilePendingInput:
    company_id: str | None
    environment: str
    limit: int = 100


@dataclass
class ReconcilePendingResult:
    scanned: int
    updated: int
    failed: int
