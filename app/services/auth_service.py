"""
Authentication service.

This module provides:
- Challenge generation and verification
- Token redemption and refresh
- Authentication lifecycle management
- Auth context handling

Classes:
    AuthService: Authentication service

Public Methods:
    start_challenge(company_id: str) -> AuthChallenge: Start authentication challenge
    redeem(company_id: str) -> AuthTokens: Redeem authentication tokens
    refresh(company_id: str) -> AuthTokens: Refresh authentication tokens
    get_auth_context(company_id: str) -> AuthContext: Get authentication context
    revoke(company_id: str) -> None: Revoke authentication

Private Methods:
    _select_strategy() -> AuthStrategyBase: Select appropriate authentication strategy
    _load_existing_tokens(company_id: str) -> AuthTokens | None: Load existing tokens from storage
    _save_tokens(company_id: str, tokens: AuthTokens) -> None: Save tokens to storage
"""
