"""Unit tests for individual program screens and the architecture
rule that the engine package never touches the LLM layer.
"""

from pathlib import Path

from app.engine import eitc, medicaid, medicare, snap, thresholds
from app.schemas import HouseholdProfile, Status


def profile(**kw) -> HouseholdProfile:
    base = {
        "state": "OH",
        "household_size": 1,
        "monthly_gross_income": 1000,
    }
    base.update(kw)
    return HouseholdProfile(**base)


# --- architecture guard ------------------------------------------------


def test_engine_never_imports_llm():
    engine_dir = Path(snap.__file__).parent
    for py in engine_dir.glob("*.py"):
        source = py.read_text()
        assert "anthropic" not in source, f"LLM import in {py.name}"
        assert "app.llm" not in source, f"LLM import in {py.name}"


# --- thresholds --------------------------------------------------------


def test_fpl_2026_contiguous():
    assert thresholds.fpl_annual(1, "OH") == 15_960
    assert thresholds.fpl_annual(4, "OH") == 33_000
    assert thresholds.fpl_annual(1, "AK") == 19_950
    assert thresholds.fpl_annual(1, "HI") == 18_360


def test_snap_limit_extends_past_8():
    assert (
        thresholds.snap_limit(
            thresholds.SNAP_GROSS_MONTHLY,
            thresholds.SNAP_GROSS_EACH_ADDITIONAL,
            10,
        )
        == 5_867 + 2 * 596
    )


# --- SNAP ---------------------------------------------------------------


def test_snap_gross_fail():
    d = snap.screen(profile(monthly_gross_income=2_000))
    assert d.status == Status.likely_ineligible


def test_snap_elderly_skips_gross_test():
    d = snap.screen(
        profile(
            monthly_gross_income=1_400,
            monthly_earned_income=0,
            has_elderly_or_disabled=True,
        )
    )
    assert d.status == Status.likely_eligible


# --- EITC ---------------------------------------------------------------


def test_eitc_requires_earned_income():
    d = eitc.screen(profile(monthly_earned_income=0))
    assert d.status == Status.likely_ineligible


def test_eitc_childless_age_gate():
    d = eitc.screen(profile(monthly_gross_income=1_000, adult_age=22))
    assert d.status == Status.likely_ineligible


def test_eitc_investment_income_gate():
    d = eitc.screen(profile(annual_investment_income=12_000, adult_age=30))
    assert d.status == Status.likely_ineligible


# --- Medicare disability -------------------------------------------------


def test_medicare_absent_without_disability_signal():
    assert medicare.screen(profile(adult_age=30)) is None


def test_medicare_ssdi_waiting_period_boundary():
    d24 = medicare.screen(profile(receives_ssdi=True, months_on_ssdi=24))
    d23 = medicare.screen(profile(receives_ssdi=True, months_on_ssdi=23))
    assert d24.status == Status.likely_eligible
    assert d23.status == Status.likely_ineligible


def test_medicare_als_waiver():
    d = medicare.screen(profile(receives_ssdi=True, has_als_or_esrd=True))
    assert d.status == Status.likely_eligible


def test_medicare_disabled_without_ssdi_points_to_pathway():
    d = medicare.screen(profile(has_elderly_or_disabled=True))
    assert d.status == Status.undetermined
    assert any("SSDI" in r for r in d.reasons)


# --- SNAP: shelter/dependent-care/medical deductions ---------------------


def test_snap_shelter_deduction_uncapped_flips_elderly_household():
    baseline = snap.screen(
        profile(
            monthly_gross_income=1_600,
            monthly_earned_income=0,
            has_elderly_or_disabled=True,
        )
    )
    assert baseline.status == Status.undetermined

    with_shelter = snap.screen(
        profile(
            monthly_gross_income=1_600,
            monthly_earned_income=0,
            has_elderly_or_disabled=True,
            monthly_housing_cost=800,
            monthly_utility_cost=100,
        )
    )
    assert with_shelter.status == Status.likely_eligible


def test_snap_shelter_deduction_capped_for_non_elderly():
    d = snap.screen(
        profile(
            household_size=8,
            monthly_gross_income=5_867,
            monthly_earned_income=0,
            monthly_housing_cost=3_000,
            monthly_utility_cost=1_000,
        )
    )
    # Even after the (capped, non-elderly) shelter deduction, net
    # income stays above the size-8 net limit.
    assert d.status == Status.possibly_eligible


def test_snap_dependent_care_deduction_flips_result():
    baseline = snap.screen(
        profile(monthly_gross_income=1_600, monthly_earned_income=0)
    )
    assert baseline.status == Status.possibly_eligible

    with_dependent_care = snap.screen(
        profile(
            monthly_gross_income=1_600,
            monthly_earned_income=0,
            monthly_dependent_care_cost=100,
        )
    )
    assert with_dependent_care.status == Status.likely_eligible


def test_snap_medical_deduction_only_over_floor_for_elderly():
    d = snap.screen(
        profile(
            monthly_gross_income=1_600,
            monthly_earned_income=0,
            has_elderly_or_disabled=True,
            monthly_medical_expenses=135,
        )
    )
    assert d.status == Status.likely_eligible


# --- SNAP: asset test ------------------------------------------------------


def test_snap_asset_test_fails_in_covered_state():
    d = snap.screen(
        profile(
            state="KS",
            monthly_gross_income=800,
            monthly_earned_income=800,
            liquid_assets=5_000,
        )
    )
    assert d.status == Status.likely_ineligible
    assert any("asset" in r.lower() for r in d.reasons)


def test_snap_asset_test_ignored_outside_covered_states():
    d = snap.screen(
        profile(
            monthly_gross_income=800,
            monthly_earned_income=800,
            liquid_assets=50_000,
        )
    )
    assert d.status == Status.likely_eligible


# --- SNAP: self-employment -------------------------------------------------


def test_snap_self_employed_sole_prop_uses_net_income():
    d = snap.screen(
        profile(
            monthly_gross_income=5_000,
            is_self_employed=True,
            monthly_gross_receipts=5_000,
            monthly_business_expenses=4_200,
        )
    )
    assert d.status == Status.likely_eligible


def test_snap_self_employed_s_corp_not_substituted():
    d = snap.screen(
        profile(
            monthly_gross_income=5_000,
            is_self_employed=True,
            business_structure="s_corp",
            monthly_w2_wages_from_business=1_000,
            monthly_k1_distributions=4_000,
        )
    )
    assert d.status == Status.likely_ineligible


# --- Medicaid: MAGI + dedicated disability question -----------------------


def test_medicaid_magi_s_corp_uses_wages_plus_distributions():
    d = medicaid.screen_adult(
        profile(
            state="OH",
            monthly_gross_income=5_000,
            business_structure="s_corp",
            monthly_w2_wages_from_business=1_000,
            monthly_k1_distributions=200,
        )
    )
    assert d.status == Status.likely_eligible


def test_medicaid_magi_sole_prop_uses_net_profit():
    d = medicaid.screen_adult(
        profile(
            state="OH",
            monthly_gross_income=5_000,
            is_self_employed=True,
            monthly_gross_receipts=5_000,
            monthly_business_expenses=4_500,
        )
    )
    assert d.status == Status.likely_eligible


def test_medicaid_non_expansion_disability_gets_dedicated_reason():
    d = medicaid.screen_adult(
        profile(state="TX", monthly_gross_income=2_000, has_disability=True)
    )
    assert d.status == Status.undetermined
    assert any("disability" in r.lower() for r in d.reasons)


# --- EITC: self-employment + qualifying-child caveat -----------------------


def test_eitc_s_corp_excludes_k1_from_earned_income():
    d = eitc.screen(
        profile(
            monthly_gross_income=3_000,
            business_structure="s_corp",
            monthly_w2_wages_from_business=0,
            monthly_k1_distributions=3_000,
            adult_age=30,
        )
    )
    assert d.status == Status.likely_ineligible
    assert any("income from work" in r for r in d.reasons)


def test_eitc_s_corp_distributions_still_count_toward_income_limit():
    d = eitc.screen(
        profile(
            monthly_gross_income=5_500,
            business_structure="s_corp",
            monthly_w2_wages_from_business=500,
            monthly_k1_distributions=5_000,
            adult_age=30,
        )
    )
    assert d.status == Status.likely_ineligible


def test_eitc_qualifying_child_caveat_present():
    d = eitc.screen(
        profile(monthly_gross_income=1_000, num_children=1, adult_age=30)
    )
    assert d.status == Status.likely_eligible
    assert any("relationship" in r.lower() for r in d.reasons)


def test_eitc_qualifying_child_caveat_absent_without_children():
    d = eitc.screen(
        profile(monthly_gross_income=1_000, num_children=0, adult_age=30)
    )
    assert not any("relationship" in r.lower() for r in d.reasons)
