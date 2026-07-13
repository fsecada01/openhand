"""Medicare disability-pathway screening.

Under-65 Medicare eligibility rides on SSDI: coverage begins
automatically after 24 months of SSDI entitlement (the statutory
waiting period) — it is 24 months of *benefit entitlement*, not of
diagnosis. The wait is waived for ALS, and ESRD has its own
dialysis/transplant-based rules. People 65+ qualify by age.

Disability-related hardship is one of the largest mutual aid request
categories, so this screen also surfaces the SSDI pathway itself when
someone reports a disability but no SSDI income.
"""

from app.schemas import Determination, HouseholdProfile, Status

APPLY_URL = "https://www.ssa.gov/medicare/sign-up"
SOURCE_URL = "https://www.medicare.gov/basics/get-started-with-medicare"
DATA_VINTAGE = "Statutory rule (24-month SSDI waiting period)"
WAITING_MONTHS = 24


def _det(status: Status, reasons: list[str]) -> Determination:
    return Determination(
        program="medicare_disability",
        program_name="Medicare (disability pathway)",
        status=status,
        reasons=reasons,
        apply_url=APPLY_URL,
        data_vintage=DATA_VINTAGE,
        source_url=SOURCE_URL,
    )


def screen(profile: HouseholdProfile) -> Determination | None:
    age = profile.adult_age

    if age is not None and age >= 65:
        return _det(
            Status.likely_eligible,
            [
                "At 65 or older you qualify for Medicare by age, "
                "regardless of disability status.",
            ],
        )

    if profile.has_als_or_esrd:
        if profile.receives_ssdi:
            return _det(
                Status.likely_eligible,
                [
                    "With ALS, Medicare starts the same month SSDI "
                    "benefits begin — the 24-month wait is waived. "
                    "With end-stage renal disease, coverage is based "
                    "on dialysis or transplant dates.",
                ],
            )
        return _det(
            Status.possibly_eligible,
            [
                "ALS and end-stage renal disease have special "
                "Medicare rules that skip or shorten the usual "
                "24-month wait, but you need to apply through Social "
                "Security to start them.",
            ],
        )

    if profile.receives_ssdi:
        months = profile.months_on_ssdi
        if months is None:
            return _det(
                Status.possibly_eligible,
                [
                    "Medicare begins automatically after 24 months "
                    "of SSDI benefits. If you've received SSDI for "
                    "two years or more, you are likely already "
                    "enrolled or eligible now.",
                ],
            )
        if months >= WAITING_MONTHS:
            return _det(
                Status.likely_eligible,
                [
                    f"You've received SSDI for {months} months — "
                    "past the 24-month waiting period, so Medicare "
                    "enrollment is automatic (check for your card or "
                    "contact Social Security if it hasn't arrived).",
                ],
            )
        remaining = WAITING_MONTHS - months
        return _det(
            Status.likely_ineligible,
            [
                f"You've received SSDI for {months} months; Medicare "
                "starts automatically at month 25 — about "
                f"{remaining} more month(s).",
                "Until then, Medicaid or Marketplace coverage can "
                "bridge the gap (see the results above).",
            ],
        )

    if profile.has_elderly_or_disabled:
        return _det(
            Status.undetermined,
            [
                "Medicare's disability pathway runs through SSDI: "
                "you first qualify for SSDI (a qualifying disability "
                "plus work history), then Medicare begins after 24 "
                "months of benefits.",
                "If you haven't applied for SSDI (or SSI, which "
                "brings Medicaid instead), that application is the "
                "place to start: ssa.gov/benefits/disability.",
            ],
        )

    return None
