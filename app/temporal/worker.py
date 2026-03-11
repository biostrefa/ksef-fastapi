"""
Temporal worker configuration and setup.

This module provides:
- Worker initialization
- Activity and workflow registration
- Worker lifecycle management
- Worker configuration
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal.task_queues import (
    KSEF_AUTH_TQ,
    KSEF_COMMANDS_TQ,
    KSEF_RECONCILIATION_TQ,
)
from app.temporal.workflows.authenticate_to_mf_workflow import AuthenticateToMfWorkflow
from app.temporal.workflows.refresh_auth_context_workflow import (
    RefreshAuthContextWorkflow,
)
from app.temporal.workflows.send_invoice_online_workflow import (
    SendInvoiceOnlineWorkflow,
)
from app.temporal.workflows.send_invoice_batch_workflow import SendInvoiceBatchWorkflow
from app.temporal.workflows.reconcile_pending_submissions_workflow import (
    ReconcilePendingSubmissionsWorkflow,
)

from app.temporal.activities.auth_activities import AuthActivities
from app.temporal.activities.session_activities import SessionActivities
from app.temporal.activities.invoice_activities import InvoiceActivities
from app.temporal.activities.persistence_activities import PersistenceActivities
from app.temporal.activities.storage_activities import StorageActivities
from app.temporal.activities.audit_activities import AuditActivities


@dataclass(frozen=True)
class WorkerSettings:
    temporal_target: str = "localhost:7233"
    temporal_namespace: str = "default"


async def build_client(settings: WorkerSettings) -> Client:
    return await Client.connect(
        settings.temporal_target,
        namespace=settings.temporal_namespace,
    )


async def run_auth_worker(
    *,
    client: Client,
    auth_activities: AuthActivities,
) -> None:
    worker = Worker(
        client,
        task_queue=KSEF_AUTH_TQ,
        workflows=[
            AuthenticateToMfWorkflow,
            RefreshAuthContextWorkflow,
        ],
        activities=[
            auth_activities.ensure_auth_context,
            auth_activities.refresh_auth_context,
        ],
    )
    await worker.run()


async def run_commands_worker(
    *,
    client: Client,
    auth_activities: AuthActivities,
    session_activities: SessionActivities,
    invoice_activities: InvoiceActivities,
    persistence_activities: PersistenceActivities,
    storage_activities: StorageActivities,
    audit_activities: AuditActivities,
) -> None:
    worker = Worker(
        client,
        task_queue=KSEF_COMMANDS_TQ,
        workflows=[
            SendInvoiceOnlineWorkflow,
            SendInvoiceBatchWorkflow,
        ],
        activities=[
            auth_activities.ensure_auth_context,
            auth_activities.refresh_auth_context,
            session_activities.open_online_session,
            session_activities.close_online_session,
            session_activities.get_online_session_status,
            invoice_activities.load_invoice_for_send,
            invoice_activities.validate_invoice_for_send,
            invoice_activities.build_fa3_xml,
            invoice_activities.encrypt_invoice_xml,
            invoice_activities.send_invoice_online,
            invoice_activities.get_invoice_status,
            invoice_activities.load_batch_for_send,
            invoice_activities.validate_batch_for_send,
            invoice_activities.send_invoice_batch,
            persistence_activities.create_submission_record,
            persistence_activities.mark_submission_started,
            persistence_activities.attach_invoice_reference_number,
            persistence_activities.mark_submission_terminal,
            storage_activities.store_xml_blob,
            storage_activities.store_binary_blob,
            audit_activities.append_audit_event,
        ],
    )
    await worker.run()


async def run_reconciliation_worker(
    *,
    client: Client,
    persistence_activities: PersistenceActivities,
) -> None:
    worker = Worker(
        client,
        task_queue=KSEF_RECONCILIATION_TQ,
        workflows=[
            ReconcilePendingSubmissionsWorkflow,
        ],
        activities=[
            persistence_activities.load_pending_submissions_for_reconciliation,
            persistence_activities.mark_submission_reconciled,
        ],
    )
    await worker.run()


#
# Bootstrap example
#
# Replace imports below with your real implementations.
#

if __name__ == "__main__":
    from app.infrastructure.http.ksef_http_client import KsefApiConfig, KsefHttpClient
    from app.infrastructure.persistence.db import AsyncSessionLocal
    from app.infrastructure.persistence.repositories.auth_context_repository import (
        AuthContextRepository,
    )
    from app.infrastructure.persistence.repositories.submission_repository import (
        SubmissionRepository,
    )

    # Replace these placeholders with real classes from your project.
    from app.somewhere.invoice_repository import SqlAlchemyInvoiceRepository
    from app.somewhere.invoice_validator import InvoiceValidator
    from app.somewhere.invoice_fa3_builder import InvoiceFa3Builder
    from app.somewhere.encryption_service import EncryptionService
    from app.somewhere.credential_provider import CredentialProvider
    from app.somewhere.token_encryption_service import TokenEncryptionService
    from app.somewhere.blob_storage import BlobStorage
    from app.somewhere.audit_log_repository import AuditLogRepository

    async def _main() -> None:
        settings = WorkerSettings()
        client = await build_client(settings)

        ksef_http_client = KsefHttpClient(
            KsefApiConfig(base_url="https://api.ksef.mf.gov.pl/v2")
        )

        auth_context_repository = AuthContextRepository(AsyncSessionLocal)
        submission_repository = SubmissionRepository(AsyncSessionLocal)

        invoice_repository = SqlAlchemyInvoiceRepository(AsyncSessionLocal)
        invoice_validator = InvoiceValidator()
        invoice_builder = InvoiceFa3Builder()
        encryption_service = EncryptionService()
        credential_provider = CredentialProvider()
        token_encryption_service = TokenEncryptionService()
        blob_storage = BlobStorage()
        audit_log_repository = AuditLogRepository(AsyncSessionLocal)

        auth_activities = AuthActivities(
            auth_context_repository=auth_context_repository,
            credential_provider=credential_provider,
            token_encryption_service=token_encryption_service,
            ksef_http_client=ksef_http_client,
        )

        session_activities = SessionActivities(
            ksef_http_client=ksef_http_client,
        )

        invoice_activities = InvoiceActivities(
            invoice_repository=invoice_repository,
            invoice_validator=invoice_validator,
            invoice_builder=invoice_builder,
            encryption_service=encryption_service,
            ksef_http_client=ksef_http_client,
        )

        persistence_activities = PersistenceActivities(
            submission_repository=submission_repository,
        )

        storage_activities = StorageActivities(
            blob_storage=blob_storage,
        )

        audit_activities = AuditActivities(
            audit_log_repository=audit_log_repository,
        )

        await asyncio.gather(
            run_auth_worker(
                client=client,
                auth_activities=auth_activities,
            ),
            run_commands_worker(
                client=client,
                auth_activities=auth_activities,
                session_activities=session_activities,
                invoice_activities=invoice_activities,
                persistence_activities=persistence_activities,
                storage_activities=storage_activities,
                audit_activities=audit_activities,
            ),
            run_reconciliation_worker(
                client=client,
                persistence_activities=persistence_activities,
            ),
        )

    asyncio.run(_main())
