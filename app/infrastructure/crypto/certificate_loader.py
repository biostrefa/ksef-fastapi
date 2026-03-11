"""
Certificate loader.

This module provides:
- Certificate loading functionality
- Key material handling
- Certificate validation
- Secure certificate storage

Classes:
    CertificateLoader: Certificate and key loading service

Methods:
    load_certificate() -> bytes: Load certificate file
    load_private_key() -> bytes: Load private key file
    load_pkcs12_bundle() -> bytes: Load PKCS12 bundle
"""
