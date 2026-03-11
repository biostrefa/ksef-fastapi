"""
Invoice processing activities.

This module provides:
- Invoice validation activities
- Invoice submission activities
- Invoice status checking activities
- UPO download activities
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from temporalio import activity
from temporalio.exceptions import ApplicationError


@runtime_checkable
class InvoiceRepositoryProtocol(Protocol):
    async def get_invoice_for_ksef(self, invoice_id: str) -> dict[str, Any] | None: ...


@runtime_checkable
class InvoiceValidatorProtocol(Protocol):
    def validate_for_ksef(self, invoice_payload: dict[str, Any]) -> None: ...


@runtime_checkable
class InvoiceFa3BuilderProtocol(Protocol):
    def build(self, invoice_payload: dict[str, Any]) -> str: ...


@runtime_checkable
class EncryptionServiceProtocol(Protocol):
    async def encrypt_xml(
        self,
        *,
        xml_text: str,
        company_id: str,
        environment: str,
    ) -> dict[str, Any]: ...


@runtime_checkable
class KsefHttpClientProtocol(Protocol):
    async def send_online_invoice(
        self,
        *,
        access_token: str,
        session_reference_number: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...

    async def get_invoice_status(
        self,
        *,
        access_token: str,
        session_reference_number: str,
        invoice_reference_number: str,
    ) -> dict[str, Any]: ...


class InvoiceActivities:
    def __init__(
        self,
        *,
        invoice_repository: InvoiceRepositoryProtocol,
        invoice_validator: InvoiceValidatorProtocol,
        invoice_builder: InvoiceFa3BuilderProtocol,
        encryption_service: EncryptionServiceProtocol,
        ksef_http_client: KsefHttpClientProtocol,
    ) -> None:
        self.invoice_repository = invoice_repository
        self.invoice_validator = invoice_validator
        self.invoice_builder = invoice_builder
        self.encryption_service = encryption_service
        self.ksef_http_client = ksef_http_client

    @activity.defn(name="load_invoice_for_send")
    async def load_invoice_for_send(self, invoice_id: str) -> dict[str, Any]:
        invoice_payload = await self.invoice_repository.get_invoice_for_ksef(invoice_id)
        if invoice_payload is None:
            raise ApplicationError(
                f"Invoice {invoice_id} not found",
                type="InvoiceNotFound",
                non_retryable=True,
            )
        return invoice_payload

    @activity.defn(name="validate_invoice_for_send")
    async def validate_invoice_for_send(self, invoice_payload: dict[str, Any]) -> None:
        try:
            self.invoice_validator.validate_for_ksef(invoice_payload)
        except ValueError as exc:
            raise ApplicationError(
                str(exc),
                type="BusinessRuleViolation",
                non_retryable=True,
            ) from exc

    @activity.defn(name="build_fa3_xml")
    async def build_fa3_xml(self, invoice_payload: dict[str, Any]) -> str:
        return self.invoice_builder.build(invoice_payload)

    @activity.defn(name="encrypt_invoice_xml")
    async def encrypt_invoice_xml(self, input: dict[str, Any]) -> dict[str, Any]:
        return await self.encryption_service.encrypt_xml(
            xml_text=str(input["xml_text"]),
            company_id=str(input["company_id"]),
            environment=str(input["environment"]),
        )

    @activity.defn(name="send_invoice_online")
    async def send_invoice_online(self, input: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "invoiceHash": input["invoice_hash"],
            "invoiceSize": input["invoice_size"],
            "encryptedInvoiceHash": input["encrypted_invoice_hash"],
            "encryptedInvoiceSize": input["encrypted_invoice_size"],
            "encryptedInvoiceContent": input["encrypted_invoice_content"],
            "offlineMode": bool(input.get("offline_mode", False)),
        }
        return await self.ksef_http_client.send_online_invoice(
            access_token=str(input["access_token"]),
            session_reference_number=str(input["session_reference_number"]),
            payload=payload,
        )

    @activity.defn(name="get_invoice_status")
    async def get_invoice_status(self, input: dict[str, Any]) -> dict[str, Any]:
        return await self.ksef_http_client.get_invoice_status(
            access_token=str(input["access_token"]),
            session_reference_number=str(input["session_reference_number"]),
            invoice_reference_number=str(input["invoice_reference_number"]),
        )

    #
    # Placeholder batch methods – coherent with spec, but not yet production flow.
    #

    @activity.defn(name="load_batch_for_send")
    async def load_batch_for_send(self, batch_id: str) -> dict[str, Any]:
        raise ApplicationError(
            "Batch flow is not implemented in this skeleton yet",
            type="BatchNotImplemented",
            non_retryable=True,
        )

    @activity.defn(name="validate_batch_for_send")
    async def validate_batch_for_send(self, batch_payload: dict[str, Any]) -> None:
        raise ApplicationError(
            "Batch flow is not implemented in this skeleton yet",
            type="BatchNotImplemented",
            non_retryable=True,
        )

    @activity.defn(name="send_invoice_batch")
    async def send_invoice_batch(self, input: dict[str, Any]) -> dict[str, Any]:
        raise ApplicationError(
            "Batch flow is not implemented in this skeleton yet",
            type="BatchNotImplemented",
            non_retryable=True,
        )
