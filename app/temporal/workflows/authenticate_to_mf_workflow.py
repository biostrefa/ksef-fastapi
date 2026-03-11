"""
Authentication to MF workflow.

This module provides:
- Complete authentication workflow orchestration
- Challenge generation and verification
- Token redemption and refresh
- Authentication context management
"""

from __future__ import annotations

from dataclasses import asdict

from temporalio import workflow

from app.temporal.models.auth_models import EnsureAuthInput, EnsureAuthResult
from app.temporal.models.common import (
    DEFAULT_ACTIVITY_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
)


@workflow.defn
class AuthenticateToMfWorkflow:
    def __init__(self) -> None:
        self._current_step = "created"
        self._auth_context_id: str | None = None

    @workflow.run
    async def run(self, input: EnsureAuthInput) -> EnsureAuthResult:
        self._current_step = "ensure_auth_context"
        result = await workflow.execute_activity(
            "ensure_auth_context",
            asdict(input),
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        self._auth_context_id = str(result["auth_context_id"])
        self._current_step = "completed"

        return EnsureAuthResult(
            auth_context_id=str(result["auth_context_id"]),
            access_token=str(result["access_token"]),
            refresh_token=result.get("refresh_token"),
            expires_at_utc=result.get("expires_at_utc"),
            session_encryption=result.get("session_encryption"),
        )

    @workflow.query
    def current_step(self) -> str:
        return self._current_step

    @workflow.query
    def auth_context_id(self) -> str | None:
        return self._auth_context_id
