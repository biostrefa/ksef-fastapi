"""
Invoice repository.

This module provides:
- Invoice CRUD operations
- Invoice status storage
- UPO storage and retrieval
- Invoice query operations

Classes:
    InvoiceRepository: Invoice data access layer

Methods:
    save(submission: InvoiceSubmission) -> None: Save invoice submission
    get_by_id(submission_id: str) -> InvoiceSubmission | None: Get submission by ID
    get_by_ksef_reference(ksef_invoice_reference: str) -> InvoiceSubmission | None: Get submission by KSeF reference
    list_by_company(company_id: str) -> list[InvoiceSubmission]: List submissions for company
    update_status(submission_id: str, status: str) -> None: Update submission status
    save_upo(submission_id: str, upo_content: str) -> None: Save UPO content
    save_error(submission_id: str, error_code: str, error_message: str) -> None: Save error information
"""
