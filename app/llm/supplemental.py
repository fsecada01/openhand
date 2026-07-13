"""Second intake pass: optional facts that sharpen (never gate) results.

Kept as its own structured-output call, separate from `app.llm.intake`,
because `IntakeFacts` already sits right at Claude's schema complexity
limit (see its docstring) — a second flat model gets a fresh budget
instead of pushing the first one over. Nothing here is required: a
failed or empty extraction just means the engine falls back to its
existing, coarser behavior.
"""

from app import config
from app.llm.client import get_client, thinking_kwargs
from app.schemas import SupplementalFacts

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
    response = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": narrative}],
        output_format=SupplementalFacts,
        **thinking_kwargs(config.ANTHROPIC_MODEL, MAX_TOKENS),
    )
    return response.parsed_output
