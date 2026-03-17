"""
Application configuration and environment settings.

This module handles all configuration including:
- Environment variables
- KSeF API endpoints and URLs
- Timeout and retry settings
- Database connections
- Security settings

Settings(BaseSettings)
pola:
app_name
app_env
debug
database_url
ksef_base_url
ksef_timeout_seconds
ksef_auth_mode
ksef_token_value
ksef_client_cert_path
ksef_client_cert_password
ksef_retry_attempts
ksef_poll_interval_seconds

Funkcje
get_settings() -> Settings
singleton / cached settings

"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

from app.core.constants import KsefAuthMode, KsefEnvironment


class Settings(BaseSettings):
    app_name: str = "KSeF FastAPI Integration"
    app_env: str = "development"
    debug: bool = False
    database_url: str
    ksef_base_url: str
    ksef_timeout_seconds: int = 30
    ksef_environment: KsefEnvironment = KsefEnvironment.TEST
    ksef_auth_mode: KsefAuthMode = KsefAuthMode.TOKEN
    ksef_user_agent: str = "ksef-fastapi/1.0"
    ksef_verify_ssl: bool = True
    ksef_token_value: str | None = None
    ksef_token_header_name: str = "KsefToken"
    ksef_client_cert_path: str | None = None
    ksef_client_cert_password: str | None = None
    ksef_retry_attempts: int = 3
    ksef_poll_interval_seconds: float = 2.0
    ksef_context_identifier_type: str = "Nip"
    ksef_context_identifier_value: str | None = None
    ksef_auth_poll_attempts: int = 10
    ksef_auth_poll_interval_seconds: float = 1.0
    ksef_mf_public_encryption_cert_path: str
    ksef_xades_signing_cert_path: str
    ksef_private_key_path: str
    ksef_private_key_password: str | None = None
    ksef_encryption_key_size: int = 256
    ksef_hash_algorithm: str = "SHA-256"
    ksef_xades_canonicalization_method: str = "http://www.w3.org/2001/10/xml-exc-c14n#"
    ksef_xades_digest_method: str = "http://www.w3.org/2001/04/xmlenc#sha256"
    ksef_xades_signature_method: str = "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
