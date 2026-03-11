"""
Hash and checksum utilities.

This module provides:
- Hash generation functions
- Checksum calculation
- Data integrity verification
- Cryptographic hash helpers

Functions:
    sha256_hex(content: bytes) -> str: Generate SHA-256 hash in hex format
    sha256_base64(content: bytes) -> str: Generate SHA-256 hash in base64 format
    base64_encode(content: bytes) -> str: Encode bytes to base64 string
    base64_decode(content: str) -> bytes: Decode base64 string to bytes
"""

from __future__ import annotations

import base64
import hashlib
import hmac


def sha256_hex(content: bytes) -> str:
    """
    Return SHA-256 digest as lowercase hexadecimal string.
    """
    return hashlib.sha256(content).hexdigest()


def sha256_base64(content: bytes) -> str:
    """
    Return SHA-256 digest as standard base64-encoded string.
    """
    digest = hashlib.sha256(content).digest()
    return base64.b64encode(digest).decode("ascii")


def base64_encode(content: bytes) -> str:
    """
    Encode bytes to standard base64 ASCII string.
    """
    return base64.b64encode(content).decode("ascii")


def base64_decode(content: str) -> bytes:
    """
    Decode standard base64 string into bytes.

    Raises:
        ValueError: when input is not valid base64.
    """
    try:
        return base64.b64decode(content, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 input.") from exc


def sha256_hex_text(content: str, encoding: str = "utf-8") -> str:
    """
    Return SHA-256 hex digest for text input.
    """
    return sha256_hex(content.encode(encoding))


def sha256_base64_text(content: str, encoding: str = "utf-8") -> str:
    """
    Return SHA-256 base64 digest for text input.
    """
    return sha256_base64(content.encode(encoding))


def verify_sha256_hex(content: bytes, expected_hex: str) -> bool:
    """
    Verify bytes against expected SHA-256 hex digest using constant-time comparison.
    """
    actual = sha256_hex(content)
    expected = expected_hex.strip().lower()
    return hmac.compare_digest(actual, expected)


def verify_sha256_base64(content: bytes, expected_base64: str) -> bool:
    """
    Verify bytes against expected SHA-256 base64 digest using constant-time comparison.
    """
    actual = sha256_base64(content)
    expected = expected_base64.strip()
    return hmac.compare_digest(actual, expected)


def md5_hex(content: bytes) -> str:
    """
    Return MD5 hex digest.

    Use only for non-security purposes such as compatibility checks.
    """
    return hashlib.md5(content).hexdigest()


def file_sha256_hex(path: str) -> str:
    """
    Compute SHA-256 hex digest of a file.
    """
    hasher = hashlib.sha256()

    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def file_sha256_base64(path: str) -> str:
    """
    Compute SHA-256 base64 digest of a file.
    """
    hasher = hashlib.sha256()

    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            hasher.update(chunk)

    return base64.b64encode(hasher.digest()).decode("ascii")
