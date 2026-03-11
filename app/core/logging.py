"""
Logging configuration and utilities.

This module provides centralized logging configuration including:
- Structured logging setup
- Log formatting
- Log levels management
- Sensitive data filtering
- Performance logging

Funkcje
configure_logging() -> None
get_logger(name: str) -> Logger
mask_sensitive_value(value: str | None) -> str
"""
