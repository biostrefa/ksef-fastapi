"""
Common Temporal models and utilities.

This module provides:
- Base temporal model classes
- Common data structures
- Model validation utilities
- Shared temporal constants
"""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel
from temporalio.common import RetryPolicy


SHORT_ACTIVITY_TIMEOUT = timedelta(seconds=30)
MEDIUM_ACTIVITY_TIMEOUT = timedelta(minutes=2)
LONG_ACTIVITY_TIMEOUT = timedelta(minutes=5)
POLL_INTERVAL = timedelta(seconds=10)

DEFAULT_ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
    non_retryable_error_types=[
        "BusinessRuleViolation",
        "InvoiceNotFound",
        "AuthenticationFailed",
        "AuthenticationTimeout",
        "UnsupportedAuthMode",
        "InvalidPersistenceInput",
    ],
)


class WorkflowErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool = False
