"""
Token database model.

This module provides:
- Token table definition
- Auth context storage
- Token metadata fields
- Token relationships

ORM Classes:
    TokenModel(Base): Token database model

Fields:
    id: Primary key
    company_id: Company identifier
    environment: KSeF environment
    access_token: Access token value
    refresh_token: Refresh token value
    expires_at: Token expiration time
    created_at: Record creation time
    updated_at: Record update time
"""
