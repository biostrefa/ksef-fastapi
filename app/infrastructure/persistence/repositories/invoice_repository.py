"""
Invoice repository.

This module provides:
- Invoice CRUD operations
- Invoice status storage
- UPO storage and retrieval
- Invoice query operations

Classes:
    InvoiceRepository: Invoice data access layer

Methods:
    save(submission: InvoiceSubmission) -> None: Save invoice submission
    get_by_id(submission_id: str) -> InvoiceSubmission | None: Get submission by ID
    get_by_ksef_reference(ksef_invoice_reference: str) -> InvoiceSubmission | None: Get submission by KSeF reference
    list_by_company(company_id: str) -> list[InvoiceSubmission]: List submissions for company
    update_status(submission_id: str, status: str) -> None: Update submission status
    save_upo(submission_id: str, upo_content: str) -> None: Save UPO content
    save_error(submission_id: str, error_code: str, error_message: str) -> None: Save error information
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import KsefEnvironment
from app.domain.models.invoice import InvoiceSubmission
from app.infrastructure.persistence.models.invoice_submission_model import (
    InvoiceSubmissionModel,
)


class InvoiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _to_domain(row: InvoiceSubmissionModel) -> InvoiceSubmission:
        return InvoiceSubmission(
            submission_id=row.id,
            company_id=row.company_id,
            session_reference_number=row.session_reference_number,
            local_invoice_number=row.local_invoice_number,
            ksef_invoice_reference=row.ksef_invoice_reference,
            status=row.status,
            xml_hash_sha256=row.xml_hash_sha256,
            upo_content=row.upo_content,
            error_code=row.error_code,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def save(
        self, submission: InvoiceSubmission, *, environment: KsefEnvironment
    ) -> InvoiceSubmission:
        row = InvoiceSubmissionModel(
            id=submission.submission_id,
            company_id=submission.company_id,
            environment=environment.value,
            session_reference_number=submission.session_reference_number,
            local_invoice_number=submission.local_invoice_number,
            ksef_invoice_reference=submission.ksef_invoice_reference,
            status=submission.status.value
            if hasattr(submission.status, "value")
            else str(submission.status),
            xml_hash_sha256=submission.xml_hash_sha256,
            upo_content=submission.upo_content,
            error_code=submission.error_code,
            error_message=submission.error_message,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_domain(row)

    async def get_by_id(self, submission_id: UUID) -> InvoiceSubmission | None:
        row = await self.db.get(InvoiceSubmissionModel, submission_id)
        return self._to_domain(row) if row else None

    async def get_by_ksef_reference(
        self, ksef_invoice_reference: str
    ) -> InvoiceSubmission | None:
        stmt = select(InvoiceSubmissionModel).where(
            InvoiceSubmissionModel.ksef_invoice_reference == ksef_invoice_reference
        )
        row = await self.db.scalar(stmt)
        return self._to_domain(row) if row else None

    async def list_by_company(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> list[InvoiceSubmission]:
        stmt = (
            select(InvoiceSubmissionModel)
            .where(
                InvoiceSubmissionModel.company_id == company_id,
                InvoiceSubmissionModel.environment == environment.value,
            )
            .order_by(InvoiceSubmissionModel.created_at.desc())
        )
        rows = (await self.db.scalars(stmt)).all()
        return [self._to_domain(row) for row in rows]

    async def update_status(
        self,
        *,
        submission_id: UUID,
        status,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> InvoiceSubmission:
        row = await self.db.get(InvoiceSubmissionModel, submission_id)
        if not row:
            raise ValueError(f"Submission not found: {submission_id}")

        row.status = status.value if hasattr(status, "value") else str(status)
        row.error_code = error_code
        row.error_message = error_message

        await self.db.commit()
        await self.db.refresh(row)
        return self._to_domain(row)

    async def save_upo(
        self,
        *,
        submission_id: UUID,
        upo_content: str,
    ) -> InvoiceSubmission:
        row = await self.db.get(InvoiceSubmissionModel, submission_id)
        if not row:
            raise ValueError(f"Submission not found: {submission_id}")

        row.upo_content = upo_content

        await self.db.commit()
        await self.db.refresh(row)
        return self._to_domain(row)
