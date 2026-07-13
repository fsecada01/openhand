"""Intake pass: plain-language narrative -> structured household facts.

Uses structured outputs (`client.messages.parse`) so the response is a
validated `IntakeExtraction`. The system prompt forbids guessing:
missing required facts come back as `missing_required` plus one
clarifying question, which the UI relays to the user.
"""

from app import config
from app.llm.client import get_client, thinking_kwargs
from app.schemas import REQUIRED_FIELDS, IntakeExtraction, IntakeFacts

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
- household_size counts the people who live and eat together,
  including the person writing. "Me and my two kids" = 3.
- If the person names a city, you may set the state only when it is
  unambiguous (e.g. "Brooklyn" -> NY). Otherwise leave state null.
- Never include names, phone numbers, or other identifying details in
  any output field.
"""


def extract(narrative: str) -> IntakeExtraction:
    client = get_client()
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
        question = (
            "Could you tell me a bit more — "
            + ", ".join(ASK_PROMPTS[f] for f in missing)
            + "?"
        )
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
