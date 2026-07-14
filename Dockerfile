# Alpine rather than debian-slim: the slim image ships the Debian
# package backlog (perl-base, coreutils, sqlite3, ...) whose CVEs
# have no upstream fixes — Docker Scout flags 38 of them. The musl
# base drops that surface entirely; every binary dep (uvloop,
# httptools, pydantic-core, watchfiles) ships musllinux cp314 wheels.
FROM python:3.14-alpine AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
RUN uv sync --frozen --no-dev


FROM python:3.14-alpine
WORKDIR /app

RUN adduser -D -u 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app ./app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    SQL_DIALECT=sqlite \
    DATABASE_URL=sqlite:////app/data/openhand.db

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
