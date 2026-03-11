"""
Unified error response models.

This module provides:
- Standard error response models
- Validation error models
- KSeF error models
- Error detail models
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: Optional[str] = Field(None, description="Field name where error occurred")
    message: str = Field(description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ValidationError(BaseModel):
    """Validation error response."""

    error: str = Field(default="validation_error", description="Error type")
    message: str = Field(description="General error message")
    details: List[ErrorDetail] = Field(
        default_factory=list, description="List of validation errors"
    )


class NotFoundError(BaseModel):
    """Resource not found error response."""

    error: str = Field(default="not_found", description="Error type")
    message: str = Field(description="Error message")
    resource: Optional[str] = Field(
        None, description="Resource type that was not found"
    )


class UnauthorizedError(BaseModel):
    """Unauthorized access error response."""

    error: str = Field(default="unauthorized", description="Error type")
    message: str = Field(description="Error message")


class ForbiddenError(BaseModel):
    """Forbidden access error response."""

    error: str = Field(default="forbidden", description="Error type")
    message: str = Field(description="Error message")


class ConflictError(BaseModel):
    """Conflict error response."""

    error: str = Field(default="conflict", description="Error type")
    message: str = Field(description="Error message")
    resource: Optional[str] = Field(None, description="Resource type with conflict")


class RateLimitError(BaseModel):
    """Rate limit exceeded error response."""

    error: str = Field(default="rate_limit_exceeded", description="Error type")
    message: str = Field(description="Error message")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


class InternalServerError(BaseModel):
    """Internal server error response."""

    error: str = Field(default="internal_server_error", description="Error type")
    message: str = Field(
        default="An unexpected error occurred", description="Error message"
    )
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class ServiceUnavailableError(BaseModel):
    """Service unavailable error response."""

    error: str = Field(default="service_unavailable", description="Error type")
    message: str = Field(description="Error message")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


class KSeFError(BaseModel):
    """KSeF specific error response."""

    error: str = Field(default="ksef_error", description="Error type")
    message: str = Field(description="Error message")
    ksef_code: Optional[str] = Field(None, description="KSeF error code")
    ksef_message: Optional[str] = Field(None, description="Original KSeF error message")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context"
    )


class BadRequestError(BaseModel):
    """Bad request error response."""

    error: str = Field(default="bad_request", description="Error type")
    message: str = Field(description="Error message")
    details: Optional[List[ErrorDetail]] = Field(
        None, description="List of error details"
    )


# Union type for all possible error responses
ErrorResponse = (
    ValidationError
    | NotFoundError
    | UnauthorizedError
    | ForbiddenError
    | ConflictError
    | RateLimitError
    | InternalServerError
    | ServiceUnavailableError
    | KSeFError
    | BadRequestError
)
