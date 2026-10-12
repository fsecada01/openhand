"""Validity windows: tables are selected by date and fail safe when stale."""

from datetime import date, datetime, timedelta

import pytest

from app.engine import evaluate, runner
from app.engine import thresholds as t
from app.engine.runner import us_today
from app.schemas import HouseholdProfile, Status

FY2026_DATE = date(2026, 6, 1)
FY2027_DATE = date(2026, 10, 15)
EXPIRY_WARNING_DAYS = 45


def profile(**kw) -> HouseholdProfile:
    base = {
        "state": "OH",
        "household_size": 1,
        "monthly_gross_income": 1_700,
        "monthly_earned_income": 1_700,
        "adult_age": 30,
    }
    base.update(kw)
    return HouseholdProfile(**base)


def by_program(determinations):
    return {d.program: d for d in determinations}


def test_default_as_of_is_us_today():
    explicit = evaluate(profile(), as_of=us_today())
    assert evaluate(profile()) == explicit


def test_us_today_never_runs_ahead_of_us_clocks(monkeypatch):
    class FakeNow:
        @staticmethod
        def now(tz):
            # 2026-10-01 05:00 UTC is still 2026-09-30 21:00 Pacific.
            return datetime(2026, 10, 1, 5, 0, tzinfo=tz)

    monkeypatch.setattr(runner, "datetime", FakeNow)
    assert us_today() == date(2026, 9, 30)


def test_snap_table_selected_by_date():
    # $1,700 gross is over the FY2026 1-person limit (1,696) but under
    # FY2027 (1,729).
    old = by_program(evaluate(profile(), as_of=FY2026_DATE))["snap"]
    new = by_program(evaluate(profile(), as_of=FY2027_DATE))["snap"]
    assert old.status == Status.likely_ineligible
    assert new.status == Status.likely_eligible
    assert "FY2026" in old.data_vintage
    assert "FY2027" in new.data_vintage
    assert "cola2027" not in old.source_url
    assert "cola2027" in new.source_url


@pytest.mark.parametrize("as_of", [date(2024, 1, 1), date(2099, 1, 1)])
def test_date_outside_every_window_is_undetermined(as_of):
    results = evaluate(profile(num_children=1, is_pregnant=True), as_of=as_of)
    by = by_program(results)
    for program in (
        "snap",
        "medicaid_adult",
        "medicaid_chip_children",
        "medicaid_pregnant",
        "eitc",
    ):
        d = by[program]
        assert d.status == Status.undetermined
        assert d.data_stale is True
        assert d.estimated_benefit is None
        assert d.apply_url.startswith("https://")
        assert d.source_url.startswith("https://")
        assert d.reasons


def test_covered_date_is_not_stale():
    for d in evaluate(profile(), as_of=FY2027_DATE):
        assert d.data_stale is False


def test_resolve_returns_none_outside_windows():
    assert t.resolve("snap", date(2020, 1, 1)) is None
    assert t.resolve("snap", FY2027_DATE).key == "FY2027"


def test_window_boundaries_are_inclusive():
    assert t.resolve("snap", date(2026, 9, 30)).key == "FY2026"
    assert t.resolve("snap", date(2026, 10, 1)).key == "FY2027"
    assert t.resolve("snap", date(2027, 9, 30)).key == "FY2027"
    assert t.resolve("snap", date(2027, 10, 1)) is None


def test_every_set_carries_provenance():
    for ts in t.THRESHOLD_SETS:
        assert ts.effective_from < ts.effective_through
        assert ts.source_url.startswith("https://")
        assert ts.last_verified <= date.today()


def test_no_threshold_set_expires_within_45_days():
    cutoff = date.today() + timedelta(days=EXPIRY_WARNING_DAYS)
    expiring = [
        f"{ts.program}/{ts.key} ends {ts.effective_through}"
        for ts in t.THRESHOLD_SETS
        if ts.effective_from <= date.today() <= ts.effective_through
        and ts.effective_through <= cutoff
    ]
    assert not expiring, f"load the next table before: {expiring}"


@pytest.mark.parametrize("program", ["snap", "medicaid", "eitc"])
def test_a_set_covers_today(program):
    assert t.resolve(program, date.today()) is not None


def test_snap_windows_and_tables_must_match(monkeypatch):
    t._check_snap_sets_match_years()
    monkeypatch.setitem(t.SNAP_YEARS, "FY2099", t.SNAP_YEARS["FY2027"])
    with pytest.raises(RuntimeError):
        t._check_snap_sets_match_years()


def test_stale_result_for_unknown_group_does_not_raise():
    from app.engine.runner import _stale

    d = _stale("x", "Program X", "nope", date(2026, 1, 1), "https://x.test/")
    assert d.data_stale is True
    assert d.status == Status.undetermined


def test_stale_reason_states_one_covered_span():
    from app.engine.runner import _stale

    d = _stale("snap", "SNAP", "snap", date(2024, 1, 1), "https://x.test/")
    assert d.reasons[0].count("2025-10-01") == 1
    assert "2027-09-30" in d.reasons[0]
