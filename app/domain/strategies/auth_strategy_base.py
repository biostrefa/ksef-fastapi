"""
Base authentication strategy.

This module provides:
- Authentication strategy interface
- Common auth functionality
- Strategy pattern implementation
- Auth method abstraction

Classes:
    AuthStrategyBase(ABC): Abstract base class for authentication strategies

Abstract Methods:
    build_redeem_payload(challenge: str) -> dict: Build token redemption payload from challenge
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AuthStrategyBase(ABC):
    @abstractmethod
    def get_auth_mode(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_auth_init_payload(
        self,
        *,
        challenge: str,
        context_identifier_type: str,
        context_identifier_value: str,
        authorization_policy: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError
