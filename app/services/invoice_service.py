"""
Invoice submission service.

This module provides:
- Invoice submission orchestration
- Invoice processing workflow
- Invoice validation and submission
- Invoice status tracking

Classes:
    InvoiceService: Invoice submission service

Public Methods:
    send_invoice(request: SendInvoiceRequest) -> InvoiceSubmission: Send invoice to KSeF
    resend_invoice(submission_id: str) -> InvoiceSubmission: Resend invoice submission
    get_submission(submission_id: str) -> InvoiceSubmission: Get invoice submission details
    list_submissions(company_id: str) -> list[InvoiceSubmission]: List all submissions for company

Private Methods:
    _load_or_open_session(company_id: str) -> KsefSession: Load existing or open new session
    _build_invoice_model(request: SendInvoiceRequest) -> Invoice: Build invoice domain model
    _validate_invoice(invoice: Invoice) -> None: Validate invoice business rules
    _build_fa3_xml(invoice: Invoice) -> str: Build FA(3) XML from invoice
    _encrypt_invoice(xml: str) -> EncryptedInvoicePayload: Encrypt invoice XML
    _send_to_ksef(reference_number: str, payload: EncryptedInvoicePayload) -> dict: Send to KSeF API
    _save_submission(...) -> InvoiceSubmission: Save submission to storage
"""
