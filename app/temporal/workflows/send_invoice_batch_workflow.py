"""
Batch invoice submission workflow.

This module provides:
- Batch invoice processing workflow
- Bulk invoice validation
- Batch session management
- Batch status tracking and reconciliation
"""

from __future__ import annotations

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from app.temporal.models.invoice_models import (
    SendInvoiceBatchInput,
    SendInvoiceBatchResult,
)


@workflow.defn
class SendInvoiceBatchWorkflow:
    """
    Placeholder workflow kept intentionally in the spec, so the architecture
    stays complete. Real batch flow should be implemented after online flow is stable.
    """

    def __init__(self) -> None:
        self._current_step = "created"

    @workflow.run
    async def run(self, input: SendInvoiceBatchInput) -> SendInvoiceBatchResult:
        self._current_step = "not_implemented"
        raise ApplicationError(
            "Batch workflow is not implemented in this skeleton yet",
            non_retryable=True,
        )

    @workflow.query
    def current_step(self) -> str:
        return self._current_step
