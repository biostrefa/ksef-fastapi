"""
Session management activities.

This module provides:
- Session creation activities
- Session closure activities
- Session status checking activities
- Session lifecycle management
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from temporalio import activity


@runtime_checkable
class KsefHttpClientProtocol(Protocol):
    async def open_online_session(
        self,
        *,
        access_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...

    async def close_online_session(
        self,
        *,
        access_token: str,
        session_reference_number: str,
    ) -> None: ...

    async def get_session_status(
        self,
        *,
        access_token: str,
        session_reference_number: str,
    ) -> dict[str, Any]: ...


class SessionActivities:
    def __init__(self, *, ksef_http_client: KsefHttpClientProtocol) -> None:
        self.ksef_http_client = ksef_http_client

    @activity.defn(name="open_online_session")
    async def open_online_session(self, input: dict[str, Any]) -> dict[str, Any]:
        access_token = str(input["access_token"])
        payload = {
            "formCode": input["form_code"],
            "encryption": input["encryption"],
        }
        if "offlineMode" in input:
            payload["offlineMode"] = input["offlineMode"]

        return await self.ksef_http_client.open_online_session(
            access_token=access_token,
            payload=payload,
        )

    @activity.defn(name="close_online_session")
    async def close_online_session(self, input: dict[str, Any]) -> None:
        await self.ksef_http_client.close_online_session(
            access_token=str(input["access_token"]),
            session_reference_number=str(input["session_reference_number"]),
        )

    @activity.defn(name="get_online_session_status")
    async def get_online_session_status(self, input: dict[str, Any]) -> dict[str, Any]:
        return await self.ksef_http_client.get_session_status(
            access_token=str(input["access_token"]),
            session_reference_number=str(input["session_reference_number"]),
        )
