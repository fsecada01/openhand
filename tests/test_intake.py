"""Unit tests for the intake extraction pass.

The Anthropic client is mocked throughout — these must never hit the
live API (see tests/conftest.py and the project's own no-live-API
testing rule).
"""

from types import SimpleNamespace

from app.llm import intake
from app.schemas import IntakeFacts


def _fake_client(facts: IntakeFacts):
    response = SimpleNamespace(parsed_output=facts)
    messages = SimpleNamespace(parse=lambda **kwargs: response)
    return SimpleNamespace(messages=messages)


def test_extract_cycles_clarify_preamble_by_round(monkeypatch):
    incomplete = IntakeFacts(household_size=3, monthly_gross_income=2000)
    monkeypatch.setattr(intake, "get_client", lambda: _fake_client(incomplete))

    questions = [
        intake.extract("help", round_num=n).clarifying_question
        for n in range(1, len(intake.CLARIFY_TEMPLATES) + 1)
    ]

    # Same missing field every round, but the wording shouldn't repeat
    # verbatim within one full cycle of the template list.
    assert len(set(questions)) == len(questions)
    assert all("which state you live in" in q for q in questions)


def test_extract_preamble_wraps_around_after_template_count(monkeypatch):
    incomplete = IntakeFacts(state="OH", monthly_gross_income=2000)
    monkeypatch.setattr(intake, "get_client", lambda: _fake_client(incomplete))

    first = intake.extract("help", round_num=1).clarifying_question
    wrapped = intake.extract(
        "help", round_num=1 + len(intake.CLARIFY_TEMPLATES)
    ).clarifying_question

    assert first == wrapped


def test_extract_no_clarifying_question_when_nothing_missing(monkeypatch):
    complete = IntakeFacts(
        state="OH", household_size=2, monthly_gross_income=1500
    )
    monkeypatch.setattr(intake, "get_client", lambda: _fake_client(complete))

    result = intake.extract("help", round_num=3)

    assert result.missing_required == []
    assert result.clarifying_question is None
