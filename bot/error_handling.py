"""Logging and failure classification for the Peace bot.

The production console counts records emitted at ``ERROR`` level.  Discord's
gateway can briefly lose DNS or TCP connectivity and discord.py logs the
automatic reconnect traceback as an error even when the session is restored a
moment later.  This module keeps those events visible as warnings while
leaving authentication failures, invalid requests and unexpected exceptions
as errors.
"""

from __future__ import annotations

import logging
from typing import Any


_TRANSIENT_NETWORK_MARKERS = (
    "ClientConnectorDNSError",
    "ClientConnectorError",
    "Temporary failure in name resolution",
    "getaddrinfo failed",
    "Cannot connect to host gateway-",
    "Cannot connect to host discord.com",
    "[Errno -3] Try again",
    "[Errno 11001] getaddrinfo failed",
)


def _exception_chain(error: BaseException | None, *, limit: int = 8) -> list[BaseException]:
    """Return a bounded exception chain without retaining traceback objects."""

    chain: list[BaseException] = []
    current = error
    while current is not None and len(chain) < limit:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def _record_exception(record: logging.LogRecord) -> BaseException | None:
    if not record.exc_info:
        return None
    error = record.exc_info[1]
    return error if isinstance(error, BaseException) else None


def _exception_status(error: BaseException) -> int | None:
    status = getattr(error, "status", None)
    return status if isinstance(status, int) else None


def _is_expected_discord_failure(error: BaseException) -> bool:
    """Whether a handled Discord API failure should not be counted as fatal."""

    for item in _exception_chain(error):
        name = type(item).__name__
        status = _exception_status(item)
        if name in {"Forbidden", "NotFound"}:
            return True
        if name == "HTTPException" and status in {429, 500, 502, 503, 504}:
            return True
    return False


def _is_transient_gateway_network_error(record: logging.LogRecord) -> bool:
    if not record.name.startswith("discord.") or record.levelno < logging.ERROR:
        return False

    values = [record.getMessage()]
    error = _record_exception(record)
    for item in _exception_chain(error):
        values.append(type(item).__name__)
        values.append(str(item))
    rendered = " ".join(values)
    return any(marker in rendered for marker in _TRANSIENT_NETWORK_MARKERS)


class PeaceErrorFilter(logging.Filter):
    """Downgrade only recoverable Discord failures in the console.

    The record remains visible, with its original traceback, but is emitted as
    ``WARNING``.  This keeps the ACL error counter useful: a real 400-level
    request error, authentication problem or unexpected exception remains an
    error and still needs attention.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.ERROR:
            return True

        error = _record_exception(record)
        if (error is not None and _is_expected_discord_failure(error)) or _is_transient_gateway_network_error(record):
            record.levelno = logging.WARNING
            record.levelname = logging.getLevelName(logging.WARNING)
            # The traceback is useful for a fatal bug, but it only repeats the
            # same reconnect cause for a recoverable gateway interruption.
            record.exc_info = None
            record.exc_text = None
        return True


def configure_logging() -> None:
    """Configure one safe, idempotent logging pipeline for local and ACL runs."""

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            if handler.formatter is None:
                handler.setFormatter(formatter)

    for handler in root.handlers:
        if not any(isinstance(item, PeaceErrorFilter) for item in handler.filters):
            handler.addFilter(PeaceErrorFilter())


def exception_details(error: BaseException) -> dict[str, Any]:
    """Return non-sensitive structured details for operational diagnostics."""

    details: dict[str, Any] = {"type": type(error).__name__}
    status = _exception_status(error)
    if status is not None:
        details["status"] = status
    return details

