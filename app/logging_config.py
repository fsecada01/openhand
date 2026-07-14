"""Root logging setup — call once at process startup.

Every line is formatted with the current request id (see
`app.logging_utils`) so the handful of log lines one /screen call
produces (intake, supplemental, explain, resource search) can be
traced back to a single request.
"""

import logging

from app import config
from app.logging_utils import RequestIdFilter


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
        )
    )
    root = logging.getLogger()
    root.setLevel(config.LOG_LEVEL)
    root.handlers = [handler]
