"""Application settings loaded via python-decouple.

Secrets stay in `.env` (see `.env.example`). ANTHROPIC_API_KEY is
wrapped in a SecretStr so it never leaks into logs or repr output.
"""

from decouple import config
from pydantic import SecretStr

ANTHROPIC_API_KEY: SecretStr = SecretStr(
    config("ANTHROPIC_API_KEY", default="")
)

# Model used for both intake extraction and explanation passes.
ANTHROPIC_MODEL: str = config("ANTHROPIC_MODEL", default="claude-opus-4-8")

DATABASE_URL: str = config("DATABASE_URL", default="sqlite:///./openhand.db")

# Privacy-first: raw narratives are NOT persisted unless explicitly
# enabled (e.g., for local debugging). Never enable in production.
STORE_NARRATIVES: bool = config("STORE_NARRATIVES", default=False, cast=bool)

RATE_LIMIT_SCREEN: str = config("RATE_LIMIT_SCREEN", default="10/minute")
