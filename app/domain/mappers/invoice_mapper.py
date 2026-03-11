"""
Invoice data mapping.

This module provides:
- ERP to domain model mapping
- Domain to XML mapping
- KSeF input mapping
- Data transformation logic

Classes:
    InvoiceMapper: Invoice data mapper

Methods:
    from_send_request(dto: SendInvoiceRequest) -> Invoice: Map from send request to domain model
    from_erp_payload(payload: dict) -> Invoice: Map from ERP payload to domain model
    to_submission_response(submission: InvoiceSubmission) -> SendInvoiceResponse: Map to submission response
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.domain.models.invoice import (
    Address,
    Invoice,
    InvoiceLine,
    InvoiceParty,
    InvoicePayment,
    InvoiceSubmission,
    InvoiceTotals,
)
from app.schemas.invoices import (
    AddressDto,
    InvoiceLineItemDto,
    InvoicePartyDto,
    InvoicePayloadDto,
    InvoiceSubmissionResponse,
    SendInvoiceRequest,
    SendInvoiceResponse,
)


class InvoiceMapper:
    @staticmethod
    def _map_address(dto: AddressDto | None) -> Address | None:
        if dto is None:
            return None
        return Address(**dto.model_dump())

    @staticmethod
    def _map_party(dto: InvoicePartyDto) -> InvoiceParty:
        return InvoiceParty(
            name=dto.name,
            tax_id=dto.tax_id,
            email=dto.email,
            address=InvoiceMapper._map_address(dto.address),
        )

    @staticmethod
    def _map_line(dto: InvoiceLineItemDto) -> InvoiceLine:
        return InvoiceLine(**dto.model_dump())

    @staticmethod
    def from_invoice_payload(dto: InvoicePayloadDto) -> Invoice:
        return Invoice(
            company_id=dto.company_id,
            invoice_number=dto.invoice_number,
            issue_date=dto.issue_date,
            sale_date=dto.sale_date,
            currency=dto.currency,
            invoice_kind=dto.invoice_kind,
            seller=InvoiceMapper._map_party(dto.seller),
            buyer=InvoiceMapper._map_party(dto.buyer),
            lines=[InvoiceMapper._map_line(line) for line in dto.lines],
            totals=InvoiceTotals(**dto.totals.model_dump()),
            payment=InvoicePayment(**dto.payment.model_dump()) if dto.payment else None,
            notes=dto.notes,
            correction_reason=dto.correction_reason,
            original_invoice_number=dto.original_invoice_number,
        )

    @staticmethod
    def from_send_request(request: SendInvoiceRequest) -> Invoice:
        return InvoiceMapper.from_invoice_payload(request.invoice)

    @staticmethod
    def to_send_response(submission: InvoiceSubmission) -> SendInvoiceResponse:
        return SendInvoiceResponse(
            submission_id=submission.submission_id,
            company_id=submission.company_id,
            session_reference_number=submission.session_reference_number,
            local_invoice_number=submission.local_invoice_number,
            ksef_invoice_reference=submission.ksef_invoice_reference,
            status=submission.status,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
        )

    @staticmethod
    def to_submission_response(
        submission: InvoiceSubmission,
    ) -> InvoiceSubmissionResponse:
        return InvoiceSubmissionResponse(
            submission_id=submission.submission_id,
            company_id=submission.company_id,
            session_reference_number=submission.session_reference_number,
            local_invoice_number=submission.local_invoice_number,
            ksef_invoice_reference=submission.ksef_invoice_reference,
            status=submission.status,
            xml_hash_sha256=submission.xml_hash_sha256,
            upo_available=bool(submission.upo_content),
            error_code=submission.error_code,
            error_message=submission.error_message,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
        )
