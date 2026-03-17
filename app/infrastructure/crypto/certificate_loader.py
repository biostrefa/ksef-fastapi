"""
Certificate loader with explicit KSeF semantics.

This module provides:
- MF public encryption certificate loading
- XAdES signing certificate loading
- Private key loading for XAdES/signing flows
- PKCS#12 bundle loading
- Certificate/private key validation helpers

KSeF roles:
- mf_public_encryption_cert_path:
    MF public certificate used to encrypt the session symmetric key
    for KSeF session opening.
- xades_signing_cert_path:
    Your certificate used for XAdES signing/authentication.
- private_key_path:
    Private key paired with your XAdES signing certificate.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.core.exceptions import ValidationError

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
except ImportError:  # pragma: no cover
    x509 = None
    hashes = None
    serialization = None
    pkcs12 = None
    rsa = None
    ec = None


class CertificateLoader:
    """
    Service responsible for loading certificate and key material from the filesystem.

    Explicit KSeF semantics:
    - MF public encryption certificate is separate from your signing material.
    - XAdES signing certificate is expected to match the configured private key.
    """

    def __init__(
        self,
        mf_public_encryption_cert_path: str | None = None,
        private_key_path: str | None = None,
        private_key_password: str | None = None,
        xades_signing_cert_path: str | None = None,
        pkcs12_bundle_path: str | None = None,
        pkcs12_password: str | None = None,
        # Backward-compatible alias; ignored if mf_public_encryption_cert_path is set.
        public_cert_path: str | None = None,
    ) -> None:
        effective_mf_cert_path = mf_public_encryption_cert_path

        self.mf_public_encryption_cert_path = (
            Path(effective_mf_cert_path).expanduser() if effective_mf_cert_path else None
        )
        self.private_key_path = Path(private_key_path).expanduser() if private_key_path else None
        self.private_key_password = private_key_password
        self.xades_signing_cert_path = Path(xades_signing_cert_path).expanduser() if xades_signing_cert_path else None
        self.pkcs12_bundle_path = Path(pkcs12_bundle_path).expanduser() if pkcs12_bundle_path else None
        self.pkcs12_password = pkcs12_password

    #
    # Raw loaders
    #

    def load_mf_encryption_certificate(self, path: str | Path | None = None) -> bytes:
        """
        Load MF public encryption certificate bytes.
        """
        cert_path = Path(path).expanduser() if path else self.mf_public_encryption_cert_path
        return self._read_required_file(
            cert_path,
            field_name="mf_public_encryption_cert_path",
        )

    def load_certificate(self, path: str | Path | None = None) -> bytes:
        """
        Backward-compatible alias for MF public encryption certificate loader.
        """
        return self.load_mf_encryption_certificate(path)

    def load_xades_signing_certificate(self, path: str | Path | None = None) -> bytes:
        """
        Load XAdES signing certificate bytes.
        """
        cert_path = Path(path).expanduser() if path else self.xades_signing_cert_path
        return self._read_required_file(
            cert_path,
            field_name="xades_signing_cert_path",
        )

    def load_private_key(self, path: str | Path | None = None) -> bytes:
        """
        Load XAdES/signing private key bytes.
        """
        key_path = Path(path).expanduser() if path else self.private_key_path
        self._validate_private_key_permissions(key_path)
        return self._read_required_file(key_path, field_name="private_key_path")

    def load_pkcs12_bundle(self, path: str | Path | None = None) -> bytes:
        """
        Load PKCS#12 / PFX bundle bytes.
        """
        bundle_path = Path(path).expanduser() if path else self.pkcs12_bundle_path
        return self._read_required_file(bundle_path, field_name="pkcs12_bundle_path")

    #
    # Password helpers
    #

    def get_private_key_password_bytes(self) -> bytes | None:
        """
        Return private key password encoded as UTF-8 bytes, if configured.
        """
        if self.private_key_password is None:
            return None
        return self.private_key_password.encode("utf-8")

    def get_pkcs12_password_bytes(self) -> bytes | None:
        """
        Return PKCS#12 password encoded as UTF-8 bytes, if configured.
        """
        if self.pkcs12_password is None:
            return None
        return self.pkcs12_password.encode("utf-8")

    #
    # Parsed loaders
    #

    def load_parsed_mf_encryption_certificate(
        self,
        path: str | Path | None = None,
    ) -> Any:
        """
        Load and parse MF public encryption certificate as x509.Certificate.
        """
        self._ensure_core_crypto_available()
        raw = self.load_mf_encryption_certificate(path)
        return self._parse_certificate(raw)

    def load_parsed_certificate(self, path: str | Path | None = None) -> Any:
        """
        Backward-compatible alias for parsed MF public encryption certificate loader.
        """
        return self.load_parsed_mf_encryption_certificate(path)

    def load_parsed_xades_signing_certificate(
        self,
        path: str | Path | None = None,
    ) -> Any:
        """
        Load and parse XAdES signing certificate as x509.Certificate.
        """
        self._ensure_core_crypto_available()
        raw = self.load_xades_signing_certificate(path)
        return self._parse_certificate(raw)

    def load_parsed_private_key(
        self,
        path: str | Path | None = None,
        password: str | bytes | None = None,
    ) -> Any:
        """
        Load and parse private key using configured password if needed.
        """
        self._ensure_core_crypto_available()

        raw = self.load_private_key(path)
        parsed_password: bytes | None

        if isinstance(password, str):
            parsed_password = password.encode("utf-8")
        elif isinstance(password, bytes):
            parsed_password = password
        else:
            parsed_password = self.get_private_key_password_bytes()

        pem_error: Exception | None = None

        try:
            return serialization.load_pem_private_key(raw, password=parsed_password)
        except Exception as exc:
            pem_error = exc

        try:
            return serialization.load_der_private_key(raw, password=parsed_password)
        except Exception as der_exc:
            raise ValidationError(
                message="Unable to parse private key file.",
                details={
                    "private_key_path": str(Path(path).expanduser()) if path else self._path_str(self.private_key_path),
                    "pem_error": str(pem_error) if pem_error else None,
                    "der_error": str(der_exc),
                },
            ) from der_exc

    def load_parsed_pkcs12_bundle(
        self,
        path: str | Path | None = None,
        password: str | bytes | None = None,
    ) -> tuple[Any, Any, list[Any]]:
        """
        Load and parse PKCS#12 / PFX bundle.

        Returns:
            (private_key, certificate, additional_certificates)
        """
        self._ensure_pkcs12_available()

        raw = self.load_pkcs12_bundle(path)

        parsed_password: bytes | None
        if isinstance(password, str):
            parsed_password = password.encode("utf-8")
        elif isinstance(password, bytes):
            parsed_password = password
        else:
            parsed_password = self.get_pkcs12_password_bytes()

        try:
            key, cert, additional = pkcs12.load_key_and_certificates(
                raw,
                password=parsed_password,
            )
        except Exception as exc:
            raise ValidationError(
                message="Unable to parse PKCS#12 bundle.",
                details={
                    "pkcs12_bundle_path": str(Path(path).expanduser())
                    if path
                    else self._path_str(self.pkcs12_bundle_path),
                    "error": str(exc),
                },
            ) from exc

        if cert is None:
            raise ValidationError(
                message="PKCS#12 bundle does not contain a certificate.",
                details={
                    "pkcs12_bundle_path": str(Path(path).expanduser())
                    if path
                    else self._path_str(self.pkcs12_bundle_path),
                },
            )

        return key, cert, list(additional or [])

    #
    # Validation helpers
    #

    def get_certificate_sha256_fingerprint(
        self,
        path: str | Path | None = None,
        *,
        use_xades_cert: bool = False,
    ) -> str:
        """
        Return SHA-256 fingerprint of the selected certificate as lowercase hex.
        """
        self._ensure_core_crypto_available()

        cert = (
            self.load_parsed_xades_signing_certificate(path)
            if use_xades_cert
            else self.load_parsed_mf_encryption_certificate(path)
        )
        return cert.fingerprint(hashes.SHA256()).hex()

    def validate_xades_certificate_matches_private_key(self) -> bool:
        """
        Check whether configured XAdES signing certificate matches the configured private key.
        """
        self._ensure_core_crypto_available()

        certificate = self.load_parsed_xades_signing_certificate()
        private_key = self.load_parsed_private_key()

        cert_public_key = certificate.public_key()
        private_public_key = private_key.public_key()

        cert_public_bytes = cert_public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        private_public_bytes = private_public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return cert_public_bytes == private_public_bytes

    def get_private_key_type(self) -> str:
        """
        Return a simple string representing the private key type.
        """
        private_key = self.load_parsed_private_key()

        if rsa is not None and isinstance(private_key, rsa.RSAPrivateKey):
            return "RSA"
        if ec is not None and isinstance(private_key, ec.EllipticCurvePrivateKey):
            return "EC"

        return type(private_key).__name__

    def ensure_required_material_for_encryption(self) -> None:
        """
        Validate that KSeF encryption-related material is available and usable.

        Requirements:
        - MF encryption certificate exists
        - certificate is parseable
        - certificate contains RSA public key
        """
        self._ensure_core_crypto_available()

        certificate = self.load_parsed_mf_encryption_certificate()
        public_key = certificate.public_key()

        if rsa is None or not isinstance(public_key, rsa.RSAPublicKey):
            raise ValidationError(
                message="MF public encryption certificate must contain an RSA public key.",
                details={"actual_key_type": type(public_key).__name__},
            )

    def ensure_required_material_for_xades(self) -> None:
        """
        Validate that XAdES-related material is available and consistent.

        Requirements:
        - XAdES signing certificate exists and is parseable
        - private key exists and is parseable
        - certificate matches the private key
        """
        self._ensure_core_crypto_available()

        self.load_parsed_xades_signing_certificate()
        self.load_parsed_private_key()

        if not self.validate_xades_certificate_matches_private_key():
            raise ValidationError(
                message="XAdES signing certificate does not match the configured private key.",
                details={
                    "xades_signing_cert_path": self._path_str(self.xades_signing_cert_path),
                    "private_key_path": self._path_str(self.private_key_path),
                },
            )

    #
    # Internal helpers
    #

    def _read_required_file(self, path: Path | None, *, field_name: str) -> bytes:
        if path is None:
            raise ValidationError(
                message=f"Missing required certificate configuration: '{field_name}'.",
                details={"field": field_name},
            )

        if not path.exists():
            raise ValidationError(
                message=f"Configured file does not exist for '{field_name}'.",
                details={"field": field_name, "path": str(path)},
            )

        if not path.is_file():
            raise ValidationError(
                message=f"Configured path for '{field_name}' is not a file.",
                details={"field": field_name, "path": str(path)},
            )

        try:
            return path.read_bytes()
        except OSError as exc:
            raise ValidationError(
                message=f"Unable to read file for '{field_name}'.",
                details={
                    "field": field_name,
                    "path": str(path),
                    "error": str(exc),
                },
            ) from exc

    def _validate_private_key_permissions(self, path: Path | None) -> None:
        """
        Perform a basic permission sanity check for the private key file.

        Enforced only on POSIX systems.
        """
        if os.name != "posix":
            return

        if path is None or not path.exists():
            return

        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            return

        if mode & 0o077:
            raise ValidationError(
                message="Private key file permissions are too broad.",
                details={
                    "field": "private_key_path",
                    "path": str(path),
                    "recommended_mode": "0600",
                    "actual_mode_octal": oct(mode),
                },
            )

    def _parse_certificate(self, raw: bytes) -> Any:
        """
        Parse certificate bytes as PEM or DER X.509 certificate.
        """
        self._ensure_core_crypto_available()

        pem_error: Exception | None = None

        try:
            return x509.load_pem_x509_certificate(raw)
        except Exception as exc:
            pem_error = exc

        try:
            return x509.load_der_x509_certificate(raw)
        except Exception as der_exc:
            raise ValidationError(
                message="Unable to parse certificate file.",
                details={
                    "pem_error": str(pem_error) if pem_error else None,
                    "der_error": str(der_exc),
                },
            ) from der_exc

    @staticmethod
    def _path_str(path: Path | None) -> str | None:
        return str(path) if path is not None else None

    @staticmethod
    def _ensure_core_crypto_available() -> None:
        if x509 is None or hashes is None or serialization is None:
            raise RuntimeError("The 'cryptography' package is required for certificate operations.")

    @staticmethod
    def _ensure_pkcs12_available() -> None:
        if pkcs12 is None:
            raise RuntimeError("The 'cryptography' package with PKCS#12 support is required for PKCS#12 operations.")
