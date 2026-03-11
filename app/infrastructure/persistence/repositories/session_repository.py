"""
Session repository.

This module provides:
- Session CRUD operations
- Session storage and retrieval
- Session state management
- Session query operations

Classes:
    SessionRepository: Session data access layer

Methods:
    save(session: KsefSession) -> None: Save session
    get_by_reference(reference_number: str) -> KsefSession | None: Get session by reference number
    get_open_session_for_company(company_id: str) -> KsefSession | None: Get open session for company
    list_by_company(company_id: str) -> list[KsefSession]: List sessions for company
    update_status(reference_number: str, status: str) -> None: Update session status
    close(reference_number: str, closed_at: datetime) -> None: Close session
"""
