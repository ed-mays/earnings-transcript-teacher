"""Tests for JsonFormatter and the LOG_FORMAT-driven handler configuration."""

import json
import logging
import os
import sys

import pytest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from main import JsonFormatter, _RequestIdFilter


def _make_record(
    message: str = "test message",
    level: int = logging.INFO,
    name: str = "test.logger",
    exc_info=None,
) -> logging.LogRecord:
    """Return a LogRecord pre-populated with a request_id for formatter tests."""
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=exc_info,
    )
    record.request_id = "req-abc-123"
    return record


def test_json_formatter_output_is_valid_json():
    """JsonFormatter must produce a parseable JSON string."""
    formatter = JsonFormatter()
    record = _make_record()
    output = formatter.format(record)
    parsed = json.loads(output)  # raises if not valid JSON
    assert isinstance(parsed, dict)


def test_json_formatter_includes_required_fields():
    """JSON output must include timestamp, level, logger, message, and request_id."""
    formatter = JsonFormatter()
    record = _make_record(message="hello world", name="my.module")
    output = json.loads(formatter.format(record))

    assert output["level"] == "INFO"
    assert output["logger"] == "my.module"
    assert output["message"] == "hello world"
    assert output["request_id"] == "req-abc-123"
    assert "timestamp" in output
    # timestamp must be a valid ISO-8601 string
    from datetime import datetime
    datetime.fromisoformat(output["timestamp"])


def test_json_formatter_includes_exception_when_exc_info_present():
    """JSON output must include an 'exception' key when the record carries exc_info."""
    formatter = JsonFormatter()
    try:
        raise ValueError("something went wrong")
    except ValueError:
        exc_info = sys.exc_info()

    record = _make_record(exc_info=exc_info)
    output = json.loads(formatter.format(record))

    assert "exception" in output
    assert "ValueError" in output["exception"]
    assert "something went wrong" in output["exception"]


def test_json_formatter_no_exception_key_without_exc_info():
    """JSON output must not include 'exception' key when no exception is attached."""
    formatter = JsonFormatter()
    record = _make_record()
    output = json.loads(formatter.format(record))
    assert "exception" not in output


def test_request_id_filter_injects_dash_when_no_context(monkeypatch):
    """_RequestIdFilter sets request_id to '-' when no ContextVar value is set."""
    # Ensure the ContextVar has no value by resetting any existing state
    import context as ctx
    token = ctx.request_id_var.set("-")
    try:
        filt = _RequestIdFilter()
        record = logging.LogRecord("x", logging.INFO, "", 0, "msg", (), None)
        filt.filter(record)
        assert record.request_id == "-"
    finally:
        ctx.request_id_var.reset(token)


def test_request_id_filter_injects_contextvar_value():
    """_RequestIdFilter propagates the active ContextVar value into the record."""
    import context as ctx
    token = ctx.request_id_var.set("req-xyz-789")
    try:
        filt = _RequestIdFilter()
        record = logging.LogRecord("x", logging.INFO, "", 0, "msg", (), None)
        filt.filter(record)
        assert record.request_id == "req-xyz-789"
    finally:
        ctx.request_id_var.reset(token)
