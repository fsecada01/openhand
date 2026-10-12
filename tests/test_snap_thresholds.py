"""SNAP threshold tables against the published USDA COLA memos.

FY2027 values come from the 2026-08-21 memo (effective 2026-10-01);
FY2026 is kept alongside so a regression to stale values is visible.
"""

import pytest

from app.engine import snap
from app.engine import thresholds as t
from app.schemas import Status
from tests.test_engine_units import profile

FY2027_GROSS = [1_729, 2_345, 2_960, 3_575, 4_191, 4_806, 5_421, 6_037]
FY2027_NET = [1_330, 1_804, 2_277, 2_750, 3_224, 3_697, 4_170, 4_644]
FY2027_MAX = [306, 562, 808, 1_023, 1_217, 1_463, 1_616, 1_841]
FY2027_STANDARD_DEDUCTION = {
    1: 217,
    2: 217,
    3: 217,
    4: 229,
    5: 268,
    6: 308,
    7: 308,
    8: 308,
}


def test_fy2027_tables_are_active():
    assert t.SNAP_ACTIVE_YEAR == "FY2027"
    assert "FY2027" in t.SNAP_DATA_VINTAGE
    assert "2026-10-01" in t.SNAP_DATA_VINTAGE


def test_fy2026_kept_alongside():
    fy26 = t.SNAP_YEARS["FY2026"]
    assert fy26.gross_monthly[1] == 1_696
    assert fy26.max_allotment[4] == 994
    assert fy26.shelter_deduction_cap == 744
    assert fy26.minimum_allotment == 24
    assert fy26.asset_limit_elderly_disabled == 4_500


@pytest.mark.parametrize("size", range(1, 9))
def test_fy2027_income_limits_and_allotments(size):
    i = size - 1
    assert (
        t.snap_limit(t.SNAP_GROSS_MONTHLY, t.SNAP_GROSS_EACH_ADDITIONAL, size)
        == FY2027_GROSS[i]
    )
    assert (
        t.snap_limit(t.SNAP_NET_MONTHLY, t.SNAP_NET_EACH_ADDITIONAL, size)
        == FY2027_NET[i]
    )
    assert (
        t.snap_limit(
            t.SNAP_MAX_ALLOTMENT, t.SNAP_ALLOTMENT_EACH_ADDITIONAL, size
        )
        == FY2027_MAX[i]
    )


@pytest.mark.parametrize("size", range(1, 9))
def test_fy2027_standard_deduction(size):
    assert t.snap_standard_deduction(size) == FY2027_STANDARD_DEDUCTION[size]


def test_fy2027_each_additional_member():
    assert t.SNAP_GROSS_EACH_ADDITIONAL == 616
    assert t.SNAP_NET_EACH_ADDITIONAL == 474
    assert t.SNAP_ALLOTMENT_EACH_ADDITIONAL == 225
    assert (
        t.snap_limit(t.SNAP_GROSS_MONTHLY, t.SNAP_GROSS_EACH_ADDITIONAL, 10)
        == 6_037 + 2 * 616
    )


def test_fy2027_shelter_cap_medical_floor_minimum_assets():
    assert t.SNAP_SHELTER_DEDUCTION_CAP == 769
    assert t.SNAP_MEDICAL_EXPENSE_FLOOR == 35
    assert t.SNAP_MIN_ALLOTMENT == 25
    assert t.SNAP_ASSET_LIMIT_GENERAL == 3_000
    assert t.SNAP_ASSET_LIMIT_ELDERLY_DISABLED == 4_750


def test_snap_source_is_fy2027_memo():
    assert "fna.snap-cola2027.pdf" in snap.SOURCE_URL
    d = snap.screen(profile())
    assert d.source_url == snap.SOURCE_URL
    assert d.data_vintage == t.SNAP_DATA_VINTAGE


def test_income_between_fy2026_and_fy2027_gross_limit_now_passes():
    # $1,700 > FY2026 1-person gross limit (1,696), <= FY2027 (1,729).
    # Earned income: 1,700 - 217 standard - 340 (20%) = 1,143 net, under
    # the FY2027 net limit of 1,330, so the result is a firm likely_eligible.
    income = 1_700
    assert income > t.SNAP_YEARS["FY2026"].gross_monthly[1]
    d = snap.screen(
        profile(monthly_gross_income=income, monthly_earned_income=income)
    )
    assert d.status == Status.likely_eligible
