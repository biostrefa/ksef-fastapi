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
