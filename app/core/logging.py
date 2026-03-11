from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any

"""
Logging configuration and utilities.

This module provides centralized logging configuration including:
- Structured logging setup
- Log formatting
- Log levels management
- Sensitive data filtering
- Performance logging

Functions
configure_logging() -> None
get_logger(name: str) -> Logger
mask_sensitive_value(value: str | None) -> str
"""


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "plain"  # allowed: plain, json


SENSITIVE_FIELD_NAMES = {
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authentication_token",
    "api_key",
    "private_key",
    "signature",
    "certificate",
    "authorization",
    "x-api-key",
}


def mask_sensitive_value(value: str | None) -> str:
    """
    Mask sensitive string value for logs.

    Examples:
        None -> "***"
        "abc" -> "***"
        "1234567890" -> "12***90"
    """
    if not value:
        return "***"

    if len(value) <= 6:
        return "***"

    return f"{value[:2]}***{value[-2:]}"


def _mask_if_sensitive(key: str, value: Any) -> Any:
    """
    Mask value if field name suggests sensitive content.
    """
    normalized_key = key.strip().lower().replace("-", "_")
    if normalized_key in SENSITIVE_FIELD_NAMES:
        if isinstance(value, str):
            return mask_sensitive_value(value)
        return "***"
    return value


def sanitize_log_data(data: dict[str, Any] | None) -> dict[str, Any]:
    """
    Return sanitized log dictionary safe for output.
    """
    if not data:
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_data(item) if isinstance(item, dict) else item
                for item in value
            ]
            sanitized[key] = [
                _mask_if_sensitive(key, item) if not isinstance(item, dict) else item
                for item in sanitized[key]
            ]
        else:
            sanitized[key] = _mask_if_sensitive(key, value)

    return sanitized


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        standard_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }

        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                extras[key] = value

        extras = sanitize_log_data(extras)
        if extras:
            log_payload["extra"] = extras

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, ensure_ascii=False, default=str)


class PlainTextFormatter(logging.Formatter):
    """
    Readable plain text formatter for local development.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{self.formatTime(record, self.datefmt)} | "
            f"{record.levelname:<8} | "
            f"{record.name} | "
            f"{record.getMessage()}"
        )

        standard_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }

        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                extras[key] = value

        extras = sanitize_log_data(extras)
        if extras:
            base += f" | extra={extras}"

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


def _build_handler(log_format: str) -> logging.Handler:
    """
    Create stream handler with selected formatter.
    """
    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        formatter: logging.Formatter = JsonFormatter(
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        formatter = PlainTextFormatter(
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    return handler


def configure_logging(
    level: str = DEFAULT_LOG_LEVEL,
    log_format: str = DEFAULT_LOG_FORMAT,
) -> None:
    """
    Configure root logging.

    This function is intended to be called once during application startup.
    """
    normalized_level = level.upper().strip()
    numeric_level = getattr(logging, normalized_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    root_logger.addHandler(_build_handler(log_format))

    # Normalize selected noisy third-party loggers
    logging.getLogger("httpx").setLevel(max(numeric_level, logging.INFO))
    logging.getLogger("httpcore").setLevel(max(numeric_level, logging.INFO))
    logging.getLogger("sqlalchemy.engine").setLevel(max(numeric_level, logging.WARNING))
    logging.getLogger("uvicorn.access").setLevel(max(numeric_level, logging.INFO))

    logging.captureWarnings(True)


def get_logger(name: str) -> logging.Logger:
    """
    Return named logger instance.
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that merges sanitized structured context into log records.
    """

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra_from_call = kwargs.pop("extra", {})
        merged_extra = {**self.extra, **extra_from_call}
        kwargs["extra"] = sanitize_log_data(merged_extra)
        return msg, kwargs


def get_bound_logger(name: str, **context: Any) -> LoggerAdapter:
    """
    Return logger bound with static structured context.
    """
    return LoggerAdapter(get_logger(name), sanitize_log_data(context))


@contextmanager
def log_timed_operation(
    logger: logging.Logger,
    operation: str,
    **context: Any,
):
    """
    Context manager for measuring operation duration.

    Example:
        with log_timed_operation(logger, "send_invoice", invoice_id="123"):
            ...
    """
    start = time.perf_counter()
    logger.info(
        f"Started operation: {operation}",
        extra={"operation": operation, **sanitize_log_data(context)},
    )

    try:
        yield
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            f"Operation failed: {operation}",
            extra={
                "operation": operation,
                "elapsed_ms": elapsed_ms,
                **sanitize_log_data(context),
            },
        )
        raise
    else:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"Finished operation: {operation}",
            extra={
                "operation": operation,
                "elapsed_ms": elapsed_ms,
                **sanitize_log_data(context),
            },
        )
