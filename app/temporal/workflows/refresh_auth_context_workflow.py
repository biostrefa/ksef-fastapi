"""
Authentication context refresh workflow.

This module provides:
- Token refresh orchestration
- Authentication context renewal
- Expiration handling
- Auth context validation
"""

from __future__ import annotations

from temporalio import workflow

from app.temporal.models.auth_models import RefreshAuthInput, RefreshAuthResult
from app.temporal.models.common import (
    DEFAULT_ACTIVITY_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
)


@workflow.defn
class RefreshAuthContextWorkflow:
    def __init__(self) -> None:
        self._current_step = "created"

    @workflow.run
    async def run(self, input: RefreshAuthInput) -> RefreshAuthResult:
        self._current_step = "refresh_auth_context"
        result = await workflow.execute_activity(
            "refresh_auth_context",
            input.auth_context_id,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        self._current_step = "completed"

        return RefreshAuthResult(
            auth_context_id=str(result["auth_context_id"]),
            access_token=str(result["access_token"]),
            expires_at_utc=result.get("expires_at_utc"),
        )

    @workflow.query
    def current_step(self) -> str:
        return self._current_step
