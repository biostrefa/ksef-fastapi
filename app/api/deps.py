"""
Dependency injection for services and repositories.

This module provides:
- FastAPI dependency functions
- Service instance injection
- Repository instance injection
- Database session management

Functions:
    get_db_session() -> AsyncSession: Get database session
    get_token_repository() -> TokenRepository: Get token repository instance
    get_session_repository() -> SessionRepository: Get session repository instance
    get_invoice_repository() -> InvoiceRepository: Get invoice repository instance
    get_ksef_http_client() -> KsefHttpClient: Get KSEF HTTP client instance
    get_encryption_service() -> EncryptionService: Get encryption service instance
    get_auth_service() -> AuthService: Get authentication service instance
    get_session_service() -> SessionService: Get session service instance
    get_invoice_service() -> InvoiceService: Get invoice service instance
    get_status_service() -> StatusService: Get status service instance

Dependency injection for services and repositories.

This module provides:
- FastAPI dependency functions
- Service instance injection
- Repository instance injection
- Database session management

Functions:
    get_db_session() -> AsyncSession: Get database session
    get_token_repository() -> TokenRepository: Get token repository instance
    get_session_repository() -> SessionRepository: Get session repository instance
    get_invoice_repository() -> InvoiceRepository: Get invoice repository instance
    get_ksef_http_client() -> KsefHttpClient: Get KSeF HTTP client instance
    get_encryption_service() -> EncryptionService: Get encryption service instance
    get_auth_service() -> AuthService: Get authentication service instance
    get_session_service() -> SessionService: Get session service instance
    get_invoice_service() -> InvoiceService: Get invoice service instance
    get_status_service() -> StatusService: Get status service instance
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.domain.builders.invoice_fa3_builder import InvoiceFa3Builder
from app.domain.mappers.invoice_mapper import InvoiceMapper
from app.domain.mappers.ksef_response_mapper import KsefResponseMapper
from app.domain.strategies.auth_strategy_base import AuthStrategyBase
from app.domain.strategies.token_auth_strategy import TokenAuthStrategy
from app.domain.strategies.xades_auth_strategy import XadesAuthStrategy
from app.domain.validators.invoice_validator import InvoiceValidator
from app.infrastructure.crypto.certificate_loader import CertificateLoader
from app.infrastructure.crypto.encryption_service import EncryptionService
from app.infrastructure.crypto.xades_signer import XadesSigner
from app.infrastructure.http.ksef_http_client import KsefHttpClient
from app.infrastructure.persistence.db import AsyncSessionFactory
from app.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)
from app.infrastructure.persistence.repositories.invoice_repository import (
    InvoiceRepository,
)
from app.infrastructure.persistence.repositories.session_repository import (
    SessionRepository,
)
from app.infrastructure.persistence.repositories.token_repository import (
    TokenRepository,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.invoice_service import InvoiceService
from app.services.session_service import SessionService
from app.services.status_service import StatusService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(lambda: get_db_session())]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a SQLAlchemy async database session.

    This should be used as the base dependency for repository providers.
    """
    async with AsyncSessionFactory() as session:
        yield session


def get_certificate_loader(settings: SettingsDep) -> CertificateLoader:
    """
    Create certificate/key material loader used by auth and encryption layers.
    """
    return CertificateLoader(
        mf_public_encryption_cert_path=settings.ksef_mf_public_encryption_cert_path,
        private_key_path=settings.ksef_private_key_path,
        private_key_password=settings.ksef_private_key_password,
        xades_signing_cert_path=settings.ksef_xades_signing_cert_path,
    )


def get_token_repository(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenRepository:
    """
    Create token repository bound to the current DB session.
    """
    return TokenRepository(db_session)


def get_session_repository(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionRepository:
    """
    Create session repository bound to the current DB session.
    """
    return SessionRepository(db_session)


def get_invoice_repository(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvoiceRepository:
    """
    Create invoice repository bound to the current DB session.
    """
    return InvoiceRepository(db_session)


def get_audit_log_repository(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuditLogRepository:
    """
    Create audit log repository bound to the current DB session.
    """
    return AuditLogRepository(db_session)


@lru_cache(maxsize=1)
def get_invoice_builder() -> InvoiceFa3Builder:
    """
    Create FA(3) invoice XML builder.

    Cached because it is stateless.
    """
    return InvoiceFa3Builder()


@lru_cache(maxsize=1)
def get_invoice_validator() -> InvoiceValidator:
    """
    Create invoice validator.

    Cached because it is stateless.
    """
    return InvoiceValidator()


@lru_cache(maxsize=1)
def get_invoice_mapper() -> InvoiceMapper:
    """
    Create invoice mapper.

    Cached because it is stateless.
    """
    return InvoiceMapper()


@lru_cache(maxsize=1)
def get_ksef_response_mapper() -> KsefResponseMapper:
    """
    Create KSeF response mapper.

    Cached because it is stateless.
    """
    return KsefResponseMapper()


def get_ksef_http_client(settings: SettingsDep) -> KsefHttpClient:
    """
    Create low-level KSeF HTTP client.
    """
    return KsefHttpClient(
        base_url=settings.ksef_base_url,
        timeout_seconds=settings.ksef_timeout_seconds,
        default_headers={"User-Agent": settings.ksef_user_agent},
    )


def get_encryption_service(
    settings: SettingsDep,
    certificate_loader: Annotated[CertificateLoader, Depends(get_certificate_loader)],
) -> EncryptionService:
    """
    Create encryption service used for KSeF session/invoice payload preparation.
    """
    return EncryptionService(
        certificate_loader=certificate_loader,
        encryption_key_size=settings.ksef_encryption_key_size,
        hash_algorithm=settings.ksef_hash_algorithm,
    )


def get_token_auth_strategy(
    settings: SettingsDep,
    certificate_loader: Annotated[CertificateLoader, Depends(get_certificate_loader)],
) -> AuthStrategyBase:
    """
    Create token-based auth strategy.
    """
    return TokenAuthStrategy(
        token_value=settings.ksef_token_value or "",
        certificate_pem=certificate_loader.load_certificate(),
    )


def get_xades_auth_strategy(
    settings: SettingsDep,
    certificate_loader: Annotated[CertificateLoader, Depends(get_certificate_loader)],
) -> AuthStrategyBase:
    """
    Create XAdES-based auth strategy.
    """
    xades_signer = XadesSigner(
        certificate_loader=certificate_loader,
        canonicalization_method=settings.ksef_xades_canonicalization_method,
        digest_method=settings.ksef_xades_digest_method,
        signature_method=settings.ksef_xades_signature_method,
    )
    return XadesAuthStrategy(
        signer=xades_signer.sign_xml,
        namespace_uri="http://ksef.mf.gov.pl/auth/token/2.0",
    )


def get_audit_service(
    audit_log_repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> AuditService:
    """
    Create audit service.
    """
    return AuditService(audit_log_repository=audit_log_repository)


def get_auth_service(
    settings: SettingsDep,
    token_repository: Annotated[TokenRepository, Depends(get_token_repository)],
    ksef_http_client: Annotated[KsefHttpClient, Depends(get_ksef_http_client)],
    token_auth_strategy: Annotated[AuthStrategyBase, Depends(get_token_auth_strategy)],
    xades_auth_strategy: Annotated[AuthStrategyBase, Depends(get_xades_auth_strategy)],
) -> AuthService:
    """
    Create authentication service.
    """
    return AuthService(
        settings=settings,
        token_repository=token_repository,
        ksef_http_client=ksef_http_client,
        token_auth_strategy=token_auth_strategy,
        xades_strategy=xades_auth_strategy,
    )


def get_session_service(
    settings: SettingsDep,
    token_repository: Annotated[TokenRepository, Depends(get_token_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    ksef_http_client: Annotated[KsefHttpClient, Depends(get_ksef_http_client)],
    encryption_service: Annotated[EncryptionService, Depends(get_encryption_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> SessionService:
    """
    Create session service.
    """
    return SessionService(
        settings=settings,
        token_repository=token_repository,
        session_repository=session_repository,
        ksef_http_client=ksef_http_client,
        encryption_service=encryption_service,
        audit_service=audit_service,
    )


def get_invoice_service(
    settings: SettingsDep,
    token_repository: Annotated[TokenRepository, Depends(get_token_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    invoice_repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    ksef_http_client: Annotated[KsefHttpClient, Depends(get_ksef_http_client)],
    encryption_service: Annotated[EncryptionService, Depends(get_encryption_service)],
    invoice_builder: Annotated[InvoiceFa3Builder, Depends(get_invoice_builder)],
    invoice_validator: Annotated[InvoiceValidator, Depends(get_invoice_validator)],
    invoice_mapper: Annotated[InvoiceMapper, Depends(get_invoice_mapper)],
    ksef_response_mapper: Annotated[KsefResponseMapper, Depends(get_ksef_response_mapper)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> InvoiceService:
    """
    Create invoice service.
    """
    return InvoiceService(
        settings=settings,
        token_repository=token_repository,
        session_repository=session_repository,
        invoice_repository=invoice_repository,
        ksef_http_client=ksef_http_client,
        encryption_service=encryption_service,
        invoice_builder=invoice_builder,
        invoice_validator=invoice_validator,
        invoice_mapper=invoice_mapper,
        ksef_response_mapper=ksef_response_mapper,
        audit_service=audit_service,
    )


def get_status_service(
    settings: SettingsDep,
    token_repository: Annotated[TokenRepository, Depends(get_token_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    invoice_repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    ksef_http_client: Annotated[KsefHttpClient, Depends(get_ksef_http_client)],
    ksef_response_mapper: Annotated[KsefResponseMapper, Depends(get_ksef_response_mapper)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StatusService:
    """
    Create status service.
    """
    return StatusService(
        settings=settings,
        token_repository=token_repository,
        session_repository=session_repository,
        invoice_repository=invoice_repository,
        ksef_http_client=ksef_http_client,
        ksef_response_mapper=ksef_response_mapper,
        audit_service=audit_service,
    )
