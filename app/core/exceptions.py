from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

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
    KsefApiError: KSeF API error exception
    KsefTransportError: KSeF transport error exception
    KsefBusinessError: KSeF business error exception
    SessionNotFoundError: Session not found error exception
    InvoiceNotFoundError: Invoice not found error exception
    RepositoryError: Repository error exception

Functions:
    app_error_to_http_status(exc: AppError) -> int: Convert application error to HTTP status code
    app_error_to_response(exc: AppError) -> dict: Convert application error to response dictionary
"""


@dataclass(slots=True)
class AppError(Exception):
    """
    Base application exception.

    Attributes:
        message: Human-readable error message.
        error_code: Stable machine-readable error code.
        details: Optional structured details for logs/API responses.
    """

    message: str
    error_code: str = "app_error"
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)


@dataclass(slots=True)
class ValidationError(AppError):
    """
    Raised when request or domain validation fails.
    """

    error_code: str = "validation_error"


@dataclass(slots=True)
class AuthenticationError(AppError):
    """
    Raised when authentication fails or auth context is invalid.
    """

    error_code: str = "authentication_error"

    def __post_init__(self) -> None:
        # Call parent __post_init__ manually to avoid MRO issues
        self.message = self.message
        Exception.__init__(self, self.message)


@dataclass(slots=True)
class AuthorizationError(AppError):
    """
    Raised when operation is not allowed for current actor/context.
    """

    error_code: str = "authorization_error"

    def __post_init__(self) -> None:
        # Call parent __post_init__ manually to avoid MRO issues
        self.message = self.message
        Exception.__init__(self, self.message)


@dataclass(slots=True)
class KsefApiError(AppError):
    """
    Base exception for KSeF-related failures.

    Attributes:
        ksef_code: Optional code returned by KSeF.
        http_status: Optional upstream HTTP status returned by KSeF.
        reference_number: Optional KSeF session/invoice reference number.
    """

    ksef_code: str | None = None
    http_status: int | None = None
    reference_number: str | None = None
    error_code: str = "ksef_api_error"

    def __post_init__(self) -> None:
        if self.ksef_code is not None:
            self.details.setdefault("ksef_code", self.ksef_code)
        if self.http_status is not None:
            self.details.setdefault("upstream_http_status", self.http_status)
        if self.reference_number is not None:
            self.details.setdefault("reference_number", self.reference_number)
        # Call parent __post_init__ manually to avoid MRO issues
        self.message = self.message
        Exception.__init__(self, self.message)


@dataclass(slots=True)
class KsefTransportError(KsefApiError):
    """
    Raised for transport-level KSeF failures:
    timeout, DNS, TLS, connection reset, malformed upstream response, etc.
    """

    error_code: str = "ksef_transport_error"


@dataclass(slots=True)
class KsefBusinessError(KsefApiError):
    """
    Raised when KSeF rejects a business operation or returns business validation errors.
    """

    error_code: str = "ksef_business_error"


@dataclass(slots=True)
class SessionNotFoundError(AppError):
    """
    Raised when local session record does not exist.
    """

    error_code: str = "session_not_found"


@dataclass(slots=True)
class InvoiceNotFoundError(AppError):
    """
    Raised when local invoice submission record does not exist.
    """

    error_code: str = "invoice_not_found"


@dataclass(slots=True)
class RepositoryError(AppError):
    """
    Raised when persistence/repository operation fails.
    """

    error_code: str = "repository_error"


def app_error_to_http_status(exc: AppError) -> int:
    """
    Convert application exception to HTTP status code.
    """
    if isinstance(exc, ValidationError):
        return HTTPStatus.UNPROCESSABLE_ENTITY

    if isinstance(exc, AuthenticationError):
        return HTTPStatus.UNAUTHORIZED

    if isinstance(exc, AuthorizationError):
        return HTTPStatus.FORBIDDEN

    if isinstance(exc, SessionNotFoundError):
        return HTTPStatus.NOT_FOUND

    if isinstance(exc, InvoiceNotFoundError):
        return HTTPStatus.NOT_FOUND

    if isinstance(exc, RepositoryError):
        return HTTPStatus.INTERNAL_SERVER_ERROR

    if isinstance(exc, KsefTransportError):
        return HTTPStatus.BAD_GATEWAY

    if isinstance(exc, KsefBusinessError):
        return HTTPStatus.UNPROCESSABLE_ENTITY

    if isinstance(exc, KsefApiError):
        return HTTPStatus.BAD_GATEWAY

    return HTTPStatus.INTERNAL_SERVER_ERROR


def app_error_to_response(exc: AppError) -> dict[str, Any]:
    """
    Convert application exception to normalized API response dictionary.
    """
    return {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "details": exc.details or {},
        }
    }
