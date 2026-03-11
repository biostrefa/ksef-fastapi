"""
FA(3) XML builder for invoices.

This module provides:
- FA(3) XML generation
- Invoice XML structure building
- XML validation and formatting
- KSeF XML compliance

Classes:
    InvoiceFa3Builder: FA(3) XML builder for invoices

Methods:
    build(invoice: Invoice) -> str: Build complete FA(3) XML from invoice
    _build_header(invoice: Invoice) -> Element: Build XML header section
    _build_seller(invoice: Invoice) -> Element: Build seller XML section
    _build_buyer(invoice: Invoice) -> Element: Build buyer XML section
    _build_lines(invoice: Invoice) -> Element: Build invoice lines XML section
    _build_totals(invoice: Invoice) -> Element: Build totals XML section
    _serialize_xml(root: Element) -> str: Serialize XML element to string

Note: This should be a pure XML builder without HTTP and database dependencies.
"""
