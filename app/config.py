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
# result, with a fallback if it fails — a lighter model than intake
# is fine. Haiku 4.5 (current gen) rejects `thinking: adaptive`, and
# this pass doesn't use extended thinking anyway, so it would also
# work — but Sonnet is the steadier default until a newer Haiku ships.
ANTHROPIC_EXPLAIN_MODEL: str = config(
    "ANTHROPIC_EXPLAIN_MODEL", default="claude-sonnet-5"
)

DATABASE_URL: str = config("DATABASE_URL", default="sqlite:///./openhand.db")

# Privacy-first: raw narratives are NOT persisted unless explicitly
# enabled (e.g., for local debugging). Never enable in production.
STORE_NARRATIVES: bool = config("STORE_NARRATIVES", default=False, cast=bool)

RATE_LIMIT_SCREEN: str = config("RATE_LIMIT_SCREEN", default="10/minute")
