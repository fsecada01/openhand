"""Unit tests for individual program screens and the architecture
rule that the engine package never touches the LLM layer.
"""

from pathlib import Path

from app.engine import eitc, medicare, snap, thresholds
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
