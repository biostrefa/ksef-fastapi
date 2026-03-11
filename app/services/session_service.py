"""
Session management service.

This module provides:
- Session opening and closing
- Reference number management
- Session lifecycle handling
- Session state tracking

Classes:
    SessionService: Session management service

Public Methods:
    open_online_session(company_id: str) -> KsefSession: Open online session
    open_batch_session(company_id: str) -> KsefSession: Open batch session
    close_session(reference_number: str) -> KsefSession: Close session by reference number
    get_session(reference_number: str) -> KsefSession: Get session by reference number
    list_sessions(company_id: str) -> list[KsefSession]: List all sessions for company

Private Methods:
    _get_valid_access_token(company_id: str) -> str: Get valid access token for company
    _persist_opened_session(session: KsefSession) -> None: Persist opened session to storage
"""
