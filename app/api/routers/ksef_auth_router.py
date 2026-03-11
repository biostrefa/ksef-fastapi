"""
KSeF authentication endpoints.

This module provides:
- Internal KSeF authentication endpoints
- Challenge generation and verification
- Token management endpoints
- Authentication context handling

Endpoint Functions:
    start_challenge(...) -> AuthChallengeResponse: Start authentication challenge
    redeem_token(...) -> AuthTokenRedeemResponse: Redeem authentication token
    refresh_access_token(...) -> AuthRefreshResponse: Refresh access token
    get_auth_context(...) -> AuthContextResponse: Get authentication context
    revoke_auth(...) -> OperationResult: Revoke authentication
"""
