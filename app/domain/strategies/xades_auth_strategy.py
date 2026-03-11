"""
XAdES signature authentication strategy.

This module provides:
- Digital signature authentication
- XAdES signature handling
- Certificate-based auth
- Signature validation logic

Classes:
    XadesAuthStrategy(AuthStrategyBase): XAdES signature-based authentication strategy

Methods:
    __init__(certificate_loader: CertificateLoader): Initialize with certificate loader
    build_redeem_payload(challenge: str) -> dict: Build token redemption payload from challenge
    sign_challenge(challenge: str) -> str: Sign challenge using XAdES signature
    get_auth_mode() -> str: Get authentication mode identifier
"""
