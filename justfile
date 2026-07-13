dev:
    uv run uvicorn app.main:app --reload

lint:
    uv run ruff check . && uv run ruff format --check .

fmt:
    uv run ruff check --fix . && uv run ruff format .

test:
    uv run pytest
