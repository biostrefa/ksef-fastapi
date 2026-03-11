"""
Base HTTP client.

This module provides:
- Common HTTP client functionality
- Retry logic and timeout handling
- Header management
- Connection pooling

Classes:
    BaseHttpClient: Base HTTP client with common functionality

Methods:
    __init__(base_url: str, timeout_seconds: int): Initialize HTTP client
    get(path: str, headers: dict | None = None, params: dict | None = None) -> dict: Send GET request
    post(path: str, headers: dict | None = None, json: dict | None = None, data: bytes | str | None = None) -> dict: Send POST request
    _handle_response(response) -> dict: Handle HTTP response
    _build_headers(headers: dict | None = None) -> dict: Build request headers
"""
