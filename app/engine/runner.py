"""Run every program screen against a household profile."""

from datetime import date

from app.engine import eitc, medicaid, medicare, snap
from app.engine import thresholds as t
from app.schemas import Determination, HouseholdProfile, Status

ENGINE_VERSION = "0.3.0-poc"


def _stale(
    program: str,
    name: str,
    group: str,
    as_of: date,
    apply_url: str,
) -> Determination:
    """Fail-safe result for a date no published table covers."""
    windows = [ts for ts in t.THRESHOLD_SETS if ts.program == group]
    covered = ", ".join(
        f"{ts.effective_from} to {ts.effective_through}" for ts in windows
    )
    return Determination(
        program=program,
        program_name=name,
        status=Status.undetermined,
        reasons=[
            f"This screener's {name} figures only cover {covered}, "
            f"and {as_of} is outside that range, so it can't give a "
            "result. Please check with the agency directly."
        ],
        apply_url=apply_url,
        data_vintage=f"No published table covers {as_of}",
        source_url=windows[0].source_url,
        data_stale=True,
    )


def evaluate(
    profile: HouseholdProfile, as_of: date | None = None
) -> list[Determination]:
    """Screen `profile` against the tables in force on `as_of`.

    `as_of` defaults to today. A program with no table covering the
    date reports `undetermined` with `data_stale`, never a computed
    result.
    """
    as_of = as_of or date.today()
    results: list[Determination | None] = []

    snap_set = t.resolve("snap", as_of)
    if snap_set:
        results.append(snap.screen(profile, t.SNAP_YEARS[snap_set.key]))
    else:
        results.append(
            _stale("snap", snap.PROGRAM_NAME, "snap", as_of, snap.APPLY_URL)
        )

    if t.resolve("medicaid", as_of):
        results += [
            medicaid.screen_adult(profile),
            medicaid.screen_children(profile),
            medicaid.screen_pregnant(profile),
        ]
    else:
        results += [
            _stale(program, name, "medicaid", as_of, medicaid.APPLY_URL)
            for program, name in medicaid.applicable_programs(profile)
        ]

    results.append(medicare.screen(profile))

    if t.resolve("eitc", as_of):
        results.append(eitc.screen(profile))
    else:
        results.append(
            _stale(
                "eitc",
                "Earned Income Tax Credit (EITC)",
                "eitc",
                as_of,
                eitc.APPLY_URL,
            )
        )
    return [d for d in results if d is not None]
