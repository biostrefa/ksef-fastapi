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
