"""Intake pass: plain-language narrative -> structured household facts.

Uses structured outputs (`client.messages.parse`) so the response is a
validated `IntakeExtraction`. The system prompt forbids guessing:
missing required facts come back as `missing_required` plus one
clarifying question, which the UI relays to the user.
"""

import logging

from app import config
from app.llm.client import get_client, thinking_kwargs
from app.logging_utils import log_api_call
from app.schemas import REQUIRED_FIELDS, IntakeExtraction, IntakeFacts

logger = logging.getLogger(__name__)

MAX_TOKENS = 4096

SYSTEM = """\
You extract household facts from a person's own description of their
situation, for a US benefits eligibility screener.

Rules:
- Extract ONLY facts the person actually stated. Never guess, infer
  from stereotypes, or fill in typical values.
- Normalize income to dollars per month (annual / 12, weekly x 4.33,
  biweekly x 2.17). "I make $18 an hour full time" means about
  $3,120/month (40 h/week x 4.33).
- Self-employment, contractor, freelance, or business income (S-Corp,
  1099, sole proprietor, etc.) still counts toward
  monthly_gross_income — convert whatever total figure the person
  states the same way as wage income. "$200K a year as a contractor"
  means monthly_gross_income is about $16,667. Don't leave
  monthly_gross_income null just because the income is
  self-employment/business income; a wage-vs-distribution or
  gross-vs-net breakdown is a separate, later question, not a reason
  to withhold this one.
- household_size counts the people who live and eat together,
  including the person writing. "Me and my two kids" = 3.
- If the person names a city, you may set the state only when it is
  unambiguous (e.g. "Brooklyn" -> NY). Otherwise leave state null.
- Never include names, phone numbers, or other identifying details in
  any output field.
"""


def extract(narrative: str, round_num: int = 1) -> IntakeExtraction:
    client = get_client()
    with log_api_call(logger, "anthropic.intake", model=config.ANTHROPIC_MODEL):
        response = client.messages.parse(
            model=config.ANTHROPIC_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": narrative}],
            output_format=IntakeFacts,
            **thinking_kwargs(config.ANTHROPIC_MODEL, MAX_TOKENS),
        )
    facts: IntakeFacts = response.parsed_output
    # What's missing, and the question to ask, are decided in Python
    # (not by the model) — see IntakeFacts' docstring for why.
    missing = [f for f in REQUIRED_FIELDS if getattr(facts, f) is None]
    question = None
    if missing:
        # `round_num` doubles as an attempt counter here — if the same
        # field is still missing a round or two later, repeating the
        # identical sentence verbatim reads as broken/stuck. Cycling
        # the preamble (not the underlying ask) keeps the wording
        # deterministic and auditable while feeling like a real
        # back-and-forth instead of a stuck loop.
        template = CLARIFY_TEMPLATES[(round_num - 1) % len(CLARIFY_TEMPLATES)]
        topics = ", ".join(ASK_PROMPTS[f] for f in missing)
        question = template.format(topics=topics)
    return IntakeExtraction(
        **facts.model_dump(),
        missing_required=missing,
        clarifying_question=question,
    )


ASK_PROMPTS = {
    "state": "which state you live in",
    "household_size": "how many people live and eat together at home",
    "monthly_gross_income": "about how much money your household "
    "brings in each month before taxes",
}

# Cycled by attempt number (see `extract`) so a still-missing field
# doesn't repeat the exact same sentence every round.
CLARIFY_TEMPLATES = [
    "Could you tell me a bit more — {topics}?",
    "Just to make sure I have this right — could you tell me {topics}?",
    "Sorry to circle back on this, but could you share {topics}?",
    "One more check before we run the numbers — could you confirm {topics}?",
]
