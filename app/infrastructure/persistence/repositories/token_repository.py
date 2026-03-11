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
