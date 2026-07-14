import os

import pytest

# sqlmodel_crud_utils resolves its SQL dialect at import time.
os.environ.setdefault("SQL_DIALECT", "sqlite")


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """slowapi's in-memory limiter persists for the whole test session
    (no reset between tests) — without this, the total number of
    /screen or /api/v1/screen calls across the entire suite is
    silently bounded by RATE_LIMIT_SCREEN, regardless of which test
    made them.
    """
    from app.routers import api_v1, screen

    screen.limiter.reset()
    api_v1.limiter.reset()
    yield
