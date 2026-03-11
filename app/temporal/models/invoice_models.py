"""
Invoice workflow models.

This module provides:
- Invoice submission models
- Invoice processing models
- Invoice status models
- Invoice reconciliation temporal models
"""

from __future__ import annotations

from pydantic import BaseModel


class SendInvoiceOnlineInput(BaseModel):
    invoice_id: str
    company_id: str
    environment: str
    requested_by: str
    correlation_id: str


class SendInvoiceOnlineResult(BaseModel):
    invoice_id: str
    submission_id: str
    session_reference_number: str
    invoice_reference_number: str | None = None
    final_status: str
    upo_storage_key: str | None = None


class SendInvoiceBatchInput(BaseModel):
    batch_id: str
    company_id: str
    environment: str
    requested_by: str
    correlation_id: str


class SendInvoiceBatchResult(BaseModel):
    batch_id: str
    submission_id: str
    final_status: str
