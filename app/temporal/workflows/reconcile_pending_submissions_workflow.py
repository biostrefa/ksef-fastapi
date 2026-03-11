"""
Pending submissions reconciliation workflow.

This module provides:
- Automatic status reconciliation
- Pending submission polling
- Error recovery and retry logic
- Reconciliation result reporting
"""

from __future__ import annotations

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from app.temporal.models.common import (
    DEFAULT_ACTIVITY_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
)
from app.temporal.models.reconciliation_models import (
    ReconcilePendingInput,
    ReconcilePendingResult,
)


@workflow.defn
class ReconcilePendingSubmissionsWorkflow:
    """
    Skeleton reconciliation workflow.

    It already loads pending submissions and marks them as reconciled if they are
    obviously terminal in local state. Real KSeF re-fetch logic can be added later.
    """

    def __init__(self) -> None:
        self._current_step = "created"

    @workflow.run
    async def run(self, input: ReconcilePendingInput) -> ReconcilePendingResult:
        self._current_step = "load_pending_submissions"
        pending = await workflow.execute_activity(
            "load_pending_submissions_for_reconciliation",
            {
                "company_id": input.company_id,
                "environment": input.environment,
                "limit": input.limit,
            },
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        scanned = len(pending)
        updated = 0
        failed = 0

        for item in pending:
            try:
                # Placeholder policy:
                # if local row already has terminal status, mark as reconciled.
                if item.get("status") in {"accepted", "failed"}:
                    await workflow.execute_activity(
                        "mark_submission_reconciled",
                        {
                            "submission_id": item["submission_id"],
                            "final_status": item["status"],
                        },
                        start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                    )
                    updated += 1
            except Exception:
                failed += 1

        self._current_step = "completed"
        return ReconcilePendingResult(
            scanned=scanned,
            updated=updated,
            failed=failed,
        )

    @workflow.query
    def current_step(self) -> str:
        return self._current_step
