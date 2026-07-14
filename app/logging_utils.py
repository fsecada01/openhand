"""Structured logging helpers for external API-call traceability.

Every Anthropic or Tavily call is wrapped in `log_api_call`, which logs
a start/outcome pair (service, elapsed time, model/program) so calls
can be traced without configuring anything else. Narrative text is
never included — only metadata (model name, program name, timing,
exception type).

`request_id_var` lets one /screen request's several API calls (intake,
supplemental, explain, resource search) share a short id in the log
output, without threading a parameter through every function.
"""

import contextvars
import logging
import time
from contextlib import contextmanager

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


@contextmanager
def log_api_call(logger: logging.Logger, service: str, **fields):
    detail = " ".join(f"{k}={v}" for k, v in fields.items())
    start = time.monotonic()
    logger.info("api_call_start service=%s %s", service, detail)
    try:
        yield
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "api_call_failed service=%s %s elapsed_ms=%d error=%s",
            service,
            detail,
            elapsed_ms,
            type(exc).__name__,
        )
        raise
    else:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "api_call_ok service=%s %s elapsed_ms=%d",
            service,
            detail,
            elapsed_ms,
        )
