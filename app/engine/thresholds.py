"""Published program thresholds; SNAP re-verified 2026-10-11 (FY2027).

Guideline-year is PER PROGRAM, not global: SNAP FY2027 uses the fixed
USDA COLA table (derived from 2026 FPL); Medicaid/CHIP screening in
mid-2026 uses the 2026 HHS poverty guidelines; EITC uses tax-year-2025
parameters (returns filed in 2026).

Sources:
- HHS poverty guidelines: https://aspe.hhs.gov/topics/
  poverty-economic-mobility/poverty-guidelines
- USDA SNAP FY2027 COLA memo (2026-08-21): https://www.usda.gov/sites/
  default/files/guidance-documents/fna.snap-cola2027.pdf
- KFF Medicaid expansion tracker: https://www.kff.org/medicaid/
  status-of-state-medicaid-expansion-decisions/
- IRS EITC tables (Rev. Proc. 2024-40): https://www.irs.gov/
  credits-deductions/individuals/earned-income-tax-credit
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
from types import MappingProxyType

# --- HHS poverty guidelines (annual dollars) -------------------------

FPL_2026 = {
    "default": {"first_person": 15_960, "each_additional": 5_680},
    "AK": {"first_person": 19_950, "each_additional": 7_100},
    "HI": {"first_person": 18_360, "each_additional": 6_530},
}


def fpl_annual(household_size: int, state: str) -> float:
    """2026 poverty guideline for a household, by state group."""
    table = FPL_2026.get(state, FPL_2026["default"])
    extra = (household_size - 1) * table["each_additional"]
    return table["first_person"] + extra


def fpl_monthly(household_size: int, state: str) -> float:
    return fpl_annual(household_size, state) / 12


# --- SNAP, 48 states + DC --------------------------------------------
# AK and HI have separate USDA tables not loaded yet -> undetermined.
# USDA resets every table on Oct 1; FY2026 is kept alongside the
# active year so a stale-vs-current regression stays visible.


@dataclass(frozen=True)
class SnapYear:
    """One fiscal year of SNAP COLA values for the 48 states + DC."""

    vintage: str
    source_url: str
    gross_monthly: Mapping[int, int]
    gross_each_additional: int
    net_monthly: Mapping[int, int]
    net_each_additional: int
    max_allotment: Mapping[int, int]
    allotment_each_additional: int
    minimum_allotment: int
    standard_deduction: Mapping[int, int]
    standard_deduction_6_plus: int
    shelter_deduction_cap: int
    asset_limit_general: int
    asset_limit_elderly_disabled: int

    def standard_deduction_for(self, size: int) -> int:
        if size >= 6:
            return self.standard_deduction_6_plus
        return self.standard_deduction[size]

    def __post_init__(self):
        # frozen=True is shallow; make the tables read-only too.
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, dict):
                object.__setattr__(self, f.name, MappingProxyType(value))


_SNAP_SOURCE = (
    "https://www.fns.usda.gov/snap/"
    "supplemental-nutrition-assistance-program-snap-"
    "income-eligibility-standards"
)
_SNAP_FY2027_COLA_SOURCE = (
    "https://www.usda.gov/sites/default/files/guidance-documents/"
    "fna.snap-cola2027.pdf"
)

SNAP_YEARS = {
    "FY2026": SnapYear(
        vintage="FY2026 (2025-10-01 to 2026-09-30)",
        source_url=_SNAP_SOURCE,
        gross_monthly={
            1: 1_696,
            2: 2_292,
            3: 2_888,
            4: 3_483,
            5: 4_079,
            6: 4_675,
            7: 5_271,
            8: 5_867,
        },
        gross_each_additional=596,
        net_monthly={
            1: 1_305,
            2: 1_763,
            3: 2_221,
            4: 2_680,
            5: 3_138,
            6: 3_596,
            7: 4_055,
            8: 4_513,
        },
        net_each_additional=459,
        max_allotment={
            1: 298,
            2: 546,
            3: 785,
            4: 994,
            5: 1_183,
            6: 1_421,
            7: 1_571,
            8: 1_789,
        },
        allotment_each_additional=218,
        minimum_allotment=24,
        standard_deduction={1: 209, 2: 209, 3: 209, 4: 223, 5: 261},
        standard_deduction_6_plus=299,
        shelter_deduction_cap=744,
        asset_limit_general=3_000,
        asset_limit_elderly_disabled=4_500,
    ),
    "FY2027": SnapYear(
        vintage="FY2027 (2026-10-01 to 2027-09-30)",
        source_url=_SNAP_FY2027_COLA_SOURCE,
        gross_monthly={
            1: 1_729,
            2: 2_345,
            3: 2_960,
            4: 3_575,
            5: 4_191,
            6: 4_806,
            7: 5_421,
            8: 6_037,
        },
        gross_each_additional=616,
        net_monthly={
            1: 1_330,
            2: 1_804,
            3: 2_277,
            4: 2_750,
            5: 3_224,
            6: 3_697,
            7: 4_170,
            8: 4_644,
        },
        net_each_additional=474,
        max_allotment={
            1: 306,
            2: 562,
            3: 808,
            4: 1_023,
            5: 1_217,
            6: 1_463,
            7: 1_616,
            8: 1_841,
        },
        allotment_each_additional=225,
        minimum_allotment=25,
        standard_deduction={1: 217, 2: 217, 3: 217, 4: 229, 5: 268},
        standard_deduction_6_plus=308,
        shelter_deduction_cap=769,
        asset_limit_general=3_000,
        asset_limit_elderly_disabled=4_750,
    ),
}

SNAP_ACTIVE_YEAR = "FY2027"
_SNAP = SNAP_YEARS[SNAP_ACTIVE_YEAR]

SNAP_STATES_COVERED = "48_states_dc"
SNAP_DATA_VINTAGE = _SNAP.vintage

SNAP_GROSS_MONTHLY = _SNAP.gross_monthly
SNAP_GROSS_EACH_ADDITIONAL = _SNAP.gross_each_additional
SNAP_NET_MONTHLY = _SNAP.net_monthly
SNAP_NET_EACH_ADDITIONAL = _SNAP.net_each_additional
SNAP_MAX_ALLOTMENT = _SNAP.max_allotment
SNAP_ALLOTMENT_EACH_ADDITIONAL = _SNAP.allotment_each_additional
SNAP_MIN_ALLOTMENT = _SNAP.minimum_allotment
SNAP_STANDARD_DEDUCTION = _SNAP.standard_deduction
SNAP_STANDARD_DEDUCTION_6_PLUS = _SNAP.standard_deduction_6_plus
SNAP_EARNED_INCOME_DEDUCTION_PCT = 0.20

# Excess shelter deduction cap, 48 states + DC. Uncapped for
# households with an elderly or disabled member.
SNAP_SHELTER_DEDUCTION_CAP = _SNAP.shelter_deduction_cap

# Elderly/disabled households can deduct unreimbursed medical expenses
# over this monthly floor. Statutory, so absent from the COLA memo;
# unchanged for FY2027.
SNAP_MEDICAL_EXPENSE_FLOOR = 35

# Federal asset limits: general, and for a household with an elderly
# (60+) or disabled member.
SNAP_ASSET_LIMIT_GENERAL = _SNAP.asset_limit_general
SNAP_ASSET_LIMIT_ELDERLY_DISABLED = _SNAP.asset_limit_elderly_disabled

# States that have NOT adopted Broad-Based Categorical Eligibility and
# so still apply the federal asset test above. A handful of other
# states (AR, ID, IN, NE, TX) use BBCE but with their own higher/custom
# asset limits — deliberately excluded here since those limits aren't
# sourced, so the app treats them like any other BBCE state (no asset
# gate) rather than guessing a wrong number. Source: USDA FNS BBCE
# overview + Propel (https://www.propel.app/snap/asset-limits-states/),
# verified 2026-07-13.
SNAP_ASSET_TEST_STATES = {"KS", "MS", "MO", "SD", "TN", "UT", "WY"}


def snap_limit(
    table: Mapping[int, int], each_additional: int, size: int
) -> int:
    if size <= 8:
        return table[size]
    return table[8] + (size - 8) * each_additional


def snap_standard_deduction(size: int) -> int:
    return _SNAP.standard_deduction_for(size)


# --- Medicaid / CHIP (mid-2026) ---------------------------------------

MEDICAID_DATA_VINTAGE = "2026 FPL guidelines; expansion map May 2026"
MEDICAID_NON_EXPANSION = {
    "AL",
    "FL",
    "GA",
    "KS",
    "MS",
    "SC",
    "TN",
    "TX",
    "WI",
    "WY",
}
MEDICAID_ADULT_EXPANSION_PCT = 1.38
# Nearly all states cover children to >=200% FPL; national median 255%.
CHILD_FLOOR_PCT = 2.00
CHILD_MEDIAN_PCT = 2.55
# Pregnant coverage: statutory floor 138%; 38 states at/above 200%.
PREGNANT_FLOOR_PCT = 1.38
PREGNANT_COMMON_PCT = 2.00

# --- EITC, tax year 2025 (filed in 2026) ------------------------------

EITC_DATA_VINTAGE = "Tax year 2025 (Rev. Proc. 2024-40)"
EITC_INVESTMENT_INCOME_LIMIT = 11_950
# {qualifying_children: (single/HoH limit, MFJ limit, max credit)}
EITC_TABLE = {
    0: (19_104, 26_214, 649),
    1: (50_434, 57_554, 4_328),
    2: (57_310, 64_430, 7_152),
    3: (61_555, 68_675, 8_046),
}
EITC_CHILDLESS_AGE_RANGE = (25, 64)


# --- Validity windows -------------------------------------------------


@dataclass(frozen=True)
class ThresholdSet:
    """One published table with the dates it may be applied to.

    `program` groups sets that compete for the same date ("snap",
    "medicaid", "eitc"); `key` names the set within the group.
    `effective_through` is inclusive. A date no set covers must never
    be answered with a computed result.
    """

    program: str
    key: str
    vintage: str
    effective_from: date
    effective_through: date
    source_url: str
    last_verified: date

    def covers(self, as_of: date) -> bool:
        return self.effective_from <= as_of <= self.effective_through


_POVERTY_SOURCE = (
    "https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines"
)
_EITC_SOURCE = (
    "https://www.irs.gov/credits-deductions/individuals/"
    "earned-income-tax-credit"
)

THRESHOLD_SETS = (
    ThresholdSet(
        program="snap",
        key="FY2026",
        vintage=SNAP_YEARS["FY2026"].vintage,
        effective_from=date(2025, 10, 1),
        effective_through=date(2026, 9, 30),
        source_url=_SNAP_SOURCE,
        last_verified=date(2026, 7, 13),
    ),
    ThresholdSet(
        program="snap",
        key="FY2027",
        vintage=SNAP_YEARS["FY2027"].vintage,
        effective_from=date(2026, 10, 1),
        effective_through=date(2027, 9, 30),
        source_url=_SNAP_SOURCE,
        last_verified=date(2026, 10, 11),
    ),
    # The 2026 HHS guidelines apply until the 2027 guidelines take
    # effect for Medicaid/CHIP, historically around April 1.
    ThresholdSet(
        program="medicaid",
        key="2026",
        vintage=MEDICAID_DATA_VINTAGE,
        effective_from=date(2026, 1, 1),
        effective_through=date(2027, 3, 31),
        source_url=_POVERTY_SOURCE,
        last_verified=date(2026, 7, 13),
    ),
    # Tax-year-2025 parameters serve returns filed during 2026; the
    # tax-year-2026 table is needed from 2027-01-01.
    ThresholdSet(
        program="eitc",
        key="TY2025",
        vintage=EITC_DATA_VINTAGE,
        effective_from=date(2026, 1, 1),
        effective_through=date(2026, 12, 31),
        source_url=_EITC_SOURCE,
        last_verified=date(2026, 7, 13),
    ),
)


def _check_snap_sets_match_years() -> None:
    """Fail at import if a SNAP window and its table drift apart."""
    keys = {ts.key for ts in THRESHOLD_SETS if ts.program == "snap"}
    if keys != set(SNAP_YEARS):
        raise RuntimeError(
            "SNAP validity windows and SNAP_YEARS disagree: "
            f"windows={sorted(keys)}, tables={sorted(SNAP_YEARS)}"
        )
    for ts in THRESHOLD_SETS:
        if ts.program == "snap" and ts.vintage != SNAP_YEARS[ts.key].vintage:
            raise RuntimeError(f"SNAP {ts.key} vintage mismatch")


_check_snap_sets_match_years()


def resolve(program: str, as_of: date) -> ThresholdSet | None:
    """The set for `program` whose window covers `as_of`, if any."""
    for ts in THRESHOLD_SETS:
        if ts.program == program and ts.covers(as_of):
            return ts
    return None
