import logging

from core.error_handling import PeaceErrorFilter, exception_details


class Forbidden(Exception):
    status = 403


def test_transient_gateway_dns_is_visible_as_warning() -> None:
    record = logging.LogRecord(
        name="discord.gateway",
        level=logging.ERROR,
        pathname="gateway.py",
        lineno=1,
        msg="ClientConnectorDNSError: Cannot connect to host gateway-us-east1-d.discord.gg:443",
        args=(),
        exc_info=None,
    )

    assert PeaceErrorFilter().filter(record) is True
    assert record.levelno == logging.WARNING
    assert record.exc_info is None


def test_unexpected_errors_remain_errors() -> None:
    record = logging.LogRecord(
        name="peace",
        level=logging.ERROR,
        pathname="main.py",
        lineno=1,
        msg="falha inesperada",
        args=(),
        exc_info=(RuntimeError, RuntimeError("bug"), None),
    )

    assert PeaceErrorFilter().filter(record) is True
    assert record.levelno == logging.ERROR


def test_handled_permission_failure_is_not_classified_as_fatal() -> None:
    error = Forbidden("missing permission")
    record = logging.LogRecord(
        name="peace",
        level=logging.ERROR,
        pathname="main.py",
        lineno=1,
        msg="request failed",
        args=(),
        exc_info=(type(error), error, None),
    )

    assert PeaceErrorFilter().filter(record) is True
    assert record.levelno == logging.WARNING
    assert exception_details(error) == {"type": "Forbidden", "status": 403}

