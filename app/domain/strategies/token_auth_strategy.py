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

from __future__ import annotations

import base64
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.constants import KsefAuthMode
from app.core.exceptions import AuthenticationError
from app.domain.strategies.auth_strategy_base import AuthStrategyBase


class TokenAuthStrategy(AuthStrategyBase):
    """
    Strategia uwierzytelnienia tokenem KSeF.

    Buduje payload do POST /auth/ksef-token:
    {
        "challenge": "...",
        "contextIdentifier": {"type": "Nip", "value": "..."},
        "encryptedToken": "base64(...)",

        # opcjonalnie
        "authorizationPolicy": {...}
    }

    encryptedToken to RSA-OAEP(SHA-256) z ciągu:
        {tokenKSeF}|{timestampMs}
    """

    def __init__(
        self,
        *,
        token_value: str,
        public_key_pem: str | bytes | None = None,
        public_key_der: bytes | None = None,
        certificate_pem: str | bytes | None = None,
        certificate_der: bytes | None = None,
    ) -> None:
        self.token_value = token_value
        self.public_key = self._load_public_key(
            public_key_pem=public_key_pem,
            public_key_der=public_key_der,
            certificate_pem=certificate_pem,
            certificate_der=certificate_der,
        )

    def get_auth_mode(self) -> str:
        return KsefAuthMode.TOKEN.value

    def build_auth_init_payload(
        self,
        *,
        challenge: str,
        context_identifier_type: str,
        context_identifier_value: str,
        authorization_policy: dict[str, Any] | None = None,
        challenge_timestamp_ms: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not challenge:
            raise AuthenticationError("Missing challenge for token authentication")
        if not context_identifier_type or not context_identifier_value:
            raise AuthenticationError(
                "Missing context identifier for token authentication"
            )
        if not self.token_value:
            raise AuthenticationError("Missing KSeF token value")
        if challenge_timestamp_ms is None:
            raise AuthenticationError(
                "Missing challenge_timestamp_ms for token authentication"
            )

        encrypted_token = self.encrypt_token_with_timestamp(
            token_value=self.token_value,
            challenge_timestamp_ms=challenge_timestamp_ms,
        )

        payload: dict[str, Any] = {
            "challenge": challenge,
            "contextIdentifier": {
                "type": context_identifier_type,
                "value": context_identifier_value,
            },
            "encryptedToken": encrypted_token,
        }

        if authorization_policy:
            payload["authorizationPolicy"] = authorization_policy

        return payload

    def encrypt_token_with_timestamp(
        self,
        *,
        token_value: str,
        challenge_timestamp_ms: int,
    ) -> str:
        plaintext = f"{token_value}|{challenge_timestamp_ms}".encode("utf-8")

        encrypted = self.public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return base64.b64encode(encrypted).decode("ascii")

    @staticmethod
    def build_authorization_policy(
        *,
        ip4_addresses: list[str] | None = None,
        ip4_masks: list[str] | None = None,
        ip4_ranges: list[str] | None = None,
    ) -> dict[str, Any]:
        allowed_ips: dict[str, Any] = {}

        if ip4_addresses:
            allowed_ips["ip4Addresses"] = ip4_addresses
        if ip4_masks:
            allowed_ips["ip4Masks"] = ip4_masks
        if ip4_ranges:
            allowed_ips["ip4Ranges"] = ip4_ranges

        if not allowed_ips:
            return {}

        return {"allowedIps": allowed_ips}

    @staticmethod
    def _load_public_key(
        *,
        public_key_pem: str | bytes | None,
        public_key_der: bytes | None,
        certificate_pem: str | bytes | None,
        certificate_der: bytes | None,
    ) -> rsa.RSAPublicKey:
        provided = [
            public_key_pem is not None,
            public_key_der is not None,
            certificate_pem is not None,
            certificate_der is not None,
        ]
        if sum(provided) != 1:
            raise AuthenticationError(
                "Provide exactly one public key source: public_key_pem, public_key_der, "
                "certificate_pem, or certificate_der"
            )

        key_obj: Any

        if public_key_pem is not None:
            pem_bytes = (
                public_key_pem.encode("utf-8")
                if isinstance(public_key_pem, str)
                else public_key_pem
            )
            key_obj = serialization.load_pem_public_key(pem_bytes)
        elif public_key_der is not None:
            key_obj = serialization.load_der_public_key(public_key_der)
        elif certificate_pem is not None:
            pem_bytes = (
                certificate_pem.encode("utf-8")
                if isinstance(certificate_pem, str)
                else certificate_pem
            )
            cert = x509.load_pem_x509_certificate(pem_bytes)
            key_obj = cert.public_key()
        else:
            cert = x509.load_der_x509_certificate(certificate_der)  # type: ignore[arg-type]
            key_obj = cert.public_key()

        if not isinstance(key_obj, rsa.RSAPublicKey):
            raise AuthenticationError("KSeF public key must be RSA")

        return key_obj
