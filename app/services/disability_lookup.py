"""Deterministic keyword lookup against the DisabilityCondition table.

Scans the person's raw narrative for a named condition — not an
LLM-extracted field, since `IntakeFacts` already sits right at
Claude's structured-output schema complexity limit (see its
docstring) and one more optional field tips it over. Seed reference
data only (SSA's own published listings), never a decision: this
just tells the Medicare-pathway wording whether a named diagnosis is
among the conditions SSA already recognizes. The engine itself still
decides Medicare/SSDI status purely from `receives_ssdi` /
`months_on_ssdi` / `has_als_or_esrd`.
"""

import re

from sqlmodel import Session, select

from app.models import DisabilityCondition


def lookup(session: Session, narrative: str | None) -> str | None:
    text = (narrative or "").lower()
    if not text:
        return None
    for condition in session.exec(select(DisabilityCondition)):
        terms = [condition.name.lower(), *_aliases(condition.aliases)]
        if any(_contains_term(text, term) for term in terms if term):
            return f"{condition.name} ({condition.ssa_reference})"
    return None


def _aliases(raw: str) -> list[str]:
    return [a.strip().lower() for a in raw.split(",") if a.strip()]


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None
