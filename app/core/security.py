from __future__ import annotations
import base64
import hashlib
import hmac
import re
from collections.abc import Mapping
from typing import Any

"""
Security utilities and helpers.

This module provides security-related functionality including:
- Data masking and sanitization
- Secret protection
- Token handling
- Certificate validation
- Input sanitization
"""


try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
except ImportError:  # pragma: no cover
    x509 = None
    hashes = None


SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authentication_token",
    "api_key",
    "private_key",
    "signature",
    "certificate",
    "authorization",
    "x-api-key",
}

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
XML_TAG_TEMPLATE = r"(<{tag}\b[^>]*>)(.*?)(</{tag}>)"


def mask_sensitive_value(value: str | None) -> str:
    """
    Mask a sensitive value for safe logging or API responses.

    Examples:
        None -> "***"
        "abc" -> "***"
        "1234567890" -> "12***90"
    """
    if not value:
        return "***"

    if len(value) <= 6:
        return "***"

    return f"{value[:2]}***{value[-2:]}"


def is_sensitive_key(key: str) -> bool:
    """
    Return True if the provided key name likely contains secret data.
    """
    normalized = key.strip().lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS


def sanitize_mapping(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Recursively sanitize mapping values by masking sensitive keys.
    """
    if not data:
        return {}

    sanitized: dict[str, Any] = {}

    for key, value in data.items():
        if is_sensitive_key(key):
            sanitized[key] = (
                mask_sensitive_value(value) if isinstance(value, str) else "***"
            )
            continue

        if isinstance(value, Mapping):
            sanitized[key] = sanitize_mapping(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_mapping(item) if isinstance(item, Mapping) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def sanitize_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    """
    Sanitize HTTP headers for safe logging.
    """
    if not headers:
        return {}

    return {
        key: mask_sensitive_value(value) if is_sensitive_key(key) else value
        for key, value in headers.items()
    }


def normalize_bearer_token(value: str | None) -> str | None:
    """
    Remove optional 'Bearer ' prefix and surrounding whitespace.
    """
    if value is None:
        return None

    normalized = value.strip()
    if normalized.lower().startswith("bearer "):
        return normalized[7:].strip()

    return normalized or None


def hash_token(token: str, *, salt: str | None = None) -> str:
    """
    Return SHA-256 hash of token, optionally salted.

    Useful for storing token fingerprints instead of raw secrets.
    """
    material = token if salt is None else f"{salt}:{token}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def constant_time_compare(left: str, right: str) -> bool:
    """
    Compare two strings in constant time.
    """
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def verify_webhook_signature(
    payload: bytes,
    provided_signature: str,
    secret: str,
    *,
    algorithm: str = "sha256",
    prefix: str | None = None,
) -> bool:
    """
    Verify HMAC webhook signature.

    Supported signature formats:
    - raw hex digest
    - prefixed form, e.g. 'sha256=<hex>' when prefix='sha256='
    """
    if not provided_signature or not secret:
        return False

    digestmod = getattr(hashlib, algorithm, None)
    if digestmod is None:
        raise ValueError(f"Unsupported HMAC algorithm: {algorithm}")

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        digestmod=digestmod,
    ).hexdigest()

    candidate = provided_signature.strip()
    if prefix and candidate.startswith(prefix):
        candidate = candidate[len(prefix) :].strip()

    return hmac.compare_digest(candidate, expected)


def sanitize_text_input(value: str | None, *, max_length: int | None = None) -> str:
    """
    Strip dangerous control characters and normalize surrounding whitespace.
    """
    if value is None:
        return ""

    sanitized = CONTROL_CHARS_RE.sub("", value).strip()

    if max_length is not None:
        sanitized = sanitized[:max_length]

    return sanitized


def sanitize_filename(filename: str, *, replacement: str = "_") -> str:
    """
    Replace unsafe filename characters with a safe replacement.
    """
    safe = sanitize_text_input(filename, max_length=255)
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]', replacement, safe)
    safe = re.sub(r"\s+", " ", safe).strip(" .")

    return safe or "file"


def redact_xml_tags(xml_text: str, tag_names: list[str]) -> str:
    """
    Redact content of selected XML tags.

    Example:
        redact_xml_tags("<Token>abc</Token>", ["Token"])
        -> "<Token>***</Token>"
    """
    redacted = xml_text

    for tag in tag_names:
        pattern = XML_TAG_TEMPLATE.format(tag=re.escape(tag))
        redacted = re.sub(
            pattern,
            r"\1***\3",
            redacted,
            flags=re.IGNORECASE | re.DOTALL,
        )

    return redacted


def ensure_base64(value: str) -> bool:
    """
    Return True if value looks like valid base64 payload.
    """
    try:
        base64.b64decode(value, validate=True)
        return True
    except Exception:
        return False


def certificate_sha256_fingerprint(certificate_pem: str | bytes) -> str:
    """
    Return SHA-256 fingerprint of a PEM certificate.

    Requires the 'cryptography' package.
    """
    if x509 is None or hashes is None:
        raise RuntimeError(
            "cryptography package is required for certificate fingerprint operations"
        )

    cert_bytes = (
        certificate_pem.encode("utf-8")
        if isinstance(certificate_pem, str)
        else certificate_pem
    )
    cert = x509.load_pem_x509_certificate(cert_bytes)
    return cert.fingerprint(hashes.SHA256()).hex()


def validate_certificate_fingerprint(
    certificate_pem: str | bytes,
    expected_fingerprint_hex: str,
) -> bool:
    """
    Validate certificate SHA-256 fingerprint against expected hex value.
    """
    actual = certificate_sha256_fingerprint(certificate_pem)
    normalized_expected = expected_fingerprint_hex.lower().replace(":", "").strip()
    normalized_actual = actual.lower().replace(":", "").strip()
    return hmac.compare_digest(normalized_actual, normalized_expected)


def build_safe_error_context(**kwargs: Any) -> dict[str, Any]:
    """
    Build sanitized structured context for logs or error responses.
    """
    return sanitize_mapping(kwargs)
