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
"""
