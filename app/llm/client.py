"""Shared Anthropic client.

The key is read from `.env` via decouple (not implicitly from
os.environ) so it stays under python-decouple's single source of
truth. Falls back to the SDK's own environment resolution when the
.env entry is empty.
"""

from functools import lru_cache

import anthropic

from app import config


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    key = config.ANTHROPIC_API_KEY.get_secret_value()
    if key:
        return anthropic.Anthropic(api_key=key)
    return anthropic.Anthropic()
