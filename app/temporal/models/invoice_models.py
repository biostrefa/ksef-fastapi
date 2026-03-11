"""
Invoice workflow models.

This module provides:
- Invoice submission models
- Invoice processing models
- Invoice status models
- Invoice reconciliation temporal models
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SendInvoiceOnlineInput:
    invoice_id: str
    company_id: str
    environment: str
    requested_by: str
    correlation_id: str


@dataclass
class SendInvoiceOnlineResult:
    invoice_id: str
    submission_id: str
    session_reference_number: str
    invoice_reference_number: Optional[str]
    final_status: str
    upo_storage_key: Optional[str] = None


@dataclass
class SendInvoiceBatchInput:
    batch_id: str
    company_id: str
    environment: str
    requested_by: str
    correlation_id: str


@dataclass
class SendInvoiceBatchResult:
    batch_id: str
    submission_id: str
    final_status: str
