"""
Session workflow models.

This module provides:
- Session creation models
- Session lifecycle models
- Session status tracking models
- Session management temporal models
"""

from __future__ import annotations

from pydantic import BaseModel


class OpenOnlineSessionInput(BaseModel):
    company_id: str
    environment: str
    access_token: str
    form_code: dict
    encryption: dict


class OpenOnlineSessionResult(BaseModel):
    reference_number: str
    status_code: int | None = None
    status_description: str | None = None


class CloseOnlineSessionInput(BaseModel):
    session_reference_number: str
    access_token: str


class SessionStatusInput(BaseModel):
    session_reference_number: str
    access_token: str


class SessionStatusResult(BaseModel):
    reference_number: str
    status_code: int | None = None
    status_description: str | None = None
