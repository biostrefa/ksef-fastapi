"""
Invoice submission database model.

This module provides:
- Invoice submission table definition
- Status tracking fields
- UPO storage
- Submission metadata

ORM Classes:
    InvoiceSubmissionModel(Base): Invoice submission database model

Fields:
    id: Primary key
    company_id: Company identifier
    session_reference_number: KSeF session reference number
    local_invoice_number: Local invoice number
    ksef_invoice_reference: KSeF invoice reference number
    status: Submission status
    xml_hash: XML content hash
    upo_content: UPO content
    error_code: Error code if any
    error_message: Error message if any
    created_at: Record creation time
    updated_at: Record update time
"""
