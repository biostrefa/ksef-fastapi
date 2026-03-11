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
