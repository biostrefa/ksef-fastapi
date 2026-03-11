"""
KSeF response mapping.

This module provides:
- KSeF API response mapping
- Response to domain model mapping
- Error response mapping
- Status response mapping

Classes:
    KsefResponseMapper: KSeF response mapper

Methods:
    map_auth_tokens(payload: dict) -> AuthTokens: Map authentication tokens from KSeF response
    map_session_open_response(payload: dict) -> KsefSession: Map session opening response to domain model
    map_session_status_response(payload: dict) -> SessionStatusSnapshot: Map session status response
    map_invoice_send_response(payload: dict) -> InvoiceSubmission: Map invoice send response
    map_invoice_status_response(payload: dict) -> InvoiceSubmission: Map invoice status response
    map_upo_response(payload: dict) -> str: Map UPO response to string
"""
