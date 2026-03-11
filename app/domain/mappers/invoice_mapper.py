"""
Invoice data mapping.

This module provides:
- ERP to domain model mapping
- Domain to XML mapping
- KSeF input mapping
- Data transformation logic

Classes:
    InvoiceMapper: Invoice data mapper

Methods:
    from_send_request(dto: SendInvoiceRequest) -> Invoice: Map from send request to domain model
    from_erp_payload(payload: dict) -> Invoice: Map from ERP payload to domain model
    to_submission_response(submission: InvoiceSubmission) -> SendInvoiceResponse: Map to submission response
"""
