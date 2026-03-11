"""
KSeF status monitoring endpoints.

This module provides:
- Session status endpoints
- Invoice status endpoints
- UPO status endpoints
- Process monitoring endpoints

Endpoint Functions:
    get_session_status(...) -> SessionStatusResponse: Get session status
    get_invoice_status(...) -> InvoiceStatusResponse: Get invoice status
    download_session_upo(...) -> UpoResponse: Download session UPO
    download_invoice_upo(...) -> UpoResponse: Download invoice UPO
    poll_status_now(...) -> OperationResult: Poll status immediately
"""
