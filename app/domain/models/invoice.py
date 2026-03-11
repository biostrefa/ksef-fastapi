"""
Invoice domain model.

This module provides:
- Invoice domain entity
- Invoice business logic
- Invoice validation rules
- Invoice state management

Classes:
    Invoice: Main invoice domain model
    InvoiceParty: Invoice party (buyer/seller) model
    InvoiceLine: Invoice line item model
    InvoiceTotals: Invoice totals calculation model
    InvoiceSubmission: Local invoice submission record
    EncryptedInvoicePayload: Encrypted invoice content model
        - encrypted_content: Encrypted invoice data
        - content_hash: Hash of the content
        - file_size: Size of the encrypted file
        - metadata: Additional metadata
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.constants import (
    InvoiceCurrency,
    InvoiceKind,
    InvoiceSubmissionStatus,
    PaymentMethod,
)
from app.domain.models.auth import DomainModel


class Address(DomainModel):
    country_code: str = Field(..., min_length=2, max_length=2)
    postal_code: str
    city: str
    street: str | None = None
    building_no: str | None = None
    apartment_no: str | None = None


class InvoiceParty(DomainModel):
    name: str
    tax_id: str | None = None
    email: str | None = None
    address: Address | None = None


class InvoiceLine(DomainModel):
    line_no: int = Field(..., ge=1)
    name: str
    quantity: Decimal = Field(..., gt=0)
    unit_code: str = "szt"
    unit_net_price: Decimal = Field(..., ge=0)
    vat_rate: Decimal = Field(..., ge=0)
    net_value: Decimal = Field(..., ge=0)
    vat_value: Decimal = Field(..., ge=0)
    gross_value: Decimal = Field(..., ge=0)
    pkwiu: str | None = None
    gtin: str | None = None

    @model_validator(mode="after")
    def validate_amounts(self) -> "InvoiceLine":
        if self.gross_value < self.net_value:
            raise ValueError("gross_value cannot be lower than net_value")
        return self


class InvoiceTotals(DomainModel):
    total_net: Decimal = Field(..., ge=0)
    total_vat: Decimal = Field(..., ge=0)
    total_gross: Decimal = Field(..., ge=0)
    amount_due: Decimal = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> "InvoiceTotals":
        if self.total_gross < self.total_net:
            raise ValueError("total_gross cannot be lower than total_net")
        return self


class InvoicePayment(DomainModel):
    method: PaymentMethod = PaymentMethod.TRANSFER
    due_date: date | None = None
    bank_account: str | None = None
    split_payment: bool = False


class Invoice(DomainModel):
    company_id: UUID
    invoice_number: str
    issue_date: date
    sale_date: date | None = None
    currency: InvoiceCurrency = InvoiceCurrency.PLN
    invoice_kind: InvoiceKind = InvoiceKind.VAT
    seller: InvoiceParty
    buyer: InvoiceParty
    lines: list[InvoiceLine]
    totals: InvoiceTotals
    payment: InvoicePayment | None = None
    notes: str | None = None
    correction_reason: str | None = None
    original_invoice_number: str | None = None

    @field_validator("lines")
    @classmethod
    def validate_lines_non_empty(cls, value: list[InvoiceLine]) -> list[InvoiceLine]:
        if not value:
            raise ValueError("invoice must contain at least one line")
        return value


class EncryptedInvoicePayload(DomainModel):
    invoice_hash_sha256_base64: str
    invoice_size: int

    encrypted_invoice_hash_sha256_base64: str
    encrypted_invoice_size: int
    encrypted_content_base64: str

    encryption_method: str
    checksum_algorithm: str = "SHA-256"
    metadata: dict = Field(default_factory=dict)


class InvoiceSubmission(DomainModel):
    submission_id: UUID
    company_id: UUID
    session_reference_number: str
    local_invoice_number: str
    ksef_invoice_reference: str | None = None
    status: InvoiceSubmissionStatus
    xml_hash_sha256: str | None = None
    upo_content: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
