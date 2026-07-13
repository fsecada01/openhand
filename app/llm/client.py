"""Shared Anthropic client.

The key is read from `.env` via decouple (not implicitly from
os.environ) so it stays under python-decouple's single source of
truth. Falls back to the SDK's own environment resolution when the
.env entry is empty.
"""

import os
from functools import lru_cache

import anthropic

from app import config


class LLMNotConfiguredError(RuntimeError):
    """No Anthropic API key available in .env or the environment."""


def thinking_kwargs(model: str, max_tokens: int) -> dict:
    """Build the `thinking` kwarg for a `messages.parse`/`create` call.

    Temporary compatibility shim: Haiku 4.5 rejects `thinking: {"type":
    "adaptive"}` with a 400 and only supports manual extended thinking
    (`type: "enabled"` + `budget_tokens`, which must be < max_tokens),
    while every other current model (Sonnet 5, Opus 4.8, Fable 5,
    etc.) uses `adaptive`. Drop the branch once a future Haiku model
    supports `adaptive`.
    """
    if "haiku" in model:
        return {
            "thinking": {
                "type": "enabled",
                "budget_tokens": max(1024, max_tokens // 2),
            }
        }
    return {"thinking": {"type": "adaptive"}}


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    key = config.ANTHROPIC_API_KEY.get_secret_value()
    if key:
        return anthropic.Anthropic(api_key=key)
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
        "ANTHROPIC_AUTH_TOKEN"
    ):
        return anthropic.Anthropic()
    raise LLMNotConfiguredError(
        "Set ANTHROPIC_API_KEY in .env or the environment."
    )
