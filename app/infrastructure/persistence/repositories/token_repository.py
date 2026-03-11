"""
Token repository.

This module provides:
- Token CRUD operations
- Token storage and retrieval
- Token lifecycle management
- Token query operations

Classes:
    TokenRepository: Token data access layer

Methods:
    save(company_id: str, tokens: AuthTokens) -> None: Save tokens for company
    get_by_company(company_id: str) -> AuthTokens | None: Get tokens by company
    delete_by_company(company_id: str) -> None: Delete tokens for company
    update(company_id: str, tokens: AuthTokens) -> None: Update tokens for company
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import KsefEnvironment
from app.domain.models.auth import AuthTokens
from app.infrastructure.persistence.models.token_model import TokenModel


class TokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
        tokens: AuthTokens,
    ) -> AuthTokens:
        stmt = select(TokenModel).where(
            TokenModel.company_id == company_id,
            TokenModel.environment == environment.value,
        )
        existing = await self.db.scalar(stmt)

        if existing:
            existing.access_token = tokens.access_token
            existing.refresh_token = tokens.refresh_token
            existing.access_token_expires_at = tokens.access_token_expires_at
            existing.refresh_token_expires_at = tokens.refresh_token_expires_at
        else:
            existing = TokenModel(
                company_id=company_id,
                environment=environment.value,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                access_token_expires_at=tokens.access_token_expires_at,
                refresh_token_expires_at=tokens.refresh_token_expires_at,
            )
            self.db.add(existing)

        await self.db.commit()
        await self.db.refresh(existing)

        return AuthTokens(
            access_token=existing.access_token,
            refresh_token=existing.refresh_token,
            access_token_expires_at=existing.access_token_expires_at,
            refresh_token_expires_at=existing.refresh_token_expires_at,
        )

    async def get_by_company(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> AuthTokens | None:
        stmt = select(TokenModel).where(
            TokenModel.company_id == company_id,
            TokenModel.environment == environment.value,
        )
        row = await self.db.scalar(stmt)
        if not row:
            return None

        return AuthTokens(
            access_token=row.access_token,
            refresh_token=row.refresh_token,
            access_token_expires_at=row.access_token_expires_at,
            refresh_token_expires_at=row.refresh_token_expires_at,
        )

    async def delete_by_company(
        self,
        *,
        company_id: UUID,
        environment: KsefEnvironment,
    ) -> None:
        stmt = select(TokenModel).where(
            TokenModel.company_id == company_id,
            TokenModel.environment == environment.value,
        )
        row = await self.db.scalar(stmt)
        if row:
            await self.db.delete(row)
            await self.db.commit()
