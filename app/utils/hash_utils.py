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
