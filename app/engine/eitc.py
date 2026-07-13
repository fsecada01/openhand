"""EITC screening, tax year 2025 (returns filed in 2026)."""

from app.engine import thresholds as t
from app.schemas import Determination, FilingStatus, HouseholdProfile, Status

APPLY_URL = (
    "https://www.irs.gov/credits-deductions/individuals/"
    "earned-income-tax-credit"
)


def _det(status, reasons, benefit=None):
    return Determination(
        program="eitc",
        program_name="Earned Income Tax Credit (EITC)",
        status=status,
        reasons=reasons,
        estimated_benefit=benefit,
        apply_url=APPLY_URL,
        data_vintage=t.EITC_DATA_VINTAGE,
        source_url=APPLY_URL,
    )


def screen(profile: HouseholdProfile) -> Determination:
    # S-Corp: only W-2 wages count as earned income (K-1 distributions
    # are explicitly excluded by the IRS). Sole proprietor/1099: net
    # profit, not gross receipts. Everyone else: unchanged.
    annual_earned = profile.eitc_earned_income_monthly * 12
    if annual_earned <= 0:
        return _det(
            Status.likely_ineligible,
            [
                "The EITC requires income from work (a job or "
                "self-employment) during the tax year.",
            ],
        )

    invest = profile.annual_investment_income or 0
    if invest > t.EITC_INVESTMENT_INCOME_LIMIT:
        return _det(
            Status.likely_ineligible,
            [
                f"Investment income ${invest:,.0f} is over the "
                f"${t.EITC_INVESTMENT_INCOME_LIMIT:,} limit.",
            ],
        )

    kids = min(profile.num_children, 3)
    single_limit, mfj_limit, max_credit = t.EITC_TABLE[kids]
    is_mfj = profile.filing_status == FilingStatus.married_joint
    limit = mfj_limit if is_mfj else single_limit
    # Self-employed/S-Corp households: use the same MAGI-style figure
    # as Medicaid (falls back to unchanged monthly_gross_income when
    # not self-employed) rather than raw gross receipts.
    annual = profile.magi_income_monthly * 12

    if kids == 0:
        lo, hi = t.EITC_CHILDLESS_AGE_RANGE
        if profile.adult_age is not None and not (
            lo <= profile.adult_age <= hi
        ):
            return _det(
                Status.likely_ineligible,
                [
                    "Without qualifying children, the EITC requires "
                    f"the filer to be {lo}-{hi} years old.",
                ],
            )

    if annual > limit:
        return _det(
            Status.likely_ineligible,
            [
                f"Estimated annual income ${annual:,.0f} is above the "
                f"${limit:,} limit for "
                f"{'3 or more' if kids == 3 else kids} qualifying "
                "children.",
            ],
        )

    benefit = f"up to ${max_credit:,} when you file your tax return"
    reasons = [
        f"You have income from work and estimated annual income "
        f"${annual:,.0f} is within the ${limit:,} limit for "
        f"{'3 or more' if kids == 3 else kids} qualifying children.",
    ]
    if kids > 0:
        reasons.append(
            "Note: the IRS 'qualifying child' test also checks "
            "relationship, residency (lived with you more than half "
            "the year), and that the child doesn't file a joint "
            "return — worth double-checking each child against those "
            "rules before filing."
        )
    if kids == 0 and profile.adult_age is None:
        reasons.append(
            "Note: with no qualifying children you must be 25-64 "
            "years old to claim it."
        )
        return _det(Status.possibly_eligible, reasons, benefit)
    return _det(Status.likely_eligible, reasons, benefit)
