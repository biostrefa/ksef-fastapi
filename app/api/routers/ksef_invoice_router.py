"""
KSeF invoice endpoints.

This module provides:
- Invoice submission endpoints
- Invoice retrieval endpoints
- Invoice status endpoints
- UPO generation endpoints

Endpoint Functions:
    send_invoice(...) -> SendInvoiceResponse: Send invoice
    get_invoice_submission(...) -> InvoiceSubmissionResponse: Get invoice submission details
    list_invoice_submissions(...) -> list[InvoiceSubmissionResponse]: List invoice submissions
    resend_invoice(...) -> SendInvoiceResponse: Resend invoice
"""
