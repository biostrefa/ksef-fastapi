"""
Session database model.

This module provides:
- KSeF session table definition
- Session metadata storage
- Session state tracking
- Session relationships

ORM Classes:
    SessionModel(Base): Session database model

Fields:
    id: Primary key
    company_id: Company identifier
    reference_number: KSeF reference number
    session_type: Session type (online/batch)
    status: Session status
    opened_at: Session opening time
    closed_at: Session closing time
    last_checked_at: Last status check time
"""
