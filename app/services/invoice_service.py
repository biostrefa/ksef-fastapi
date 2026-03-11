"""
Invoice submission service.

This module provides:
- Invoice submission orchestration
- Invoice processing workflow
- Invoice validation and submission
- Invoice status tracking

Classes:
    InvoiceService: Invoice submission service

Public Methods:
    submit_invoice(request: SubmitInvoiceRequest) -> SubmitInvoiceResponse:
        Submit invoice to KSeF
    resubmit_invoice(submission_id: str) -> ResubmitInvoiceResponse:
        Resubmit failed invoice submission
    get_submission(submission_id: str) -> InvoiceDetailsResponse:
        Get invoice submission details
    get_submission_xml(submission_id: str) -> InvoiceXmlResponse:
        Get generated XML for a submission
    list_submissions(...) -> InvoiceListResponse:
        List invoice submissions using local filters

Private Methods:
    _load_or_open_session(tenant_id: str) -> Any:
        Load existing reusable session or open a new one
    _build_invoice_model(request: SubmitInvoiceRequest) -> Any:
        Build invoice domain model
    _validate_invoice(invoice: Any) -> None:
        Validate invoice business rules
    _build_fa3_xml(invoice: Any) -> str:
        Build FA(3) XML from invoice
    _encrypt_invoice(xml: str) -> dict[str, Any]:
        Encrypt invoice XML and build KSeF payload metadata
    _send_to_ksef(reference_number: str, payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        Send encrypted invoice to KSeF API
    _save_submission(...) -> Any:
        Save submission record to local storage
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import (
    AuthenticationError,
    InvoiceNotFoundError,
    KsefBusinessError,
    KsefTransportError,
    SessionNotFoundError,
    ValidationError,
)
from app.core.logging import get_bound_logger, log_timed_operation
from app.infrastructure.persistence.models.audit_log_model import (
    AuditEventOutcome,
    AuditEventSeverity,
)
from app.schemas.invoices import (
    InvoiceDetailsResponse,
    InvoiceListResponse,
    InvoiceXmlResponse,
    ResubmitInvoiceResponse,
    SubmitInvoiceRequest,
    SubmitInvoiceResponse,
)


class InvoiceService:
    """
    Service responsible for the full invoice submission workflow.

    Expected collaborators:
    - token_repository: local access token retrieval
    - session_repository: local KSeF session persistence
    - invoice_repository: local submission persistence
    - ksef_http_client: transport layer for KSeF API
    - encryption_service: session / invoice encryption utilities
    - invoice_builder: FA(3) XML builder
    - invoice_validator: business validation
    - invoice_mapper: request -> domain invoice mapping
    - ksef_response_mapper: optional helper for mapping KSeF responses
    - audit_service: audit trail
    """

    def __init__(
        self,
        *,
        settings: Any,
        token_repository: Any,
        session_repository: Any,
        invoice_repository: Any,
        ksef_http_client: Any,
        encryption_service: Any,
        invoice_builder: Any,
        invoice_validator: Any,
        invoice_mapper: Any,
        ksef_response_mapper: Any,
        audit_service: Any,
    ) -> None:
        self.settings = settings
        self.token_repository = token_repository
        self.session_repository = session_repository
        self.invoice_repository = invoice_repository
        self.ksef_http_client = ksef_http_client
        self.encryption_service = encryption_service
        self.invoice_builder = invoice_builder
        self.invoice_validator = invoice_validator
        self.invoice_mapper = invoice_mapper
        self.ksef_response_mapper = ksef_response_mapper
        self.audit_service = audit_service

        self.logger = get_bound_logger(__name__, component="invoice_service")

    async def submit_invoice(
        self,
        request: SubmitInvoiceRequest,
    ) -> SubmitInvoiceResponse:
        """
        Submit a new invoice to KSeF.

        Flow:
        1. build domain invoice
        2. validate invoice
        3. load reusable session or open a new one
        4. build FA(3) XML
        5. encrypt invoice XML
        6. persist local submission record
        7. send invoice to KSeF
        8. persist KSeF response and local status
        """
        tenant_id = self._extract_tenant_id(request)
        actor_id = self._extract_actor_id(request)
        submission_record: Any | None = None

        with log_timed_operation(
            self.logger,
            "submit_invoice",
            tenant_id=tenant_id,
            actor_id=actor_id,
        ):
            await self.audit_service.log_invoice_event(
                event_name="invoice_submission_started",
                message="Invoice submission workflow started.",
                outcome=AuditEventOutcome.PENDING,
                severity=AuditEventSeverity.INFO,
                tenant_id=tenant_id,
                actor_id=actor_id,
                context={"request": self._serialize(request)},
            )

            invoice = self._build_invoice_model(request)
            self._validate_invoice(invoice)

            session = await self._load_or_open_session(tenant_id)
            session_reference_number = self._read_attr(session, "reference_number")
            if not session_reference_number:
                raise SessionNotFoundError(
                    message="Loaded KSeF session does not contain reference number.",
                    details={"tenant_id": tenant_id},
                )

            xml = self._build_fa3_xml(invoice)
            encrypted_payload = self._encrypt_invoice(xml)

            submission_record = await self._save_submission(
                tenant_id=tenant_id,
                actor_id=actor_id,
                session_reference_number=session_reference_number,
                source_request=request,
                invoice=invoice,
                xml=xml,
                encrypted_payload=encrypted_payload,
                local_status="prepared",
                transport_status="pending",
            )

            try:
                ksef_response = await self._send_to_ksef(
                    reference_number=session_reference_number,
                    payload=encrypted_payload,
                    tenant_id=tenant_id,
                )
            except Exception as exc:
                await self._mark_submission_failed(
                    submission_id=str(self._read_attr(submission_record, "id")),
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                )
                await self.audit_service.log_invoice_event(
                    event_name="invoice_submission_failed",
                    message="Invoice submission to KSeF failed.",
                    outcome=AuditEventOutcome.FAILURE,
                    severity=AuditEventSeverity.ERROR,
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    session_reference_number=session_reference_number,
                    submission_id=str(self._read_attr(submission_record, "id")),
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                    context={"request": self._serialize(request)},
                )
                raise

            invoice_reference_number = self._extract_invoice_reference_number(
                ksef_response
            )
            processing_code = self._extract_processing_code(ksef_response)

            updated_record = await self._update_submission_after_send(
                submission_id=str(self._read_attr(submission_record, "id")),
                invoice_reference_number=invoice_reference_number,
                local_status="sent",
                transport_status="accepted_by_gateway",
                ksef_response=ksef_response,
                processing_code=processing_code,
            )

            await self.audit_service.log_invoice_event(
                event_name="invoice_submission_sent",
                message="Invoice was sent to KSeF.",
                outcome=AuditEventOutcome.SUCCESS,
                severity=AuditEventSeverity.INFO,
                tenant_id=tenant_id,
                actor_id=actor_id,
                session_reference_number=session_reference_number,
                invoice_reference_number=invoice_reference_number,
                submission_id=str(self._read_attr(updated_record, "id")),
                context={
                    "processing_code": processing_code,
                    "ksef_response": self._serialize(ksef_response),
                },
            )

            return self._build_schema(
                SubmitInvoiceResponse,
                {
                    "submission_id": str(self._read_attr(updated_record, "id")),
                    "local_status": self._read_attr(
                        updated_record, "local_status", "sent"
                    ),
                    "transport_status": self._read_attr(
                        updated_record,
                        "transport_status",
                        "accepted_by_gateway",
                    ),
                    "session_reference_number": session_reference_number,
                    "invoice_reference_number": invoice_reference_number,
                    "processing_code": processing_code,
                    "message": "Invoice submitted to KSeF.",
                },
            )

    async def send_invoice(
        self,
        request: SubmitInvoiceRequest,
    ) -> SubmitInvoiceResponse:
        """
        Backward-compatible alias for submit_invoice().
        """
        return await self.submit_invoice(request)

    async def resubmit_invoice(
        self,
        submission_id: str,
    ) -> ResubmitInvoiceResponse:
        """
        Resubmit previously failed or pending invoice submission.

        The service reuses stored XML if available. If not available, it tries
        to rebuild XML from stored source payload.
        """
        record = await self.invoice_repository.get_by_id(submission_id)
        if record is None:
            raise InvoiceNotFoundError(
                message="Invoice submission not found.",
                details={"submission_id": submission_id},
            )

        tenant_id = self._read_attr(record, "tenant_id")
        actor_id = self._read_attr(record, "actor_id")
        session = await self._load_or_open_session(tenant_id)
        session_reference_number = self._read_attr(session, "reference_number")

        xml = self._read_attr(record, "xml_content")
        if not xml:
            source_payload = self._read_attr(record, "source_payload_json") or {}
            rebuilt_request = self._coerce_source_payload_to_submit_request(
                source_payload
            )
            invoice = self._build_invoice_model(rebuilt_request)
            self._validate_invoice(invoice)
            xml = self._build_fa3_xml(invoice)

        encrypted_payload = self._encrypt_invoice(xml)
        ksef_response = await self._send_to_ksef(
            reference_number=session_reference_number,
            payload=encrypted_payload,
            tenant_id=tenant_id,
        )

        invoice_reference_number = self._extract_invoice_reference_number(ksef_response)
        processing_code = self._extract_processing_code(ksef_response)

        updated_record = await self._update_submission_after_send(
            submission_id=submission_id,
            invoice_reference_number=invoice_reference_number,
            local_status="resent",
            transport_status="accepted_by_gateway",
            ksef_response=ksef_response,
            processing_code=processing_code,
            xml_content=xml,
        )

        await self.audit_service.log_invoice_event(
            event_name="invoice_resubmitted",
            message="Invoice was resubmitted to KSeF.",
            outcome=AuditEventOutcome.SUCCESS,
            severity=AuditEventSeverity.INFO,
            tenant_id=tenant_id,
            actor_id=actor_id,
            session_reference_number=session_reference_number,
            invoice_reference_number=invoice_reference_number,
            submission_id=submission_id,
            context={"processing_code": processing_code},
        )

        return self._build_schema(
            ResubmitInvoiceResponse,
            {
                "submission_id": str(self._read_attr(updated_record, "id")),
                "local_status": self._read_attr(
                    updated_record, "local_status", "resent"
                ),
                "transport_status": self._read_attr(
                    updated_record,
                    "transport_status",
                    "accepted_by_gateway",
                ),
                "session_reference_number": session_reference_number,
                "invoice_reference_number": invoice_reference_number,
                "processing_code": processing_code,
                "message": "Invoice resubmitted to KSeF.",
            },
        )

    async def resend_invoice(
        self,
        submission_id: str,
    ) -> ResubmitInvoiceResponse:
        """
        Backward-compatible alias for resubmit_invoice().
        """
        return await self.resubmit_invoice(submission_id)

    async def get_submission(
        self,
        submission_id: str,
    ) -> InvoiceDetailsResponse:
        """
        Return local invoice submission details.
        """
        record = await self.invoice_repository.get_by_id(submission_id)
        if record is None:
            raise InvoiceNotFoundError(
                message="Invoice submission not found.",
                details={"submission_id": submission_id},
            )

        return self._build_schema(
            InvoiceDetailsResponse,
            self._serialize_submission_record(record),
        )

    async def get_submission_xml(
        self,
        submission_id: str,
    ) -> InvoiceXmlResponse:
        """
        Return locally stored XML generated for the submission.
        """
        record = await self.invoice_repository.get_by_id(submission_id)
        if record is None:
            raise InvoiceNotFoundError(
                message="Invoice submission not found.",
                details={"submission_id": submission_id},
            )

        xml_content = self._read_attr(record, "xml_content")
        if not xml_content:
            raise ValidationError(
                message="XML content is not available for this submission.",
                details={"submission_id": submission_id},
            )

        return self._build_schema(
            InvoiceXmlResponse,
            {
                "submission_id": submission_id,
                "xml_content": xml_content,
            },
        )

    async def list_submissions(
        self,
        *,
        session_reference_number: str | None = None,
        local_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InvoiceListResponse:
        """
        List local invoice submissions using filters known to the internal API.
        """
        items = await self.invoice_repository.list_submissions(
            session_reference_number=session_reference_number,
            local_status=local_status,
            limit=limit,
            offset=offset,
        )

        serialized_items = [self._serialize_submission_record(item) for item in items]

        return self._build_schema(
            InvoiceListResponse,
            {
                "items": serialized_items,
                "limit": limit,
                "offset": offset,
                "count": len(serialized_items),
            },
        )

    async def _load_or_open_session(self, tenant_id: str) -> Any:
        """
        Load existing reusable online session or open a new one.

        Expected repository/client contract:
        - session_repository.get_reusable_online_session(tenant_id)
        - token_repository.get_active_access_token(tenant_id)
        - encryption_service.build_session_init_payload()
        - ksef_http_client.create_online_session(access_token=..., payload=...)
        - session_repository.create_from_remote(...)
        """
        reusable_session = await self.session_repository.get_reusable_online_session(
            tenant_id
        )
        if reusable_session is not None:
            return reusable_session

        access_token = await self._get_active_access_token(tenant_id)
        session_init_payload = self.encryption_service.build_session_init_payload()

        try:
            remote_response = await self.ksef_http_client.create_online_session(
                access_token=access_token,
                payload=session_init_payload,
            )
        except Exception as exc:
            raise KsefTransportError(
                message="Failed to open KSeF online session.",
                details={"tenant_id": tenant_id, "error": str(exc)},
            ) from exc

        reference_number = self._extract_session_reference_number(remote_response)
        if not reference_number:
            raise KsefBusinessError(
                message="KSeF did not return session reference number.",
                details={
                    "tenant_id": tenant_id,
                    "response": self._serialize(remote_response),
                },
            )

        session_record = await self.session_repository.create_from_remote(
            tenant_id=tenant_id,
            session_type="online",
            reference_number=reference_number,
            local_status="open",
            auth_context=self._serialize(remote_response),
            init_payload=self._serialize(session_init_payload),
            remote_response=self._serialize(remote_response),
        )

        await self.audit_service.log_session_event(
            event_name="online_session_opened",
            message="A new KSeF online session was opened.",
            outcome=AuditEventOutcome.SUCCESS,
            severity=AuditEventSeverity.INFO,
            tenant_id=tenant_id,
            session_reference_number=reference_number,
            context={"remote_response": self._serialize(remote_response)},
        )

        return session_record

    def _build_invoice_model(self, request: SubmitInvoiceRequest) -> Any:
        """
        Map request payload to domain invoice model.
        """
        if hasattr(self.invoice_mapper, "to_domain"):
            return self.invoice_mapper.to_domain(request)

        if hasattr(self.invoice_mapper, "map_request_to_invoice"):
            return self.invoice_mapper.map_request_to_invoice(request)

        raise ValidationError(
            message="Invoice mapper does not expose supported mapping method.",
            details={"expected_methods": ["to_domain", "map_request_to_invoice"]},
        )

    def _validate_invoice(self, invoice: Any) -> None:
        """
        Validate invoice business rules before XML generation.
        """
        if hasattr(self.invoice_validator, "validate_for_ksef"):
            self.invoice_validator.validate_for_ksef(invoice)
            return

        if hasattr(self.invoice_validator, "validate"):
            self.invoice_validator.validate(invoice)
            return

        raise ValidationError(
            message="Invoice validator does not expose supported validation method.",
            details={"expected_methods": ["validate_for_ksef", "validate"]},
        )

    def _build_fa3_xml(self, invoice: Any) -> str:
        """
        Build FA(3) XML using dedicated builder.
        """
        if hasattr(self.invoice_builder, "build"):
            xml = self.invoice_builder.build(invoice)
        elif hasattr(self.invoice_builder, "build_fa3_xml"):
            xml = self.invoice_builder.build_fa3_xml(invoice)
        else:
            raise ValidationError(
                message="Invoice builder does not expose supported build method.",
                details={"expected_methods": ["build", "build_fa3_xml"]},
            )

        if not isinstance(xml, str) or not xml.strip():
            raise ValidationError(
                message="Invoice builder returned empty XML content.",
                details={},
            )

        return xml

    def _encrypt_invoice(self, xml: str) -> dict[str, Any]:
        """
        Encrypt invoice XML and produce payload required by KSeF transport layer.
        """
        if hasattr(self.encryption_service, "encrypt_invoice_xml"):
            payload = self.encryption_service.encrypt_invoice_xml(xml)
        elif hasattr(self.encryption_service, "encrypt_invoice_payload"):
            payload = self.encryption_service.encrypt_invoice_payload(xml)
        else:
            raise ValidationError(
                message="Encryption service does not expose supported invoice encryption method.",
                details={
                    "expected_methods": [
                        "encrypt_invoice_xml",
                        "encrypt_invoice_payload",
                    ]
                },
            )

        if not isinstance(payload, dict):
            raise ValidationError(
                message="Encryption service returned unsupported payload type.",
                details={"actual_type": type(payload).__name__},
            )

        return payload

    async def _send_to_ksef(
        self,
        reference_number: str,
        payload: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Send encrypted invoice to KSeF using active access token.
        """
        access_token = await self._get_active_access_token(tenant_id)

        try:
            if hasattr(self.ksef_http_client, "send_invoice_in_online_session"):
                response = await self.ksef_http_client.send_invoice_in_online_session(
                    reference_number=reference_number,
                    access_token=access_token,
                    payload=payload,
                )
            elif hasattr(self.ksef_http_client, "send_invoice_online"):
                response = await self.ksef_http_client.send_invoice_online(
                    reference_number=reference_number,
                    access_token=access_token,
                    payload=payload,
                )
            else:
                raise ValidationError(
                    message="KSeF HTTP client does not expose supported send method.",
                    details={
                        "expected_methods": [
                            "send_invoice_in_online_session",
                            "send_invoice_online",
                        ]
                    },
                )
        except (KsefTransportError, KsefBusinessError):
            raise
        except Exception as exc:
            raise KsefTransportError(
                message="Failed to send invoice to KSeF.",
                details={
                    "tenant_id": tenant_id,
                    "reference_number": reference_number,
                    "error": str(exc),
                },
            ) from exc

        if not isinstance(response, dict):
            return {"raw_response": self._serialize(response)}

        return response

    async def _save_submission(
        self,
        *,
        tenant_id: str,
        actor_id: str | None,
        session_reference_number: str,
        source_request: SubmitInvoiceRequest,
        invoice: Any,
        xml: str,
        encrypted_payload: dict[str, Any],
        local_status: str,
        transport_status: str,
    ) -> Any:
        """
        Persist initial local invoice submission record.
        """
        record = await self.invoice_repository.create_submission(
            tenant_id=tenant_id,
            actor_id=actor_id,
            session_reference_number=session_reference_number,
            invoice_number=self._extract_invoice_number(invoice, source_request),
            local_status=local_status,
            transport_status=transport_status,
            source_payload_json=self._serialize(source_request),
            invoice_payload_json=self._serialize(invoice),
            xml_content=xml,
            xml_sha256=self._extract_xml_hash(encrypted_payload),
            encrypted_payload_json=self._serialize(encrypted_payload),
            created_at=datetime.now(timezone.utc),
        )

        await self.audit_service.log_invoice_event(
            event_name="invoice_submission_saved",
            message="Invoice submission record was created locally.",
            outcome=AuditEventOutcome.SUCCESS,
            severity=AuditEventSeverity.INFO,
            tenant_id=tenant_id,
            actor_id=actor_id,
            session_reference_number=session_reference_number,
            submission_id=str(self._read_attr(record, "id")),
            context={
                "invoice_number": self._extract_invoice_number(invoice, source_request)
            },
        )

        return record

    async def _mark_submission_failed(
        self,
        *,
        submission_id: str,
        error_code: str | None,
        error_message: str | None,
    ) -> Any:
        """
        Mark local submission as failed.
        """
        return await self.invoice_repository.mark_send_failed(
            submission_id=submission_id,
            local_status="send_failed",
            transport_status="failed",
            error_code=error_code,
            error_message=error_message,
            updated_at=datetime.now(timezone.utc),
        )

    async def _update_submission_after_send(
        self,
        *,
        submission_id: str,
        invoice_reference_number: str | None,
        local_status: str,
        transport_status: str,
        ksef_response: dict[str, Any],
        processing_code: str | None,
        xml_content: str | None = None,
    ) -> Any:
        """
        Persist KSeF acceptance metadata after sending invoice.
        """
        return await self.invoice_repository.update_submission_after_send(
            submission_id=submission_id,
            invoice_reference_number=invoice_reference_number,
            local_status=local_status,
            transport_status=transport_status,
            processing_code=processing_code,
            remote_response_json=self._serialize(ksef_response),
            xml_content=xml_content,
            updated_at=datetime.now(timezone.utc),
        )

    async def _get_active_access_token(self, tenant_id: str) -> str:
        """
        Load active access token for tenant/company.
        """
        token_record = await self.token_repository.get_active_access_token(tenant_id)
        if token_record is None:
            raise AuthenticationError(
                message="No active KSeF access token found for tenant.",
                details={"tenant_id": tenant_id},
            )

        access_token = self._read_attr(token_record, "access_token") or self._read_attr(
            token_record,
            "token",
        )
        if not access_token:
            raise AuthenticationError(
                message="Stored auth context does not contain access token.",
                details={"tenant_id": tenant_id},
            )

        return access_token

    def _extract_tenant_id(self, request: SubmitInvoiceRequest) -> str:
        """
        Resolve tenant/company identifier from request.
        """
        tenant_id = (
            self._read_attr(request, "tenant_id")
            or self._read_attr(request, "company_id")
            or self._read_attr(request, "organization_id")
        )
        if not tenant_id:
            raise ValidationError(
                message="Invoice submission request does not contain tenant identifier.",
                details={
                    "expected_fields": ["tenant_id", "company_id", "organization_id"]
                },
            )
        return str(tenant_id)

    def _extract_actor_id(self, request: SubmitInvoiceRequest) -> str | None:
        """
        Resolve optional actor identifier from request.
        """
        actor_id = self._read_attr(request, "actor_id") or self._read_attr(
            request, "user_id"
        )
        return str(actor_id) if actor_id else None

    def _extract_invoice_number(
        self, invoice: Any, request: SubmitInvoiceRequest
    ) -> str | None:
        """
        Resolve invoice number from domain model or source request.
        """
        return (
            self._string_or_none(self._read_attr(invoice, "invoice_number"))
            or self._string_or_none(self._read_attr(invoice, "number"))
            or self._string_or_none(self._read_attr(request, "invoice_number"))
            or self._string_or_none(self._read_attr(request, "number"))
        )

    def _extract_xml_hash(self, encrypted_payload: dict[str, Any]) -> str | None:
        """
        Resolve XML hash / digest from encrypted payload metadata.
        """
        return (
            self._string_or_none(encrypted_payload.get("document_hash"))
            or self._string_or_none(encrypted_payload.get("hash"))
            or self._string_or_none(encrypted_payload.get("sha256"))
        )

    def _extract_session_reference_number(self, remote_response: Any) -> str | None:
        """
        Resolve KSeF session reference number from remote response.
        """
        if hasattr(self.ksef_response_mapper, "extract_session_reference_number"):
            value = self.ksef_response_mapper.extract_session_reference_number(
                remote_response
            )
            if value:
                return str(value)

        serialized = self._serialize(remote_response)
        return self._string_or_none(
            serialized.get("referenceNumber")
            or serialized.get("reference_number")
            or serialized.get("sessionReferenceNumber")
            or serialized.get("session_reference_number")
        )

    def _extract_invoice_reference_number(self, remote_response: Any) -> str | None:
        """
        Resolve KSeF invoice reference number from remote response.
        """
        if hasattr(self.ksef_response_mapper, "extract_invoice_reference_number"):
            value = self.ksef_response_mapper.extract_invoice_reference_number(
                remote_response
            )
            if value:
                return str(value)

        serialized = self._serialize(remote_response)
        return self._string_or_none(
            serialized.get("invoiceReferenceNumber")
            or serialized.get("invoice_reference_number")
            or serialized.get("referenceNumber")
            or serialized.get("reference_number")
        )

    def _extract_processing_code(self, remote_response: Any) -> str | None:
        """
        Resolve gateway / processing code from KSeF response.
        """
        if hasattr(self.ksef_response_mapper, "extract_processing_code"):
            value = self.ksef_response_mapper.extract_processing_code(remote_response)
            if value:
                return str(value)

        serialized = self._serialize(remote_response)
        return self._string_or_none(
            serialized.get("processingCode")
            or serialized.get("processing_code")
            or serialized.get("code")
        )

    def _serialize_submission_record(self, record: Any) -> dict[str, Any]:
        """
        Normalize repository/model object into API-friendly payload.
        """
        payload = self._serialize(record)
        payload.pop("_sa_instance_state", None)
        return payload

    def _coerce_source_payload_to_submit_request(
        self,
        source_payload: dict[str, Any],
    ) -> SubmitInvoiceRequest:
        """
        Recreate SubmitInvoiceRequest from stored source payload.
        """
        return self._build_schema(SubmitInvoiceRequest, source_payload)

    def _build_schema(self, model_cls: Any, payload: dict[str, Any]) -> Any:
        """
        Create Pydantic model or plain class instance from payload.
        """
        if hasattr(model_cls, "model_validate"):
            return model_cls.model_validate(payload)

        if hasattr(model_cls, "parse_obj"):
            return model_cls.parse_obj(payload)

        return model_cls(**payload)

    def _serialize(self, value: Any) -> Any:
        """
        Convert Pydantic, dataclass-like and ORM-like objects to plain structures.
        """
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {key: self._serialize(val) for key, val in value.items()}

        if isinstance(value, list):
            return [self._serialize(item) for item in value]

        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")

        if hasattr(value, "dict"):
            return value.dict()

        if hasattr(value, "__dict__"):
            return {
                key: self._serialize(val)
                for key, val in vars(value).items()
                if not key.startswith("_")
            }

        return value

    def _read_attr(self, obj: Any, name: str, default: Any = None) -> Any:
        """
        Safe attribute-or-dict access helper.
        """
        if obj is None:
            return default

        if isinstance(obj, dict):
            return obj.get(name, default)

        return getattr(obj, name, default)

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
