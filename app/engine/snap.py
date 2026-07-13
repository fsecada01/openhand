"""SNAP screening (48 states + DC, FY2026 USDA tables).

Screening-level test only: gross income test (130% FPL) plus an
estimated net income test (100% FPL) using the standard deduction and
the 20% earned income deduction. Shelter, dependent-care, and medical
deductions are not modeled, so a failed net test with deductions
unmodeled is reported as undetermined rather than ineligible where
those deductions could plausibly flip the result.
"""

from app.engine import thresholds as t
from app.schemas import Determination, HouseholdProfile, Status

APPLY_URL = "https://www.fns.usda.gov/snap/state-directory"
SOURCE_URL = (
    "https://www.usda.gov/sites/default/files/guidance-documents/"
    "fns.snap-cola-fy26memo.pdf"
)


def _det(status: Status, reasons: list[str], benefit: str | None = None):
    return Determination(
        program="snap",
        program_name="SNAP (food assistance)",
        status=status,
        reasons=reasons,
        estimated_benefit=benefit,
        apply_url=APPLY_URL,
        data_vintage=t.SNAP_DATA_VINTAGE,
        source_url=SOURCE_URL,
    )


def screen(profile: HouseholdProfile) -> Determination:
    if profile.state in ("AK", "HI"):
        return _det(
            Status.undetermined,
            [
                "Alaska and Hawaii use separate SNAP income tables "
                "that this screener does not include yet. Your state "
                "SNAP office can check for you."
            ],
        )

    size = profile.household_size
    income = profile.monthly_gross_income
    gross_limit = t.snap_limit(
        t.SNAP_GROSS_MONTHLY, t.SNAP_GROSS_EACH_ADDITIONAL, size
    )
    net_limit = t.snap_limit(
        t.SNAP_NET_MONTHLY, t.SNAP_NET_EACH_ADDITIONAL, size
    )
    max_allotment = t.snap_limit(
        t.SNAP_MAX_ALLOTMENT, t.SNAP_ALLOTMENT_EACH_ADDITIONAL, size
    )

    # Estimated net income: standard deduction + 20% of earned income.
    est_net = (
        income
        - t.snap_standard_deduction(size)
        - profile.earned * t.SNAP_EARNED_INCOME_DEDUCTION_PCT
    )
    est_net = max(est_net, 0)
    benefit = f"up to ${max_allotment}/month for {size} people"

    # Households with an elderly (60+) or disabled member skip the
    # gross test and are judged on net income alone.
    if profile.has_elderly_or_disabled:
        if est_net <= net_limit:
            return _det(
                Status.likely_eligible,
                [
                    "Households with an elderly or disabled member "
                    "only need to pass the net income test.",
                    f"Estimated net income ${est_net:,.0f} is within "
                    f"the ${net_limit:,}/month limit for {size} "
                    "people.",
                ],
                benefit,
            )
        return _det(
            Status.undetermined,
            [
                f"Estimated net income ${est_net:,.0f} is above the "
                f"${net_limit:,}/month limit, but medical and housing "
                "cost deductions (not estimated here) often change "
                "this for elderly or disabled households. Worth "
                "applying or asking your SNAP office.",
            ],
        )

    if income > gross_limit:
        return _det(
            Status.likely_ineligible,
            [
                f"Monthly income ${income:,.0f} is above the "
                f"${gross_limit:,} gross limit (130% of poverty) for "
                f"{size} people.",
            ],
        )

    if est_net <= net_limit:
        return _det(
            Status.likely_eligible,
            [
                f"Monthly income ${income:,.0f} is within the "
                f"${gross_limit:,} gross limit for {size} people.",
                f"Estimated net income ${est_net:,.0f} is within the "
                f"${net_limit:,} net limit.",
            ],
            benefit,
        )

    return _det(
        Status.possibly_eligible,
        [
            f"Monthly income ${income:,.0f} passes the gross test, "
            "and housing or childcare cost deductions (not estimated "
            "here) may bring net income under the "
            f"${net_limit:,} limit.",
        ],
        benefit,
    )
