"""
KSeF session management endpoints.

This module provides:
- Online session endpoints
- Batch session endpoints
- Session lifecycle management
- Reference number handling

Endpoint Functions:
    open_online_session(...) -> OpenSessionResponse: Open online session
    close_online_session(...) -> CloseSessionResponse: Close online session
    get_session(...) -> SessionResponse: Get session details
    list_sessions(...) -> list[SessionResponse]: List all sessions
    open_batch_session(...) -> OpenSessionResponse: Open batch session
"""
