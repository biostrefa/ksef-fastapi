"""
Invoice domain model.

This module provides:
- Invoice domain entity
- Invoice business logic
- Invoice validation rules
- Invoice state management

Classes:
    Invoice: Main invoice domain model
    InvoiceParty: Invoice party (buyer/seller) model
    InvoiceLine: Invoice line item model
    InvoiceTotals: Invoice totals calculation model
    InvoiceSubmission: Local invoice submission record
    EncryptedInvoicePayload: Encrypted invoice content model
        - encrypted_content: Encrypted invoice data
        - content_hash: Hash of the content
        - file_size: Size of the encrypted file
        - metadata: Additional metadata
"""
