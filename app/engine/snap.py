"""SNAP screening (48 states + DC, FY2026 USDA tables).

Screening-level test only: gross income test (130% FPL, skipped for
elderly/disabled households) plus an estimated net income test (100%
FPL) using the standard deduction, the 20% earned income deduction,
and — when volunteered — the excess shelter, dependent-care, and
elderly/disabled medical expense deductions. A federal asset test
($3,000 general / $4,500 elderly-or-disabled) applies only in the
handful of states confirmed to still enforce it (no Broad-Based
Categorical Eligibility waiver); other states are treated as if the
test doesn't bind, since state-specific BBCE asset limits aren't
sourced here. When shelter/dependent-care/medical facts aren't
volunteered, a failed net test is reported as undetermined rather than
ineligible, since those deductions could plausibly flip the result.
"""

from app.engine import thresholds as t
from app.schemas import (
    BusinessStructure,
    Determination,
    HouseholdProfile,
    Status,
)

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

    asset_limit = (
        t.SNAP_ASSET_LIMIT_ELDERLY_DISABLED
        if profile.has_elderly_or_disabled
        else t.SNAP_ASSET_LIMIT_GENERAL
    )
    if (
        profile.state in t.SNAP_ASSET_TEST_STATES
        and profile.liquid_assets is not None
        and profile.liquid_assets > asset_limit
    ):
        return _det(
            Status.likely_ineligible,
            [
                f"{profile.state} still applies SNAP's federal asset "
                f"limit. Countable cash and bank balances "
                f"${profile.liquid_assets:,.0f} are above the "
                f"${asset_limit:,} limit for this household.",
            ],
        )

    size = profile.household_size
    # SNAP counts NET self-employment income (gross receipts minus
    # business costs), never gross receipts — substitute it for gross
    # income whenever it's available. There's no sourced SNAP-specific
    # rule for the S-Corp wage/distribution split, so rather than
    # falling back to a stale monthly_gross_income figure that can
    # silently disagree with what Medicaid/EITC show for the same
    # household in the same report, S-Corp households use the same
    # MAGI-style total (W-2 wages + K-1 distributions) Medicaid uses
    # for the income tests — that's the actual money reaching the
    # household. Only the W-2 wages count toward the 20% earned-income
    # deduction below, since K-1 distributions aren't earned income.
    self_employed_net = profile.self_employment_net_monthly
    is_s_corp = profile.business_structure == BusinessStructure.s_corp
    use_self_employment = (
        profile.is_self_employed
        and not is_s_corp
        and self_employed_net is not None
    )
    if use_self_employment:
        income = self_employed_net
        earned = self_employed_net
    elif is_s_corp:
        income = profile.magi_income_monthly
        earned = profile.eitc_earned_income_monthly
    else:
        income = profile.monthly_gross_income
        earned = profile.earned

    gross_limit = t.snap_limit(
        t.SNAP_GROSS_MONTHLY, t.SNAP_GROSS_EACH_ADDITIONAL, size
    )
    net_limit = t.snap_limit(
        t.SNAP_NET_MONTHLY, t.SNAP_NET_EACH_ADDITIONAL, size
    )
    max_allotment = t.snap_limit(
        t.SNAP_MAX_ALLOTMENT, t.SNAP_ALLOTMENT_EACH_ADDITIONAL, size
    )

    # Adjusted income: standard deduction, 20% of earned income,
    # dependent-care cost, and (elderly/disabled only) unreimbursed
    # medical expenses over the federal floor.
    dependent_care = profile.monthly_dependent_care_cost or 0
    medical_deduction = 0.0
    if profile.has_elderly_or_disabled and profile.monthly_medical_expenses:
        medical_deduction = max(
            profile.monthly_medical_expenses - t.SNAP_MEDICAL_EXPENSE_FLOOR, 0
        )
    adjusted = (
        income
        - t.snap_standard_deduction(size)
        - earned * t.SNAP_EARNED_INCOME_DEDUCTION_PCT
        - dependent_care
        - medical_deduction
    )
    adjusted = max(adjusted, 0)

    # Excess shelter deduction: shelter cost above half of adjusted
    # income, capped unless the household has an elderly or disabled
    # member (uncapped for them).
    shelter_costs = (profile.monthly_housing_cost or 0) + (
        profile.monthly_utility_cost or 0
    )
    excess_shelter = max(shelter_costs - 0.5 * adjusted, 0)
    if not profile.has_elderly_or_disabled:
        excess_shelter = min(excess_shelter, t.SNAP_SHELTER_DEDUCTION_CAP)
    est_net = max(adjusted - excess_shelter, 0)
    deductions_applied = (
        excess_shelter > 0 or dependent_care > 0 or medical_deduction > 0
    )
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
        if deductions_applied:
            return _det(
                Status.undetermined,
                [
                    f"Estimated net income ${est_net:,.0f}, after the "
                    "housing, dependent-care, and medical costs you "
                    "shared, is still above the "
                    f"${net_limit:,}/month limit. Other deductions "
                    "this screener doesn't estimate could still change "
                    "this — worth applying or asking your SNAP "
                    "office.",
                ],
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

    if deductions_applied:
        return _det(
            Status.possibly_eligible,
            [
                f"Monthly income ${income:,.0f} passes the gross "
                f"test. Estimated net income ${est_net:,.0f}, after "
                "the housing/dependent-care/medical costs you shared, "
                f"is still above the ${net_limit:,} limit, but other "
                "unestimated deductions could still bring it under.",
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
