from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from temporalio import activity


@runtime_checkable
class AuditLogRepositoryProtocol(Protocol):
    async def append_event(
        self,
        *,
        entity_type: str,
        entity_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None: ...


class AuditActivities:
    def __init__(self, *, audit_log_repository: AuditLogRepositoryProtocol) -> None:
        self.audit_log_repository = audit_log_repository

    @activity.defn(name="append_audit_event")
    async def append_audit_event(self, input: dict[str, Any]) -> None:
        await self.audit_log_repository.append_event(
            entity_type=str(input["entity_type"]),
            entity_id=str(input["entity_id"]),
            event_type=str(input["event_type"]),
            payload=dict(input.get("payload", {})),
        )
