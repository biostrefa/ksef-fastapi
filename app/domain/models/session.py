"""
KSeF session domain model.

This module provides:
- KSeF session domain entity
- Session lifecycle management
- Session state tracking
- Session validation rules

Classes:
    KsefSession: KSeF session domain entity
        - id: Session identifier
        - reference_number: KSeF reference number
        - session_type: Type of session (online/batch)
        - status: Current session status
        - opened_at: Session opening timestamp
        - closed_at: Session closing timestamp
    SessionStatusSnapshot: Session status snapshot entity
        - reference_number: KSeF reference number
        - status: Session status at snapshot time
        - last_checked_at: Last status check timestamp
"""
