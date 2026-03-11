"""
Invoice request/response models.

This module provides:
- Invoice submission models
- Invoice status models
- UPO models
- Invoice metadata models

Pydantic Classes:
    SendInvoiceRequest: Invoice submission request
    SendInvoiceResponse: Invoice submission response
    InvoiceSubmissionResponse: Invoice submission details response
    InvoiceStatusResponse: Invoice status response
    UpoResponse: UPO (Unified Proof of Purchase) response
    InvoiceLineItemDto: Invoice line item data transfer object
    SellerDto: Seller information data transfer object
    BuyerDto: Buyer information data transfer object
    InvoicePayloadDto: Invoice payload data transfer object
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
from app.schemas.common import ApiModel


class AddressDto(ApiModel):
    country_code: str = Field(..., min_length=2, max_length=2)
    postal_code: str
    city: str
    street: str | None = None
    building_no: str | None = None
    apartment_no: str | None = None


class InvoicePartyDto(ApiModel):
    name: str
    tax_id: str | None = None
    email: str | None = None
    address: AddressDto | None = None


class InvoiceLineItemDto(ApiModel):
    line_no: int = Field(..., ge=1)
    name: str
    quantity: Decimal = Field(..., gt=0)
    unit_code: str = Field(default="szt")
    unit_net_price: Decimal = Field(..., ge=0)
    vat_rate: Decimal = Field(..., ge=0)
    net_value: Decimal = Field(..., ge=0)
    vat_value: Decimal = Field(..., ge=0)
    gross_value: Decimal = Field(..., ge=0)
    pkwiu: str | None = None
    gtin: str | None = None

    @model_validator(mode="after")
    def validate_amounts(self) -> "InvoiceLineItemDto":
        if self.gross_value < self.net_value:
            raise ValueError("gross_value cannot be lower than net_value")
        return self


class InvoiceTotalsDto(ApiModel):
    total_net: Decimal = Field(..., ge=0)
    total_vat: Decimal = Field(..., ge=0)
    total_gross: Decimal = Field(..., ge=0)
    amount_due: Decimal = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> "InvoiceTotalsDto":
        if self.total_gross < self.total_net:
            raise ValueError("total_gross cannot be lower than total_net")
        return self


class InvoicePaymentDto(ApiModel):
    method: PaymentMethod = PaymentMethod.TRANSFER
    due_date: date | None = None
    bank_account: str | None = None
    split_payment: bool = False


class InvoicePayloadDto(ApiModel):
    company_id: UUID
    invoice_number: str
    issue_date: date
    sale_date: date | None = None
    currency: InvoiceCurrency = InvoiceCurrency.PLN
    invoice_kind: InvoiceKind = InvoiceKind.VAT
    seller: InvoicePartyDto
    buyer: InvoicePartyDto
    lines: list[InvoiceLineItemDto] = Field(default_factory=list)
    totals: InvoiceTotalsDto
    payment: InvoicePaymentDto | None = None
    notes: str | None = None
    correction_reason: str | None = None
    original_invoice_number: str | None = None

    @field_validator("lines")
    @classmethod
    def validate_lines_non_empty(
        cls, value: list[InvoiceLineItemDto]
    ) -> list[InvoiceLineItemDto]:
        if not value:
            raise ValueError("invoice must contain at least one line")
        return value


class SendInvoiceRequest(ApiModel):
    company_id: UUID
    environment: str
    invoice: InvoicePayloadDto
    session_reference_number: str | None = None
    auto_open_session: bool = True


class SendInvoiceResponse(ApiModel):
    submission_id: UUID
    company_id: UUID
    session_reference_number: str
    local_invoice_number: str
    ksef_invoice_reference: str | None = None
    status: InvoiceSubmissionStatus
    created_at: datetime
    updated_at: datetime


class InvoiceSubmissionResponse(ApiModel):
    submission_id: UUID
    company_id: UUID
    session_reference_number: str
    local_invoice_number: str
    ksef_invoice_reference: str | None = None
    status: InvoiceSubmissionStatus
    xml_hash_sha256: str | None = None
    upo_available: bool = False
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceStatusResponse(ApiModel):
    submission_id: UUID
    ksef_invoice_reference: str | None = None
    status: InvoiceSubmissionStatus
    last_checked_at: datetime
    error_code: str | None = None
    error_message: str | None = None


class UpoResponse(ApiModel):
    submission_id: UUID | None = None
    session_reference_number: str | None = None
    upo_content: str
    content_type: str = "application/xml"
    downloaded_at: datetime
