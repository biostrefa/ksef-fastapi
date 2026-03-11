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
