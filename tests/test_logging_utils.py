"""Unit tests for app.logging_utils (no external calls)."""

import logging

import pytest

from app.logging_utils import RequestIdFilter, log_api_call, request_id_var


def test_log_api_call_logs_start_and_ok(caplog):
    logger = logging.getLogger("test.logging_utils.ok")
    with caplog.at_level(logging.INFO, logger=logger.name):
        with log_api_call(logger, "anthropic.intake", model="claude-opus-4-8"):
            pass
    assert "api_call_start service=anthropic.intake" in caplog.text
    assert "model=claude-opus-4-8" in caplog.text
    assert "api_call_ok service=anthropic.intake" in caplog.text


def test_log_api_call_logs_failure_and_reraises(caplog):
    logger = logging.getLogger("test.logging_utils.fail")
    with caplog.at_level(logging.INFO, logger=logger.name):
        with pytest.raises(RuntimeError):
            with log_api_call(logger, "tavily.search", program="SNAP"):
                raise RuntimeError("boom")
    assert "api_call_failed service=tavily.search" in caplog.text
    assert "program=SNAP" in caplog.text
    assert "error=RuntimeError" in caplog.text


def test_log_api_call_never_logs_narrative_content(caplog):
    logger = logging.getLogger("test.logging_utils.privacy")
    narrative = "my SSN is 123-45-6789 and I live at 42 Elm St"
    with caplog.at_level(logging.INFO, logger=logger.name):
        with log_api_call(logger, "anthropic.intake", model="claude-opus-4-8"):
            pass
    assert narrative not in caplog.text


def test_request_id_filter_attaches_current_value():
    token = request_id_var.set("abc123")
    try:
        record = logging.LogRecord(
            "x", logging.INFO, __file__, 1, "msg", None, None
        )
        assert RequestIdFilter().filter(record) is True
        assert record.request_id == "abc123"
    finally:
        request_id_var.reset(token)


def test_request_id_filter_defaults_when_unset():
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "msg", None, None
    )
    assert RequestIdFilter().filter(record) is True
    assert record.request_id == "-"
