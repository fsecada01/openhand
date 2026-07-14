default:
    @just --list

# --- Dev ---

install:
    uv sync --group dev

dev:
    uv run uvicorn app.main:app --reload

dev-port port:
    uv run uvicorn app.main:app --reload --port {{port}}

# --- Quality ---

lint:
    uv run ruff check . && uv run ruff format --check .

fmt:
    uv run ruff check --fix . && uv run ruff format .

test:
    uv run pytest

test-one path:
    uv run pytest {{path}}

check: lint test

# --- Docker ---

docker-build:
    docker compose build

docker-up:
    docker compose up --build -d

docker-down:
    docker compose down

docker-restart: docker-down docker-up

docker-logs:
    docker compose logs -f

docker-ps:
    docker compose ps

docker-shell:
    docker compose exec openhand /bin/bash

# Drops the named volume too — local sqlite data is gone after this.
docker-clean:
    docker compose down -v

# --- Claude Code ---

claude:
    claude

claude-p prompt:
    claude -p "{{prompt}}" --output-format json

# --- Misc ---

# Wipes the local dev sqlite file (not the Docker volume).
db-reset:
    rm -f openhand.db
