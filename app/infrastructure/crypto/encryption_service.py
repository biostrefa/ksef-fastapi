"""
Encryption service for KSeF 2.x.

This module provides:
- Session encryption material generation
- Symmetric key wrapping with MF public key
- Invoice encryption for interactive session send flow
- SHA-256 hashing and metadata generation
- Local test-only decryption helpers

Important:
- KSeF session opening uses:
    encryption.encryptedSymmetricKey
    encryption.initializationVector
- KSeF invoice send uses:
    invoiceHash
    invoiceSize
    encryptedInvoiceHash
    encryptedInvoiceSize
    encryptedInvoiceContent

This implementation is aligned with KSeF 2.x requirements:
- AES-256-CBC for invoice content
- PKCS#7 padding
- RSAES-OAEP with SHA-256/MGF1 for wrapping the symmetric key
- 32-byte symmetric key
- 16-byte initialization vector
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.exceptions import ValidationError
from app.infrastructure.crypto.certificate_loader import CertificateLoader
from app.utils.hash_utils import sha256_base64


AES_KEY_SIZE_BYTES = 32
AES_BLOCK_SIZE_BYTES = 16
AES_BLOCK_SIZE_BITS = 128


@dataclass(slots=True)
class SessionEncryptionMaterial:
    """
    Local session encryption material used after KSeF session opening.

    This object contains both:
    - API-facing values required by KSeF to open the session
    - local raw values required later to encrypt invoices for that session

    Notes:
    - raw symmetric key and IV must never be logged
    - raw symmetric key should be stored only if strictly necessary
    """

    symmetric_key: bytes = field(repr=False)
    initialization_vector: bytes = field(repr=False)
    encrypted_symmetric_key_base64: str

    key_encryption_algorithm: str = "RSAES-OAEP"
    key_encryption_hash: str = "SHA-256"
    content_encryption_algorithm: str = "AES-256-CBC"
    content_padding: str = "PKCS#7"

    @property
    def initialization_vector_base64(self) -> str:
        return base64.b64encode(self.initialization_vector).decode("ascii")

    @property
    def symmetric_key_base64(self) -> str:
        return base64.b64encode(self.symmetric_key).decode("ascii")

    def to_open_session_encryption_dict(self) -> dict[str, str]:
        """
        Build encryption object for KSeF open session request.
        """
        return {
            "encryptedSymmetricKey": self.encrypted_symmetric_key_base64,
            "initializationVector": self.initialization_vector_base64,
        }

    def to_secure_storage_dict(self) -> dict[str, str]:
        """
        Build local persistence payload for session encryption context.

        This is meant for protected storage only.
        """
        return {
            "symmetric_key_base64": self.symmetric_key_base64,
            "initialization_vector_base64": self.initialization_vector_base64,
            "encrypted_symmetric_key_base64": self.encrypted_symmetric_key_base64,
            "key_encryption_algorithm": self.key_encryption_algorithm,
            "key_encryption_hash": self.key_encryption_hash,
            "content_encryption_algorithm": self.content_encryption_algorithm,
            "content_padding": self.content_padding,
        }

    @classmethod
    def from_secure_storage_dict(
        cls, data: dict[str, Any]
    ) -> "SessionEncryptionMaterial":
        """
        Restore local session encryption material from protected storage.
        """
        try:
            symmetric_key = base64.b64decode(
                data["symmetric_key_base64"], validate=True
            )
            initialization_vector = base64.b64decode(
                data["initialization_vector_base64"],
                validate=True,
            )
            encrypted_symmetric_key_base64 = str(data["encrypted_symmetric_key_base64"])
        except Exception as exc:
            raise ValidationError(
                message="Invalid stored session encryption material.",
                details={"error": str(exc)},
            ) from exc

        return cls(
            symmetric_key=symmetric_key,
            initialization_vector=initialization_vector,
            encrypted_symmetric_key_base64=encrypted_symmetric_key_base64,
            key_encryption_algorithm=str(
                data.get("key_encryption_algorithm", "RSAES-OAEP")
            ),
            key_encryption_hash=str(data.get("key_encryption_hash", "SHA-256")),
            content_encryption_algorithm=str(
                data.get("content_encryption_algorithm", "AES-256-CBC")
            ),
            content_padding=str(data.get("content_padding", "PKCS#7")),
        )


@dataclass(slots=True)
class EncryptedInvoicePayload:
    """
    KSeF invoice send payload content.

    Field names are intentionally close to the KSeF API contract.
    """

    invoice_hash: str
    invoice_size: int
    encrypted_invoice_hash: str
    encrypted_invoice_size: int
    encrypted_invoice_content: str
    offline_mode: bool = False

    def to_send_invoice_request_dict(self) -> dict[str, Any]:
        """
        Build payload for KSeF SendInvoiceRequest.
        """
        return {
            "invoiceHash": self.invoice_hash,
            "invoiceSize": self.invoice_size,
            "encryptedInvoiceHash": self.encrypted_invoice_hash,
            "encryptedInvoiceSize": self.encrypted_invoice_size,
            "encryptedInvoiceContent": self.encrypted_invoice_content,
            "offlineMode": self.offline_mode,
        }


class EncryptionService:
    """
    KSeF 2.x encryption service.

    Assumptions:
    - certificate_loader.load_certificate() returns the MF public certificate
      used for symmetric key wrapping in session opening flow
    - the returned SessionEncryptionMaterial is stored securely and associated
      with a concrete KSeF session reference number
    """

    def __init__(
        self,
        *,
        certificate_loader: CertificateLoader,
        encryption_key_size: int = 256,
        hash_algorithm: str = "SHA-256",
    ) -> None:
        self.certificate_loader = certificate_loader
        self.encryption_key_size = encryption_key_size
        self.hash_algorithm = hash_algorithm.upper().strip()

        if self.encryption_key_size != 256:
            raise ValidationError(
                message="KSeF 2.x requires a 256-bit symmetric key.",
                details={"encryption_key_size": encryption_key_size},
            )

        if self.hash_algorithm != "SHA-256":
            raise ValidationError(
                message="KSeF 2.x requires SHA-256 hashing.",
                details={"hash_algorithm": hash_algorithm},
            )

    def create_session_encryption_material(self) -> SessionEncryptionMaterial:
        """
        Generate session key material and wrap the symmetric key with the MF public key.

        Returns:
            SessionEncryptionMaterial
        """
        symmetric_key = self._generate_symmetric_key()
        initialization_vector = self._generate_initialization_vector()
        encrypted_symmetric_key = self._encrypt_symmetric_key_with_mf_public_key(
            symmetric_key
        )

        return SessionEncryptionMaterial(
            symmetric_key=symmetric_key,
            initialization_vector=initialization_vector,
            encrypted_symmetric_key_base64=base64.b64encode(
                encrypted_symmetric_key
            ).decode("ascii"),
        )

    def build_session_init_payload(
        self,
        *,
        form_code: dict[str, Any] | None = None,
        session_material: SessionEncryptionMaterial | None = None,
    ) -> dict[str, Any]:
        """
        Build KSeF open online session request payload.

        If form_code is provided, the returned payload is ready to send.
        If form_code is omitted, the payload contains only the encryption section.
        """
        material = session_material or self.create_session_encryption_material()

        encryption_payload = material.to_open_session_encryption_dict()
        if form_code is None:
            return {
                "encryption": encryption_payload,
                "_local_session_encryption_material": material.to_secure_storage_dict(),
            }

        return {
            "formCode": form_code,
            "encryption": encryption_payload,
            "_local_session_encryption_material": material.to_secure_storage_dict(),
        }

    def encrypt_invoice_xml(
        self,
        xml_content: str,
        *,
        symmetric_key: bytes,
        initialization_vector: bytes,
        offline_mode: bool = False,
    ) -> EncryptedInvoicePayload:
        """
        Encrypt XML content for KSeF SendInvoiceRequest using AES-256-CBC + PKCS#7.
        """
        plain_bytes = xml_content.encode("utf-8")
        self._validate_symmetric_key(symmetric_key)
        self._validate_initialization_vector(initialization_vector)

        invoice_hash = self.calculate_hash(plain_bytes)
        invoice_size = len(plain_bytes)

        encrypted_bytes = self._encrypt_bytes_cbc_pkcs7(
            content=plain_bytes,
            key=symmetric_key,
            initialization_vector=initialization_vector,
        )

        encrypted_invoice_hash = self.calculate_hash(encrypted_bytes)
        encrypted_invoice_size = len(encrypted_bytes)
        encrypted_invoice_content = base64.b64encode(encrypted_bytes).decode("ascii")

        return EncryptedInvoicePayload(
            invoice_hash=invoice_hash,
            invoice_size=invoice_size,
            encrypted_invoice_hash=encrypted_invoice_hash,
            encrypted_invoice_size=encrypted_invoice_size,
            encrypted_invoice_content=encrypted_invoice_content,
            offline_mode=offline_mode,
        )

    def encrypt_invoice_for_session(
        self,
        xml_content: str,
        session_material: SessionEncryptionMaterial,
        *,
        offline_mode: bool = False,
    ) -> EncryptedInvoicePayload:
        """
        Encrypt XML using previously generated session material.
        """
        return self.encrypt_invoice_xml(
            xml_content,
            symmetric_key=session_material.symmetric_key,
            initialization_vector=session_material.initialization_vector,
            offline_mode=offline_mode,
        )

    def build_send_invoice_request(
        self,
        xml_content: str,
        session_material: SessionEncryptionMaterial,
        *,
        offline_mode: bool = False,
    ) -> dict[str, Any]:
        """
        Convenience helper returning ready-to-send KSeF invoice payload.
        """
        payload = self.encrypt_invoice_for_session(
            xml_content,
            session_material,
            offline_mode=offline_mode,
        )
        return payload.to_send_invoice_request_dict()

    def calculate_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash in Base64 form expected by KSeF.
        """
        return sha256_base64(content)

    def generate_metadata(self, content: bytes) -> dict[str, Any]:
        """
        Generate generic size/hash metadata for content.
        """
        return {
            "size": len(content),
            "sha256Base64": self.calculate_hash(content),
        }

    def decrypt_content(
        self,
        *,
        encrypted_content_base64: str,
        symmetric_key: bytes,
        initialization_vector: bytes,
    ) -> bytes:
        """
        Local test helper only.

        Decrypt AES-256-CBC + PKCS#7 content previously produced by this service.
        """
        self._validate_symmetric_key(symmetric_key)
        self._validate_initialization_vector(initialization_vector)

        try:
            encrypted_bytes = base64.b64decode(encrypted_content_base64, validate=True)
        except Exception as exc:
            raise ValidationError(
                message="Encrypted content is not valid Base64.",
                details={"error": str(exc)},
            ) from exc

        cipher = Cipher(
            algorithms.AES(symmetric_key),
            modes.CBC(initialization_vector),
        )
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(encrypted_bytes) + decryptor.finalize()

        unpadder = sym_padding.PKCS7(AES_BLOCK_SIZE_BITS).unpadder()
        try:
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        except ValueError as exc:
            raise ValidationError(
                message="Invalid PKCS#7 padding or corrupted encrypted payload.",
                details={"error": str(exc)},
            ) from exc

        return plaintext

    def _generate_symmetric_key(self) -> bytes:
        """
        Generate 32-byte AES-256 key.
        """
        return os.urandom(AES_KEY_SIZE_BYTES)

    def _generate_initialization_vector(self) -> bytes:
        """
        Generate 16-byte IV for AES-CBC.
        """
        return os.urandom(AES_BLOCK_SIZE_BYTES)

    def _encrypt_bytes_cbc_pkcs7(
        self,
        *,
        content: bytes,
        key: bytes,
        initialization_vector: bytes,
    ) -> bytes:
        """
        Encrypt bytes with AES-256-CBC and PKCS#7 padding.
        """
        padder = sym_padding.PKCS7(AES_BLOCK_SIZE_BITS).padder()
        padded_content = padder.update(content) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(initialization_vector),
        )
        encryptor = cipher.encryptor()
        return encryptor.update(padded_content) + encryptor.finalize()

    def _encrypt_symmetric_key_with_mf_public_key(self, symmetric_key: bytes) -> bytes:
        """
        Wrap symmetric key using MF public certificate and RSAES-OAEP SHA-256/MGF1.
        """
        public_key = self._load_mf_public_key()

        if not isinstance(public_key, rsa.RSAPublicKey):
            raise ValidationError(
                message="MF encryption certificate does not contain an RSA public key.",
                details={"actual_key_type": type(public_key).__name__},
            )

        return public_key.encrypt(
            symmetric_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def _load_mf_public_key(self) -> rsa.RSAPublicKey:
        """
        Load MF public certificate from CertificateLoader and extract RSA public key.
        """
        certificate_bytes = self.certificate_loader.load_certificate()

        certificate: x509.Certificate
        try:
            certificate = x509.load_pem_x509_certificate(certificate_bytes)
        except ValueError:
            try:
                certificate = x509.load_der_x509_certificate(certificate_bytes)
            except ValueError as exc:
                raise ValidationError(
                    message="Unable to parse MF public certificate.",
                    details={"error": str(exc)},
                ) from exc

        public_key = certificate.public_key()
        return public_key

    @staticmethod
    def restore_session_material(
        stored_data: dict[str, Any],
    ) -> SessionEncryptionMaterial:
        """
        Restore SessionEncryptionMaterial from secure local storage.
        """
        return SessionEncryptionMaterial.from_secure_storage_dict(stored_data)

    @staticmethod
    def export_session_material(
        session_material: SessionEncryptionMaterial,
    ) -> dict[str, str]:
        """
        Export SessionEncryptionMaterial into protected-storage form.
        """
        return session_material.to_secure_storage_dict()

    @staticmethod
    def _validate_symmetric_key(key: bytes) -> None:
        if len(key) != AES_KEY_SIZE_BYTES:
            raise ValidationError(
                message="Invalid symmetric key length. Expected 32 bytes for AES-256.",
                details={"actual_length": len(key)},
            )

    @staticmethod
    def _validate_initialization_vector(initialization_vector: bytes) -> None:
        if len(initialization_vector) != AES_BLOCK_SIZE_BYTES:
            raise ValidationError(
                message="Invalid initialization vector length. Expected 16 bytes.",
                details={"actual_length": len(initialization_vector)},
            )
