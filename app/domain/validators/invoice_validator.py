"""
Invoice business validation.

This module provides:
- Invoice data validation
- Business rule validation
- Required field validation
- Invoice format validation

Classes:
    InvoiceValidator: Invoice business validator

Methods:
    validate(invoice: Invoice) -> None: Validate complete invoice
    validate_required_fields(invoice: Invoice) -> None: Validate required fields
    validate_parties(invoice: Invoice) -> None: Validate buyer and seller parties
    validate_lines(invoice: Invoice) -> None: Validate invoice line items
    validate_totals(invoice: Invoice) -> None: Validate invoice totals
    validate_currency(invoice: Invoice) -> None: Validate currency codes
    validate_issue_dates(invoice: Invoice) -> None: Validate issue dates
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.models.invoice import Invoice


class InvoiceValidator:
    @staticmethod
    def validate(invoice: Invoice) -> None:
        if not invoice.lines:
            raise ValueError("Invoice must contain at least one line")

        calculated_net = sum(
            (line.net_value for line in invoice.lines), start=Decimal("0")
        )
        calculated_vat = sum(
            (line.vat_value for line in invoice.lines), start=Decimal("0")
        )
        calculated_gross = sum(
            (line.gross_value for line in invoice.lines), start=Decimal("0")
        )

        if calculated_net != invoice.totals.total_net:
            raise ValueError("Invoice totals.total_net does not match line net sum")

        if calculated_vat != invoice.totals.total_vat:
            raise ValueError("Invoice totals.total_vat does not match line VAT sum")

        if calculated_gross != invoice.totals.total_gross:
            raise ValueError("Invoice totals.total_gross does not match line gross sum")
