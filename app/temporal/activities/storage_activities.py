"""
Storage-related activities.

This module provides:
- File storage activities
- XML document storage activities
- UPO document storage activities
- Storage cleanup activities
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from temporalio import activity


@runtime_checkable
class BlobStorageProtocol(Protocol):
    async def put_text(
        self,
        *,
        key: str,
        content: str,
        content_type: str,
    ) -> str: ...

    async def put_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
    ) -> str: ...


class StorageActivities:
    def __init__(self, *, blob_storage: BlobStorageProtocol) -> None:
        self.blob_storage = blob_storage

    @activity.defn(name="store_xml_blob")
    async def store_xml_blob(self, input: dict[str, str]) -> str:
        return await self.blob_storage.put_text(
            key=input["key"],
            content=input["content"],
            content_type=input.get("content_type", "application/xml"),
        )

    @activity.defn(name="store_binary_blob")
    async def store_binary_blob(self, input: dict) -> str:
        return await self.blob_storage.put_bytes(
            key=input["key"],
            content=input["content"],
            content_type=input.get("content_type", "application/octet-stream"),
        )
