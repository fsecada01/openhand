"""Second intake pass: optional facts that sharpen (never gate) results.

Kept separate from `app.llm.intake`, because `IntakeFacts` already
sits right at Claude's schema complexity limit (see its docstring) —
a second pass gets a fresh budget instead of pushing the first one
over. Split into two smaller sequential structured-output calls
(`SupplementalHousingFacts`, `SupplementalSelfEmploymentFacts`)
rather than one 13-field call, after repeated grammar-compilation
failures (400 timeout, 400 too-complex, 503 overloaded_error) on the
single combined schema. Nothing here is required: a failed or empty
extraction just means the engine falls back to its existing, coarser
behavior — and a failure in one half no longer costs the other half.
"""

import logging

from app import config
from app.llm.client import get_client, thinking_kwargs
from app.logging_utils import log_api_call
from app.schemas import (
    SupplementalFacts,
    SupplementalHousingFacts,
    SupplementalSelfEmploymentFacts,
)

logger = logging.getLogger(__name__)

MAX_TOKENS = 4096

SYSTEM = """\
You extract optional supplemental household facts from a person's own
description of their situation, for a US benefits eligibility
screener. These facts sharpen results but are never required.

Rules:
- Extract ONLY facts the person actually stated. Never guess, infer
  from stereotypes, or fill in typical values. Leave a field null if
  it wasn't mentioned.
- Normalize dollar amounts to a monthly figure (annual / 12, weekly x
  4.33, biweekly x 2.17).
- If self-employed, only fill business_structure/wages/distributions
  when the person's own words distinguish them — never infer an
  S-Corp from context alone.
- Never include names, phone numbers, or other identifying details in
  any output field.
"""


def extract_supplemental(narrative: str) -> SupplementalFacts:
    client = get_client()
    housing = _extract_one(
        client,
        narrative,
        SupplementalHousingFacts,
        "anthropic.supplemental_housing",
    )
    self_employment = _extract_one(
        client,
        narrative,
        SupplementalSelfEmploymentFacts,
        "anthropic.supplemental_self_employment",
    )
    return SupplementalFacts(
        **housing.model_dump(), **self_employment.model_dump()
    )


def _extract_one(client, narrative: str, schema: type, service: str):
    """Run one structured-output pass; degrade to an empty schema on failure.

    Each half is independent — an overload or compilation failure on
    one pass must not cost the other half its facts.
    """
    try:
        with log_api_call(logger, service, model=config.ANTHROPIC_MODEL):
            response = client.messages.parse(
                model=config.ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM,
                messages=[{"role": "user", "content": narrative}],
                output_format=schema,
                **thinking_kwargs(config.ANTHROPIC_MODEL, MAX_TOKENS),
            )
        return response.parsed_output
    except Exception:
        return schema()
