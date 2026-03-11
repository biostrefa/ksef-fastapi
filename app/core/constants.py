"""
System constants and enums.

This module defines:
- System-wide constants
- Status names and codes
- Environment types
- Configuration constants

Enums / Constants:
    KsefEnvironment: KSEF environment types
    KsefAuthMode: KSEF authentication modes
    KsefSessionType: KSEF session types
    KsefSessionStatus: KSEF session statuses
    InvoiceSubmissionStatus: Invoice submission statuses
    DEFAULT_TIMEOUT_SECONDS: Default timeout in seconds
    FA3_SCHEMA_VERSION: FA3 schema version
"""

from __future__ import annotations

from enum import Enum


class AppEnv(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    TEST = "test"
    STAGE = "stage"
    PROD = "prod"


class KsefEnvironment(str, Enum):
    TEST = "test"
    DEMO = "demo"
    PROD = "prod"


class KsefAuthMode(str, Enum):
    TOKEN = "token"
    XADES = "xades"


class KsefSessionType(str, Enum):
    ONLINE = "online"
    BATCH = "batch"


class KsefSessionStatus(str, Enum):
    NEW = "new"
    OPENING = "opening"
    OPEN = "open"
    PROCESSING = "processing"
    CLOSED = "closed"
    FAILED = "failed"
    EXPIRED = "expired"


class InvoiceSubmissionStatus(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    VALIDATED = "validated"
    XML_BUILT = "xml_built"
    ENCRYPTED = "encrypted"
    QUEUED = "queued"
    SENT = "sent"
    PROCESSING = "processing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UPO_AVAILABLE = "upo_available"
    FAILED = "failed"


class InvoiceCurrency(str, Enum):
    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


class InvoiceKind(str, Enum):
    VAT = "vat"
    CORRECTION = "correction"
    ADVANCE = "advance"
    FINAL = "final"


class PaymentMethod(str, Enum):
    TRANSFER = "transfer"
    CASH = "cash"
    CARD = "card"
    OTHER = "other"
