"""Unit tests for HouseholdProfile.updated_with (phase-2 overlay)."""

from app.schemas import (
    HouseholdProfile,
    IntakeExtraction,
    SupplementalFacts,
)


def _profile(**overrides) -> HouseholdProfile:
    base = dict(state="NY", household_size=4, monthly_gross_income=12_000)
    base.update(overrides)
    return HouseholdProfile(**base)


def test_updated_with_all_none_keeps_carried_profile():
    # A pure question extracts nothing — every carried fact survives,
    # and the result compares equal so the router can skip the
    # engine/explanation/search re-run entirely.
    p = _profile(monthly_housing_cost=3_300, is_self_employed=True)
    assert p.updated_with(IntakeExtraction()) == p


def test_updated_with_non_null_facts_override():
    merged = _profile().updated_with(
        IntakeExtraction(monthly_gross_income=1_000, state="oh")
    )
    assert merged.monthly_gross_income == 1_000
    assert merged.state == "OH"
    assert merged.household_size == 4


def test_updated_with_supplemental_overlay():
    merged = _profile().updated_with(
        IntakeExtraction(),
        SupplementalFacts(monthly_housing_cost=2_000, is_veteran=True),
    )
    assert merged.monthly_housing_cost == 2_000
    assert merged.is_veteran is True
    assert merged.monthly_gross_income == 12_000


def test_updated_with_ignores_bookkeeping_fields():
    # missing_required/clarifying_question are IntakeExtraction
    # control-flow fields, not household facts — they must never
    # leak into the profile overlay.
    merged = _profile().updated_with(
        IntakeExtraction(
            missing_required=["state"],
            clarifying_question="which state?",
        )
    )
    assert merged == _profile()
