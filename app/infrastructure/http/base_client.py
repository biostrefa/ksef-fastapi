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

from __future__ import annotations

from typing import Any

import httpx

from app.core.exceptions import KsefApiError, KsefTransportError


class BaseHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: int = 30,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.default_headers = default_headers or {}

    def _build_headers(
        self,
        *,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        accept: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, str]:
        result = dict(self.default_headers)

        if accept:
            result["Accept"] = accept
        if content_type:
            result["Content-Type"] = content_type
        if bearer_token:
            result["Authorization"] = f"Bearer {bearer_token}"

        if headers:
            result.update(headers)

        return result

    async def _request(
        self,
        *,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        content: bytes | str | None = None,
        accept: str = "application/json",
        content_type: str | None = "application/json",
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._build_headers(
                        headers=headers,
                        bearer_token=bearer_token,
                        accept=accept,
                        content_type=content_type,
                    ),
                    params=params,
                    json=json,
                    content=content,
                )
        except httpx.TimeoutException as exc:
            raise KsefTransportError(
                "KSeF request timed out",
                details={"method": method, "path": path},
            ) from exc
        except httpx.HTTPError as exc:
            raise KsefTransportError(
                "KSeF transport error",
                details={"method": method, "path": path, "error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise self._to_api_error(response=response, method=method, path=path)

        return response

    async def get_json(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._request(
            method="GET",
            path=path,
            headers=headers,
            bearer_token=bearer_token,
            params=params,
            accept="application/json",
            content_type=None,
        )
        return self._parse_json_response(response)

    async def post_json(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._request(
            method="POST",
            path=path,
            headers=headers,
            bearer_token=bearer_token,
            params=params,
            json=json,
            accept="application/json",
            content_type="application/json",
        )
        return self._parse_json_response(response)

    async def post_xml(
        self,
        path: str,
        *,
        xml_content: str,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._request(
            method="POST",
            path=path,
            headers=headers,
            bearer_token=bearer_token,
            params=params,
            content=xml_content,
            accept="application/json",
            content_type="application/xml",
        )
        return self._parse_json_response(response)

    async def post_no_content(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> None:
        response = await self._request(
            method="POST",
            path=path,
            headers=headers,
            bearer_token=bearer_token,
            params=params,
            json=json,
            accept="application/json",
            content_type="application/json",
        )
        if response.status_code not in (200, 202, 204):
            raise self._to_api_error(response=response, method="POST", path=path)

    async def delete_no_content(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        response = await self._request(
            method="DELETE",
            path=path,
            headers=headers,
            bearer_token=bearer_token,
            params=params,
            accept="application/json",
            content_type=None,
        )
        if response.status_code not in (200, 202, 204):
            raise self._to_api_error(response=response, method="DELETE", path=path)

    async def get_text(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        bearer_token: str | None = None,
        params: dict[str, Any] | None = None,
        accept: str = "application/xml",
    ) -> tuple[str, dict[str, str]]:
        response = await self._request(
            method="GET",
            path=path,
            headers=headers,
            bearer_token=bearer_token,
            params=params,
            accept=accept,
            content_type=None,
        )
        return response.text, dict(response.headers)

    @staticmethod
    def _parse_json_response(response: httpx.Response) -> dict[str, Any]:
        if response.status_code == 204 or not response.content:
            return {}

        try:
            payload = response.json()
        except ValueError as exc:
            raise KsefApiError(
                "Invalid JSON response from KSeF",
                details={
                    "status_code": response.status_code,
                    "body": response.text[:2000],
                },
            ) from exc

        if not isinstance(payload, dict):
            raise KsefApiError(
                "Unexpected JSON response shape from KSeF",
                details={
                    "status_code": response.status_code,
                    "payload_type": type(payload).__name__,
                },
            )

        return payload

    @staticmethod
    def _to_api_error(
        *,
        response: httpx.Response,
        method: str,
        path: str,
    ) -> KsefApiError:
        details: dict[str, Any] = {
            "method": method,
            "path": path,
            "status_code": response.status_code,
        }

        content_type = response.headers.get("content-type", "")

        if (
            "application/json" in content_type
            or "application/problem+json" in content_type
        ):
            try:
                details["response"] = response.json()
            except ValueError:
                details["response_text"] = response.text[:4000]
        else:
            details["response_text"] = response.text[:4000]

        return KsefApiError("KSeF API returned an error", details=details)
