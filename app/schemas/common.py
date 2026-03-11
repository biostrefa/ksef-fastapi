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
