"""
Application exceptions and error mapping.

This module contains:
- Custom application exceptions
- Error code definitions
- Error response mapping
- Exception handling utilities

Classes:
    AppError: Base application exception
    ValidationError: Validation error exception
    AuthenticationError: Authentication error exception
    AuthorizationError: Authorization error exception
    KsefApiError: KSEF API error exception
    KsefTransportError: KSEF transport error exception
    KsefBusinessError: KSEF business error exception
    SessionNotFoundError: Session not found error exception
    InvoiceNotFoundError: Invoice not found error exception
    RepositoryError: Repository error exception

Functions:
    app_error_to_http_status(exc: AppError) -> int: Convert application error to HTTP status code
    app_error_to_response(exc: AppError) -> dict: Convert application error to response dictionary
"""
