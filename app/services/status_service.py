"""
Status monitoring service.

This module provides:
- Session status retrieval
- Invoice status tracking
- UPO status monitoring
- Status polling logic

Classes:
    StatusService: Status monitoring service

Public Methods:
    get_session_status(reference_number: str) -> SessionStatusSnapshot: Get session status
    get_invoice_status(submission_id: str) -> InvoiceSubmission: Get invoice status
    download_session_upo(reference_number: str) -> str: Download session UPO
    download_invoice_upo(submission_id: str) -> str: Download invoice UPO
    poll_and_update_session(reference_number: str) -> SessionStatusSnapshot: Poll and update session status
    poll_and_update_invoice(submission_id: str) -> InvoiceSubmission: Poll and update invoice status

Private Methods:
    _get_access_token_for_session(reference_number: str) -> str: Get access token for session
    _update_local_session_status(snapshot: SessionStatusSnapshot) -> None: Update local session status
    _update_local_invoice_status(submission: InvoiceSubmission) -> None: Update local invoice status
"""
