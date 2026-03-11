"""
Encryption service.

This module provides:
- Payload encryption
- SHA-256 hashing
- Key management
- Cryptographic operations

Classes:
    EncryptionService: Encryption and cryptographic operations service

Methods:
    encrypt_xml(xml_content: str) -> EncryptedInvoicePayload: Encrypt XML content
    calculate_hash(content: bytes) -> str: Calculate SHA-256 hash
    generate_metadata(content: bytes) -> dict: Generate encryption metadata
    decrypt_content(encrypted_content: bytes) -> bytes: Decrypt encrypted content

Helper Methods (for local testing only):
    _generate_symmetric_key() -> bytes: Generate symmetric key
    _encrypt_bytes(content: bytes, key: bytes) -> bytes: Encrypt bytes with key
"""

from __future__ import annotations

import base64
import os
from hashlib import sha256

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.domain.models.invoice import EncryptedInvoicePayload


class EncryptionService:
    """
    Szyfrowanie payloadu faktury po stronie aplikacji.

    Uwaga:
    - ten serwis buduje spójny wewnętrzny model szyfrowania,
    - przed produkcją trzeba dopasować metadane i ewentualne opakowanie klucza
      do dokładnego kontraktu KSeF dla otwierania sesji i wysyłki faktury.
    """

    def __init__(self, *, aad: bytes | None = None) -> None:
        self.aad = aad

    def encrypt_xml(self, xml_content: str) -> EncryptedInvoicePayload:
        plain_bytes = xml_content.encode("utf-8")

        invoice_hash_sha256_base64 = self._sha256_base64(plain_bytes)
        invoice_size = len(plain_bytes)

        key = self._generate_symmetric_key()
        nonce = os.urandom(12)

        aesgcm = AESGCM(key)
        encrypted_bytes = aesgcm.encrypt(nonce, plain_bytes, self.aad)

        encrypted_invoice_hash_sha256_base64 = self._sha256_base64(encrypted_bytes)
        encrypted_invoice_size = len(encrypted_bytes)

        return EncryptedInvoicePayload(
            invoice_hash_sha256_base64=invoice_hash_sha256_base64,
            invoice_size=invoice_size,
            encrypted_invoice_hash_sha256_base64=encrypted_invoice_hash_sha256_base64,
            encrypted_invoice_size=encrypted_invoice_size,
            encrypted_content_base64=base64.b64encode(encrypted_bytes).decode("ascii"),
            encryption_method="AES-256-GCM",
            checksum_algorithm="SHA-256",
            metadata={
                "nonce_base64": base64.b64encode(nonce).decode("ascii"),
                "key_base64": base64.b64encode(key).decode("ascii"),
                "aad_base64": base64.b64encode(self.aad).decode("ascii")
                if self.aad
                else None,
                "plaintext_encoding": "utf-8",
            },
        )

    @staticmethod
    def calculate_hash(content: bytes) -> str:
        return EncryptionService._sha256_base64(content)

    @staticmethod
    def generate_metadata(content: bytes) -> dict:
        return {
            "size": len(content),
            "sha256_base64": EncryptionService._sha256_base64(content),
        }

    @staticmethod
    def decrypt_content(
        *,
        encrypted_content_base64: str,
        nonce_base64: str,
        key_base64: str,
        aad_base64: str | None = None,
    ) -> bytes:
        encrypted_bytes = base64.b64decode(encrypted_content_base64)
        nonce = base64.b64decode(nonce_base64)
        key = base64.b64decode(key_base64)
        aad = base64.b64decode(aad_base64) if aad_base64 else None

        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, encrypted_bytes, aad)

    @staticmethod
    def _generate_symmetric_key() -> bytes:
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def _sha256_base64(content: bytes) -> str:
        return base64.b64encode(sha256(content).digest()).decode("ascii")
