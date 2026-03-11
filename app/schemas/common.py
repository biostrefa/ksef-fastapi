"""
Common request/response models.

This module provides:
- Base response models
- Common request models
- Pagination models
- Standard error models

Pydantic Classes:
    OperationResult: Standard operation result with success status and message
        - success: bool: Operation success status
        - message: str | None: Optional message describing the result
    PaginationParams: Pagination parameters for list endpoints
    ErrorResponse: Standard error response model
    ReferenceNumberResponse: Response containing reference number
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )


class OperationResult(ApiModel):
    success: bool = True
    message: str | None = None


class ErrorResponse(ApiModel):
    code: str
    message: str
    details: dict | None = None


class ReferenceNumberResponse(ApiModel):
    reference_number: str


class PaginationParams(ApiModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


class PageMeta(ApiModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PagedResponse(ApiModel, Generic[T]):
    items: list[T]
    meta: PageMeta


class AuditInfo(ApiModel):
    request_id: UUID | None = None
    correlation_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
