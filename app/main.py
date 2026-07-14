"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.db import init_db
from app.logging_config import configure_logging
from app.routers import api_v1, screen

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="OpenHand",
    description="Needs-based benefits & mutual aid navigator (POC)",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = screen.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(screen.router)
app.include_router(api_v1.router)


@app.get("/healthz")
async def healthz():
    """Liveness check for the container/orchestrator — no DB or LLM."""
    return {"status": "ok"}
