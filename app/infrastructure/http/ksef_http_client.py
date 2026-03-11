"""
KSeF HTTP client.

This module provides:
- KSeF API integration
- Request/response handling
- KSeF-specific error handling

Classes:
    KsefHttpClient(BaseHttpClient): KSeF-specific HTTP client

Auth Methods:
    get_challenge() -> dict: Get authentication challenge
    redeem_token(payload: dict) -> dict: Redeem authentication token
    refresh_token(payload: dict) -> dict: Refresh authentication token

Session Methods:
    open_online_session(access_token: str, payload: dict) -> dict: Open online session
    open_batch_session(access_token: str, payload: dict) -> dict: Open batch session
    close_session(access_token: str, reference_number: str) -> dict: Close session
    get_session_status(access_token: str, reference_number: str) -> dict: Get session status

Invoice Methods:
    send_invoice(access_token: str, reference_number: str, payload: dict) -> dict: Send invoice
    get_invoice_status(access_token: str, reference_number: str, invoice_reference: str) -> dict: Get invoice status

UPO Methods:
    download_session_upo(access_token: str, reference_number: str) -> dict: Download session UPO
    download_invoice_upo(access_token: str, invoice_reference: str) -> dict: Download invoice UPO
"""

from __future__ import annotations

from typing import Any

from app.infrastructure.http.base_client import BaseHttpClient


class KsefHttpClient(BaseHttpClient):
    """
    Cienki klient HTTP pod aktualne endpointy KSeF 2.x.
    Zwraca dane w możliwie ujednoliconym formacie snake_case,
    żeby wyższe warstwy nie musiały znać szczegółów wire-formatu MF.
    """

    @staticmethod
    def _pick_token_node(
        payload: dict[str, Any], key: str
    ) -> tuple[str | None, str | None]:
        node = payload.get(key) or {}
        if not isinstance(node, dict):
            return None, None
        return node.get("token"), node.get("validUntil")

    @staticmethod
    def _normalize_auth_init(payload: dict[str, Any]) -> dict[str, Any]:
        auth_token = payload.get("authenticationToken") or {}
        return {
            "reference_number": payload.get("referenceNumber"),
            "authentication_token": auth_token.get("token"),
            "authentication_token_valid_until": auth_token.get("validUntil"),
        }

    @staticmethod
    def _normalize_auth_status(payload: dict[str, Any]) -> dict[str, Any]:
        status = payload.get("status") or {}
        return {
            "authentication_method": payload.get("authenticationMethod"),
            "status_code": status.get("code"),
            "status_description": status.get("description"),
            "status_details": status.get("details") or [],
            "start_date": payload.get("startDate"),
        }

    @classmethod
    def _normalize_auth_tokens(cls, payload: dict[str, Any]) -> dict[str, Any]:
        access_token, access_valid_until = cls._pick_token_node(payload, "accessToken")
        refresh_token, refresh_valid_until = cls._pick_token_node(
            payload, "refreshToken"
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_token_expires_at": access_valid_until,
            "refresh_token_expires_at": refresh_valid_until,
        }

    @staticmethod
    def _normalize_open_session(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "reference_number": payload.get("referenceNumber"),
            "valid_until": payload.get("validUntil"),
        }

    @staticmethod
    def _normalize_send_invoice(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "reference_number": payload.get("referenceNumber"),
        }

    @staticmethod
    def _normalize_session_status(payload: dict[str, Any]) -> dict[str, Any]:
        status = payload.get("status") or {}
        upo = payload.get("upo") or {}
        pages = upo.get("pages") or []

        first_page = pages[0] if pages else None
        return {
            "status_code": status.get("code"),
            "status_description": status.get("description"),
            "status_details": status.get("details") or [],
            "date_created": payload.get("dateCreated"),
            "date_updated": payload.get("dateUpdated"),
            "invoice_count": payload.get("invoiceCount"),
            "successful_invoice_count": payload.get("successfulInvoiceCount"),
            "failed_invoice_count": payload.get("failedInvoiceCount"),
            "upo_pages": pages,
            "upo_available": bool(pages),
            "upo_reference_number": first_page.get("referenceNumber")
            if first_page
            else None,
            "upo_download_url": first_page.get("downloadUrl") if first_page else None,
            "upo_download_url_expiration_date": (
                first_page.get("downloadUrlExpirationDate") if first_page else None
            ),
        }

    @staticmethod
    def _normalize_invoice_status(payload: dict[str, Any]) -> dict[str, Any]:
        status = payload.get("status") or {}
        return {
            "ordinal_number": payload.get("ordinalNumber"),
            "reference_number": payload.get("referenceNumber"),
            "invoicing_date": payload.get("invoicingDate"),
            "status_code": status.get("code"),
            "status_description": status.get("description"),
            "status_details": status.get("details") or [],
        }

    async def get_challenge(self) -> dict[str, Any]:
        payload = await self.post_json("/auth/challenge", json=None)
        return {
            "challenge": payload.get("challenge"),
            "timestamp": payload.get("timestamp"),
            "timestamp_ms": payload.get("timestampMs"),
            "client_ip": payload.get("clientIp"),
        }

    async def init_auth_ksef_token(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = await self.post_json("/auth/ksef-token", json=payload)
        return self._normalize_auth_init(raw)

    async def init_auth_xades_signature(
        self,
        *,
        signed_xml: str,
        verify_certificate_chain: bool | None = None,
    ) -> dict[str, Any]:
        params = {}
        if verify_certificate_chain is not None:
            params["verifyCertificateChain"] = str(verify_certificate_chain).lower()

        raw = await self.post_xml(
            "/auth/xades-signature",
            xml_content=signed_xml,
            params=params or None,
        )
        return self._normalize_auth_init(raw)

    async def get_auth_status(
        self,
        *,
        reference_number: str,
        authentication_token: str,
    ) -> dict[str, Any]:
        raw = await self.get_json(
            f"/auth/{reference_number}",
            bearer_token=authentication_token,
        )
        return self._normalize_auth_status(raw)

    async def redeem_token(self, *, authentication_token: str) -> dict[str, Any]:
        raw = await self.post_json(
            "/auth/token/redeem",
            bearer_token=authentication_token,
            json=None,
        )
        return self._normalize_auth_tokens(raw)

    async def refresh_token(self, *, refresh_token: str) -> dict[str, Any]:
        raw = await self.post_json(
            "/auth/token/refresh",
            bearer_token=refresh_token,
            json=None,
        )
        normalized = self._normalize_auth_tokens(raw)

        # API refresh zwraca tylko nowy access token.
        # Zostawiamy istniejący refresh token po stronie aplikacji.
        normalized["refresh_token"] = refresh_token
        return normalized

    async def revoke_current_auth(self, *, access_or_refresh_token: str) -> None:
        await self.delete_no_content(
            "/auth/sessions/current",
            bearer_token=access_or_refresh_token,
        )

    async def open_online_session(
        self,
        *,
        access_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raw = await self.post_json(
            "/sessions/online",
            bearer_token=access_token,
            json=payload,
        )
        return self._normalize_open_session(raw)

    async def close_online_session(
        self,
        *,
        access_token: str,
        reference_number: str,
    ) -> None:
        await self.post_no_content(
            f"/sessions/online/{reference_number}/close",
            bearer_token=access_token,
            json=None,
        )

    async def open_batch_session(
        self,
        *,
        access_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raw = await self.post_json(
            "/sessions/batch",
            bearer_token=access_token,
            json=payload,
        )
        return self._normalize_open_session(raw)

    async def close_batch_session(
        self,
        *,
        access_token: str,
        reference_number: str,
    ) -> None:
        await self.post_no_content(
            f"/sessions/batch/{reference_number}/close",
            bearer_token=access_token,
            json=None,
        )

    async def send_invoice(
        self,
        *,
        access_token: str,
        reference_number: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raw = await self.post_json(
            f"/sessions/online/{reference_number}/invoices",
            bearer_token=access_token,
            json=payload,
        )
        return self._normalize_send_invoice(raw)

    async def get_session_status(
        self,
        *,
        access_token: str,
        reference_number: str,
    ) -> dict[str, Any]:
        raw = await self.get_json(
            f"/sessions/{reference_number}",
            bearer_token=access_token,
        )
        return self._normalize_session_status(raw)

    async def get_invoice_status(
        self,
        *,
        access_token: str,
        reference_number: str,
        invoice_reference_number: str,
    ) -> dict[str, Any]:
        raw = await self.get_json(
            f"/sessions/{reference_number}/invoices/{invoice_reference_number}",
            bearer_token=access_token,
        )
        return self._normalize_invoice_status(raw)

    async def download_session_upo(
        self,
        *,
        access_token: str,
        reference_number: str,
        upo_reference_number: str,
    ) -> dict[str, Any]:
        upo_content, headers = await self.get_text(
            f"/sessions/{reference_number}/upo/{upo_reference_number}",
            bearer_token=access_token,
            accept="application/xml",
        )
        return {
            "upo_content": upo_content,
            "content_type": "application/xml",
            "hash_sha256_base64": headers.get("x-ms-meta-hash"),
        }

    async def download_invoice_upo(
        self,
        *,
        access_token: str,
        reference_number: str,
        invoice_reference_number: str,
    ) -> dict[str, Any]:
        upo_content, headers = await self.get_text(
            f"/sessions/{reference_number}/invoices/{invoice_reference_number}/upo",
            bearer_token=access_token,
            accept="application/xml",
        )
        return {
            "upo_content": upo_content,
            "content_type": "application/xml",
            "hash_sha256_base64": headers.get("x-ms-meta-hash"),
        }
