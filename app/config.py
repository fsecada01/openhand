"""Application settings loaded via python-decouple.

Secrets stay in `.env` (see `.env.example`). ANTHROPIC_API_KEY is
wrapped in a SecretStr so it never leaks into logs or repr output.
"""

from decouple import config
from pydantic import SecretStr

ANTHROPIC_API_KEY: SecretStr = SecretStr(
    config("ANTHROPIC_API_KEY", default="")
)

# Intake extraction: feeds the deterministic engine directly, so
# accuracy (income-unit math, refusing to guess) matters more than
# cost — default to a stronger model.
ANTHROPIC_MODEL: str = config("ANTHROPIC_MODEL", default="claude-opus-4-8")

# Explanation pass: constrained rewording of an already-decided
# result, with a fallback if it fails — a lighter, cheaper model than
# intake is fine here. Haiku 4.5 rejects `thinking: adaptive` but does
# support manual extended thinking (`type: "enabled"` + budget_tokens)
# if this pass ever needs it; it doesn't today, since it's rewording,
# not reasoning, so Haiku is a safe default either way.
ANTHROPIC_EXPLAIN_MODEL: str = config(
    "ANTHROPIC_EXPLAIN_MODEL", default="claude-haiku-4-5"
)

DATABASE_URL: str = config("DATABASE_URL", default="sqlite:///./openhand.db")

# Optional: powers the "other resources to check" fallback search for
# programs the federal screen didn't match well. Feature is simply
# skipped (see app.services.resource_search) when unset.
TAVILY_API_KEY: SecretStr = SecretStr(config("TAVILY_API_KEY", default=""))

# Privacy-first: raw narratives are NOT persisted unless explicitly
# enabled (e.g., for local debugging). Never enable in production.
STORE_NARRATIVES: bool = config("STORE_NARRATIVES", default=False, cast=bool)

RATE_LIMIT_SCREEN: str = config("RATE_LIMIT_SCREEN", default="10/minute")

# Controls verbosity of app.* loggers (see app.logging_config). INFO
# surfaces one line per external API call (Anthropic/Tavily) with
# timing and outcome — no narrative content — for traceability.
LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
