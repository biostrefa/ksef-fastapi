"""
Database configuration.

This module provides:
- Database engine setup
- Session manager configuration
- Connection management
- Database utilities

Objects / Functions:
    Base = DeclarativeBase: SQLAlchemy declarative base
    engine: Database engine instance
    async_session_factory: Async session factory

Functions:
    get_async_session() -> AsyncSession: Get async database session
    init_db() -> None: Initialize database
"""
