"""Published program thresholds, verified 2026-07-13.

Guideline-year is PER PROGRAM, not global: SNAP FY2026 uses the fixed
USDA COLA table (derived from 2025 FPL); Medicaid/CHIP screening in
mid-2026 uses the 2026 HHS poverty guidelines; EITC uses tax-year-2025
parameters (returns filed in 2026).

Sources:
- HHS poverty guidelines: https://aspe.hhs.gov/topics/
  poverty-economic-mobility/poverty-guidelines
- USDA FNS SNAP FY2026 COLA memo: https://www.usda.gov/sites/default/
  files/guidance-documents/fns.snap-cola-fy26memo.pdf
- KFF Medicaid expansion tracker: https://www.kff.org/medicaid/
  status-of-state-medicaid-expansion-decisions/
- IRS EITC tables (Rev. Proc. 2024-40): https://www.irs.gov/
  credits-deductions/individuals/earned-income-tax-credit
"""

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


# --- SNAP FY2026 (Oct 2025 – Sep 2026), 48 states + DC ---------------
# AK and HI have separate USDA tables not loaded yet -> undetermined.

SNAP_STATES_COVERED = "48_states_dc"
SNAP_DATA_VINTAGE = "FY2026 (2025-10-01 to 2026-09-30)"

SNAP_GROSS_MONTHLY = {
    1: 1_696,
    2: 2_292,
    3: 2_888,
    4: 3_483,
    5: 4_079,
    6: 4_675,
    7: 5_271,
    8: 5_867,
}
SNAP_GROSS_EACH_ADDITIONAL = 596

SNAP_NET_MONTHLY = {
    1: 1_305,
    2: 1_763,
    3: 2_221,
    4: 2_680,
    5: 3_138,
    6: 3_596,
    7: 4_055,
    8: 4_513,
}
SNAP_NET_EACH_ADDITIONAL = 459

SNAP_MAX_ALLOTMENT = {
    1: 298,
    2: 546,
    3: 785,
    4: 994,
    5: 1_183,
    6: 1_421,
    7: 1_571,
    8: 1_789,
}
SNAP_ALLOTMENT_EACH_ADDITIONAL = 218

SNAP_STANDARD_DEDUCTION = {1: 209, 2: 209, 3: 209, 4: 223, 5: 261}
SNAP_STANDARD_DEDUCTION_6_PLUS = 299
SNAP_EARNED_INCOME_DEDUCTION_PCT = 0.20


def snap_limit(table: dict, each_additional: int, size: int) -> int:
    if size <= 8:
        return table[size]
    return table[8] + (size - 8) * each_additional


def snap_standard_deduction(size: int) -> int:
    if size >= 6:
        return SNAP_STANDARD_DEDUCTION_6_PLUS
    return SNAP_STANDARD_DEDUCTION[size]


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
