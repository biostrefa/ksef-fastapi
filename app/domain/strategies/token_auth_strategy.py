"""
KSeF token authentication strategy.

This module provides:
- Token-based authentication
- KSeF token handling
- Token lifecycle management
- Token refresh logic

Classes:
    TokenAuthStrategy(AuthStrategyBase): Token-based authentication strategy

Methods:
    __init__(token_value: str): Initialize with token value
    build_redeem_payload(challenge: str) -> dict: Build token redemption payload from challenge
    get_auth_mode() -> str: Get authentication mode identifier
"""
