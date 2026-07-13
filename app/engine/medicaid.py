"""Medicaid / CHIP screening using 2026 HHS poverty guidelines.

Adult screening uses the ACA expansion MAGI limit (138% FPL) plus the
KFF non-expansion state list. Child and pregnancy screening uses
conservative national bands (floor 200% / median 255% for children;
floor 138% / common 200% for pregnancy) because exact upper limits are
state-specific — results between bands report possibly_eligible.
"""

from app.engine import thresholds as t
from app.schemas import Determination, HouseholdProfile, Status

APPLY_URL = "https://www.healthcare.gov/medicaid-chip/"
SOURCE_URL = (
    "https://www.kff.org/medicaid/status-of-state-medicaid-expansion-decisions/"
)


def _det(program, name, status, reasons):
    return Determination(
        program=program,
        program_name=name,
        status=status,
        reasons=reasons,
        apply_url=APPLY_URL,
        data_vintage=t.MEDICAID_DATA_VINTAGE,
        source_url=SOURCE_URL,
    )


def screen_adult(profile: HouseholdProfile) -> Determination:
    fpl = t.fpl_monthly(profile.household_size, profile.state)
    limit = fpl * t.MEDICAID_ADULT_EXPANSION_PCT
    income = profile.monthly_gross_income
    pct = income / fpl * 100

    if profile.state in t.MEDICAID_NON_EXPANSION:
        return _det(
            "medicaid_adult",
            "Medicaid (adults)",
            Status.undetermined,
            [
                f"{profile.state} has not expanded Medicaid to "
                "low-income adults, so adult eligibility depends on "
                "narrower state categories (pregnancy, disability, "
                "caring for young children).",
                "If your income is between 100% and 400% of poverty, "
                "you may instead qualify for reduced-cost Marketplace "
                "coverage at healthcare.gov.",
            ],
        )

    if income <= limit:
        return _det(
            "medicaid_adult",
            "Medicaid (adults)",
            Status.likely_eligible,
            [
                f"Monthly income ${income:,.0f} is about "
                f"{pct:.0f}% of the poverty level — within the 138% "
                f"expansion limit (${limit:,.0f}/month) for "
                f"{profile.household_size} people in {profile.state}.",
            ],
        )

    return _det(
        "medicaid_adult",
        "Medicaid (adults)",
        Status.likely_ineligible,
        [
            f"Monthly income ${income:,.0f} is about {pct:.0f}% of "
            "the poverty level, above the 138% expansion limit "
            f"(${limit:,.0f}/month).",
            "You may still qualify for subsidized Marketplace "
            "coverage at healthcare.gov.",
        ],
    )


def screen_children(profile: HouseholdProfile) -> Determination | None:
    if profile.num_children < 1:
        return None
    fpl = t.fpl_monthly(profile.household_size, profile.state)
    income = profile.monthly_gross_income
    pct = income / fpl * 100

    if income <= fpl * t.CHILD_FLOOR_PCT:
        status = Status.likely_eligible
        reasons = [
            f"Household income is about {pct:.0f}% of the poverty "
            "level. Nearly every state covers children through "
            "Medicaid/CHIP up to at least 200%.",
        ]
    elif income <= fpl * t.CHILD_MEDIAN_PCT:
        status = Status.possibly_eligible
        reasons = [
            f"Household income is about {pct:.0f}% of the poverty "
            "level — above the 200% floor but under the 255% national "
            "median CHIP limit. Coverage depends on your state's "
            "exact limit.",
        ]
    else:
        status = Status.possibly_eligible
        reasons = [
            f"Household income is about {pct:.0f}% of the poverty "
            "level, above most states' CHIP limits — but some states "
            "(e.g., NY) cover children up to roughly 400%. Check "
            "your state's limit.",
        ]
    return _det(
        "medicaid_chip_children",
        "Medicaid/CHIP (children)",
        status,
        reasons,
    )


def screen_pregnant(profile: HouseholdProfile) -> Determination | None:
    if not profile.is_pregnant:
        return None
    fpl = t.fpl_monthly(profile.household_size, profile.state)
    income = profile.monthly_gross_income
    pct = income / fpl * 100

    if income <= fpl * t.PREGNANT_FLOOR_PCT:
        status = Status.likely_eligible
        reasons = [
            f"Household income is about {pct:.0f}% of the poverty "
            "level — under the 138% floor every state must cover for "
            "pregnancy Medicaid.",
        ]
    elif income <= fpl * t.PREGNANT_COMMON_PCT:
        status = Status.likely_eligible
        reasons = [
            f"Household income is about {pct:.0f}% of the poverty "
            "level; 38 states cover pregnancy at or above 200%.",
        ]
    else:
        status = Status.possibly_eligible
        reasons = [
            f"Household income is about {pct:.0f}% of the poverty "
            "level — above 200%, but several states cover pregnancy "
            "higher (up to ~380%). Check your state's limit.",
        ]
    return _det(
        "medicaid_pregnant",
        "Medicaid (pregnancy)",
        status,
        reasons,
    )
