"""
KSeF HTTP client.

This module provides:
- KSeF API integration
- Request/response handling
- KSeF-specific error handling

Classes:
    KsefHttpClient(BaseHttpClient): KSeF-specific HTTP client

Auth Methods:
    get_challenge() -> dict: Get authentication challenge
    redeem_token(payload: dict) -> dict: Redeem authentication token
    refresh_token(payload: dict) -> dict: Refresh authentication token

Session Methods:
    open_online_session(access_token: str, payload: dict) -> dict: Open online session
    open_batch_session(access_token: str, payload: dict) -> dict: Open batch session
    close_session(access_token: str, reference_number: str) -> dict: Close session
    get_session_status(access_token: str, reference_number: str) -> dict: Get session status

Invoice Methods:
    send_invoice(access_token: str, reference_number: str, payload: dict) -> dict: Send invoice
    get_invoice_status(access_token: str, reference_number: str, invoice_reference: str) -> dict: Get invoice status

UPO Methods:
    download_session_upo(access_token: str, reference_number: str) -> dict: Download session UPO
    download_invoice_upo(access_token: str, invoice_reference: str) -> dict: Download invoice UPO
"""
