"""
Session repository.

This module provides:
- Session CRUD operations
- Session storage and retrieval
- Session state management
- Session query operations

Classes:
    SessionRepository: Session data access layer

Methods:
    save(session: KsefSession) -> None: Save session
    get_by_reference(reference_number: str) -> KsefSession | None: Get session by reference number
    get_open_session_for_company(company_id: str) -> KsefSession | None: Get open session for company
    list_by_company(company_id: str) -> list[KsefSession]: List sessions for company
    update_status(reference_number: str, status: str) -> None: Update session status
    close(reference_number: str, closed_at: datetime) -> None: Close session
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import KsefEnvironment, KsefSessionStatus, KsefSessionType
from app.domain.models.session import KsefSession, SessionStatusSnapshot
from app.infrastructure.persistence.models.session_model import SessionModel


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _to_domain(row: SessionModel) -> KsefSession:
        return KsefSession(
            id=row.id,
            company_id=row.company_id,
            environment=row.environment,
            session_type=row.session_type,
            reference_number=row.reference_number,
            status=row.status,
            opened_at=row.opened_at,
            closed_at=row.closed_at,
            last_checked_at=row.last_checked_at,
            last_error_code=row.last_error_code,
            last_error_message=row.last_error_message,
            upo_reference_number=row.upo_reference_number,
        )

    async def save(self, session: KsefSession) -> KsefSession:
        stmt = select(SessionModel).where(
            SessionModel.reference_number == session.reference_number
        )
        existing = await self.db.scalar(stmt)

        if existing:
            existing.status = session.status
            existing.opened_at = session.opened_at
            existing.closed_at = session.closed_at
            existing.last_checked_at = session.last_checked_at
            existing.last_error_code = session.last_error_code
            existing.last_error_message = session.last_error_message
            existing.upo_reference_number = session.upo_reference_number

        else:
            existing = SessionModel(
                id=session.id,
                company_id=session.company_id,
                environment=session.environment.value,
                session_type=session.session_type.value,
                reference_number=session.reference_number,
                status=session.status.value,
                opened_at=session.opened_at,
                closed_at=session.closed_at,
                last_checked_at=session.last_checked_at,
                last_error_code=session.last_error_code,
                last_error_message=session.last_error_message,
                upo_reference_number=session.upo_reference_number,
            )
            self.db.add(existing)

        await self.db.commit()
        await self.db.refresh(existing)
        return self._to_domain(existing)

    async def get_by_reference(self, reference_number: str) -> KsefSession | None:
        stmt = select(SessionModel).where(
            SessionModel.reference_number == reference_number
        )
        row = await self.db.scalar(stmt)
        return self._to_domain(row) if row else None

    async def get_open_session_for_company(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
        session_type: KsefSessionType,
    ) -> KsefSession | None:
        stmt = (
            select(SessionModel)
            .where(
                SessionModel.company_id == company_id,
                SessionModel.environment == environment.value,
                SessionModel.session_type == session_type.value,
                SessionModel.status == KsefSessionStatus.OPEN.value,
            )
            .order_by(SessionModel.created_at.desc())
        )
        row = await self.db.scalar(stmt)
        return self._to_domain(row) if row else None

    async def list_by_company(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> list[KsefSession]:
        stmt = (
            select(SessionModel)
            .where(
                SessionModel.company_id == company_id,
                SessionModel.environment == environment.value,
            )
            .order_by(SessionModel.created_at.desc())
        )
        rows = (await self.db.scalars(stmt)).all()
        return [self._to_domain(row) for row in rows]

    async def close(
        self,
        *,
        reference_number: str,
        status,
        closed_at,
    ) -> KsefSession:
        stmt = select(SessionModel).where(
            SessionModel.reference_number == reference_number
        )
        row = await self.db.scalar(stmt)
        if not row:
            raise ValueError(f"Session not found: {reference_number}")

        row.status = status.value if hasattr(status, "value") else str(status)
        row.closed_at = closed_at

        await self.db.commit()
        await self.db.refresh(row)
        return self._to_domain(row)

    async def update_status_snapshot(
        self,
        reference_number: str,
        snapshot: SessionStatusSnapshot,
    ) -> KsefSession:
        stmt = select(SessionModel).where(
            SessionModel.reference_number == reference_number
        )
        row = await self.db.scalar(stmt)
        if not row:
            raise ValueError(f"Session not found: {reference_number}")

        row.status = (
            snapshot.status.value
            if hasattr(snapshot.status, "value")
            else str(snapshot.status)
        )
        row.last_checked_at = snapshot.last_checked_at
        row.last_error_code = snapshot.last_error_code
        row.last_error_message = snapshot.last_error_message
        row.upo_reference_number = getattr(snapshot, "upo_reference_number", None)

        await self.db.commit()
        await self.db.refresh(row)
        return self._to_domain(row)
