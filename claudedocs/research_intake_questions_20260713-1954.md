# Research Report: Conversational Intake Question Coverage for OpenHand

**Date:** 2026-07-13
**Scope:** Compare OpenHand's current conversational-intake field set (`app/schemas.py:IntakeFacts`) against (a) the eligibility logic already implemented in `app/engine/*.py` and (b) published intake question sets from real-world benefits screeners, to identify what the intake is missing.
**Depth:** Standard (web search + primary-source engine read, 2 hops)
**Method:** No implementation performed — research only, per user request.

---

## Executive Summary

The current intake (`IntakeFacts`) asks for 13 facts: state, household size, gross/earned income, number of children, filing status, elderly-or-disabled flag, pregnancy, adult age, investment income, SSDI receipt + duration, and ALS/ESRD status. This is enough to run the five programs currently implemented (SNAP, Medicaid adult/child/pregnant, Medicare disability pathway, EITC) at a coarse, income-band level, but it is missing several fields that (1) every real-world screener researched asks as standard, and (2) the app's own engine code already flags as unmodeled gaps in its docstrings and comments. The most consequential gap is **citizenship/immigration status and SSN validity** — a hard eligibility gate for SNAP, Medicaid, and EITC alike — which the intake does not ask about at all, meaning the screener can currently return "likely eligible" for someone who is categorically barred, or the reverse, discourage a lawfully-present immigrant who does in fact qualify. The next-largest gaps are **housing/shelter cost, utility cost, dependent-care cost, and medical expenses for elderly/disabled members** — all four are the exact "deductions... not modeled" the SNAP module's own docstring calls out as the reason it reports `undetermined`/`possibly_eligible` instead of a firm result. Asking three or four extra questions would let a meaningful fraction of those soft results become firm ones.

A closely related gap, researched second at the user's request (§6): **self-employed and S-Corp households aren't a single "income" number.** SNAP counts net self-employment income after business expenses; Medicaid MAGI counts an S-Corp owner's W-2 wages *and* K-1 distributions together; EITC counts *only* W-2 wages for an S-Corp owner and explicitly excludes K-1 distributions from "earned income." A single `monthly_gross_income`/`monthly_earned_income` pair can't represent all three correctly at once for this population.

**Confidence:** High that the gaps listed below are real (each is either sourced from a government/nonprofit screener's published question set, an IRS/Medicaid primary source, or is directly visible in OpenHand's own engine code and docstrings). Moderate on prioritization — this is a judgment call about which gaps matter most for the app's Phase 1 program set, not an empirical finding.

---

## 1. What OpenHand Currently Asks

From `app/schemas.py:IntakeFacts` (fields the LLM extracts) and `HouseholdProfile` (what the engine consumes):

| Field | Used by |
|---|---|
| `state` | SNAP (AK/HI carve-out), Medicaid (FPL table + expansion status) |
| `household_size` | SNAP, Medicaid FPL |
| `monthly_gross_income` / `monthly_earned_income` | SNAP, Medicaid, EITC |
| `num_children` | Medicaid/CHIP children screen, EITC qualifying-children count |
| `filing_status` | EITC (married-filing-jointly limit only) |
| `has_elderly_or_disabled` | SNAP (skips gross test), Medicare (disability-pathway trigger) |
| `is_pregnant` | Medicaid pregnancy screen |
| `adult_age` | EITC childless-filer age band, Medicare age-65 rule |
| `annual_investment_income` | EITC investment-income cap |
| `receives_ssdi` / `months_on_ssdi` | Medicare 24-month waiting period |
| `has_als_or_esrd` | Medicare waiting-period waiver |
| `disability_diagnosis_match` (non-LLM, keyword-matched separately) | Medicare undetermined-branch wording only |

This set is sufficient to produce a result for every program currently implemented, but several of those results are explicitly softened (`possibly_eligible`/`undetermined`) because supporting facts aren't collected — see §2.

## 2. Gaps Visible in OpenHand's Own Engine Code

These aren't external opinions — they're gaps the app's own source already flags:

- **`app/engine/snap.py` docstring, verbatim:** *"Shelter, dependent-care, and medical deductions are not modeled, so a failed net test with deductions unmodeled is reported as undetermined rather than ineligible where those deductions could plausibly flip the result."* None of shelter cost, dependent-care cost, or elderly/disabled medical expense is an intake question today — all three are the direct cause of soft SNAP results.
- **`app/engine/medicaid.py:screen_adult`**, non-expansion-state branch, returns `undetermined` and tells the user eligibility "depends on narrower state categories (pregnancy, disability, caring for young children)" — but the intake never asks the disability question this branch is describing as a possible path (it only reuses `has_elderly_or_disabled`, which conflates elderly and disabled into one boolean and is framed around SNAP/Medicare, not asked in a way tailored to this Medicaid path).
- **`app/engine/eitc.py:screen`** counts `num_children` (defined in `IntakeFacts` as *"Children under 19 in the household"* — a SNAP-style headcount) directly as EITC "qualifying children," but the IRS qualifying-child test has independent relationship, residency (>half the year), and joint-return sub-tests (see §3.4) that a plain headcount can silently get wrong (e.g., a niece being informally raised, or a child who moved out mid-year).
- **`app/engine/eitc.py`** only special-cases `filing_status == married_joint` for the higher income limit; a `married` person filing **separately** (which collapses into `FilingStatus.other` in the current 4-value enum) is generally *disallowed* from EITC entirely under IRS rules, but the code doesn't distinguish that case from single/head-of-household.

## 3. What Real-World Screeners Ask That OpenHand Doesn't

### 3.1 Citizenship / immigration status — highest-priority gap
Every program OpenHand screens gates eligibility on immigration status, and OpenHand asks nothing about it:
- **Medicaid**: non-citizens need a "qualified" immigration status, and most qualified immigrants face a statutory **5-year bar** after obtaining that status (exceptions: refugees, asylees, and — at state option — children/pregnant people under ICHIA). [KFF](https://www.kff.org/medicaid/how-states-verify-citizenship-and-immigration-status-in-medicaid/), [Medicaid.gov implementation guide](https://www.medicaid.gov/resources-for-states/downloads/macpro-ig-citizenship-and-non-citizen-eligibility.pdf)
- **SNAP**: has its own, separately-defined set of eligible noncitizen categories (not identical to Medicaid's).
- **EITC**: requires a valid SSN (not an ITIN) for the filer, spouse, and every qualifying child.
This is the one gap that can flip a result from correct to actively wrong (falsely encouraging or falsely discouraging an applicant), so it's the highest-value addition even though it's also the most sensitive one to ask about — see §4 for a phrasing caveat.

### 3.2 Housing / shelter situation
NYC's own eligibility-screening API (the system behind ACCESS NYC, one of the strongest public precedents already cited in this project's own `CLAUDE.md`) collects explicit housing-status fields: `livingRentalType`, `livingRenting`, `livingOwner`, `livingStayingWithFriend`, `livingHotel`, `livingShelter`, `livingPreferNotToSay`, plus a `cashOnHand` asset field. [NYC Screening API docs](https://screeningapidocs.cityofnewyork.us/) OpenHand asks none of this today, even though shelter cost is the specific unmodeled SNAP deduction called out in §2, and housing status is the natural gateway to any future LIHEAP/HUD program (already named as backlog candidates in this project's own brainstorming doc).

### 3.3 Assets / resources
- **SNAP**: federal asset limit is $3,000 for most households, $4,500 if elderly/disabled — still binding in the roughly 10 states that haven't adopted Broad-Based Categorical Eligibility (BBCE) to waive it. [CBPP SNAP guide](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits)
- **TANF**: resource limit around $1,000 in many states.
- **LIHEAP**: asset tests where used range roughly $2,000–$25,000 depending on state. [LIHEAP Clearinghouse](https://liheapch.acf.gov/tables/assets.htm)
OpenHand has no asset/resource question at all; today it implicitly assumes every household passes any asset test, which is only true in BBCE states.

### 3.4 EITC qualifying-child sub-tests
The IRS qualifying-child test for EITC has three independent parts beyond a raw headcount: **relationship** (child/stepchild/foster/sibling or their descendant), **residency** (lived with filer in the US more than half the year), and a joint-return restriction, plus a valid SSN. [IRS qualifying child rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/qualifying-child-rules) OpenHand's `num_children` doesn't probe any of these — it's borrowed wholesale from the SNAP household-composition concept.

### 3.5 Veteran status
NCOA's BenefitsCheckUp — a long-running, well-established senior/disability benefits screener — asks veteran status explicitly, because it gates VA disability and pension programs and because veterans' and disability benefits count toward the SNAP income test differently. [NCOA BenefitsCheckUp](https://www.ncoa.org/article/what-is-benefitscheckup-and-how-does-it-help-people-find-benefits-assistance/) This is a "future program" gap rather than a correctness gap in the five programs OpenHand implements today, but it's a one-question addition that several peer tools treat as standard.

### 3.6 Utility costs (separate from rent)
Distinct from shelter cost — SNAP's Standard Utility Allowance and LIHEAP both key off utility spending specifically (e.g., DC's SNAP utility allowance is a flat $374/month, updated annually). Not asked today.

## 4. A Caveat on "Just Add More Questions"

The project's own design principles (`CLAUDE.md` §2) call for **privacy-first, needs-based framing**, and the intake system prompt (`app/llm/intake.py`) is deliberately built to extract facts only from what a person volunteers, never to interrogate. Citizenship/immigration status in particular is a fact many users may be unwilling or afraid to disclose to any tool, automated or not — and the population this app serves (per the origin Mutual Aid Monday thread analysis) is an explicitly named scam target where trust is fragile. Any addition here is a genuine product-and-trust tradeoff, not just a schema change: e.g., asking it as a fully optional, clearly-explained question ("if you're comfortable sharing...") with an explicit "prefer not to say" path (mirroring NYC's own `livingPreferNotToSay` pattern in §3.2) is likely necessary, versus a hard-required field. That tradeoff is a product decision for a human to make, not something this research report resolves.

## 5. Suggested Priority Order (for human decision, not applied)

1. **Citizenship/immigration status + SSN validity** — highest correctness impact across all three income/benefit programs; needs the optional/sensitive framing discussed in §4.
2. **Housing cost (rent/mortgage) + utility cost** — directly resolves the SNAP shelter-deduction gap the engine already flags, two of the smallest asks (dollar amounts).
3. **Assets/resources (cash + bank balance)** — needed for SNAP in non-BBCE states and any future TANF/LIHEAP screen; one number.
4. **A dedicated disability question, separate from "elderly or disabled"** — the Medicaid non-expansion branch and Medicare undetermined branch both reference "disabled" as a distinct pathway from "elderly," but the intake only has one combined boolean.
5. **EITC qualifying-child relationship/residency** — narrower blast radius (only affects EITC, and only in edge cases), lower priority than the above.
6. **Veteran status, dependent-care cost, elderly/disabled medical expenses** — valuable but tied to programs not yet implemented (veteran) or to further softening already-implemented deductions (dependent care, medical) rather than fixing a wrong answer.
7. **Self-employment / S-Corp income breakdown (§6)** — narrower population than the above, but where it applies, today's single gross/earned-income split can silently produce a materially wrong SNAP, Medicaid, or EITC number, not just a softened one.

## 6. Self-Employed / S-Corp Households: A Distinct Income Model Per Program

Today's intake collects one pair of numbers — `monthly_gross_income` and an optional `monthly_earned_income` — and every engine module treats them the same way regardless of income source. Self-employment breaks that assumption because **each of the three income-tested programs OpenHand implements defines "countable income" for a self-employed or S-Corp household differently**, and the differences are large enough to flip a result, not just soften it.

### 6.1 SNAP: net self-employment income, not gross receipts
SNAP counts *net* self-employment income — gross receipts minus allowable business expenses — never gross receipts. States compute the deduction one of two ways: actual documented business costs (labor, stock/raw materials, business-property loan principal, business insurance, business property taxes — explicitly **excluding** prior-period losses, income taxes, retirement contributions, transportation, and depreciation), or a flat standard deduction on gross receipts that varies by state (examples found: 50% or 40% of declared receipts). [CalFresh guide](https://calfresh.guide/how-self-employment-income-is-counted-and-what-business-expenses-can-be-deducted/), [Montana SNAP manual](https://dphhs.mt.gov/assets/hcsd/snapmanual/SNAP503.1nc.pdf) If a self-employed person reports their *gross* business receipts as `monthly_gross_income` today (a very plausible LLM extraction outcome, since the intake system prompt never asks the distinction), SNAP's gross/net income tests both run on a number that could be far above their actual countable income — producing a false `likely_ineligible` instead of `likely_eligible`.

### 6.2 Medicaid MAGI: net profit, but S-Corp wages *and* distributions both count
Medicaid uses MAGI rules: for a sole proprietor, that's the same net-profit figure as Schedule C (gross revenue minus allowable business expenses, further reduced by the self-employment-tax and self-employed-health-insurance deductions that also reduce federal AGI). For an **S-Corp**, MAGI counts *both* the shareholder's W-2 wages from the business *and* any K-1 distributions — the entity-structure choice that separates wages from distributions for payroll-tax purposes does not shelter distributions from Medicaid MAGI the way it does for EITC (§6.3). [medicaideligibilitycalculator.com](https://medicaideligibilitycalculator.com/business-income-impact/), [Santa Clara County MAGI Medi-Cal handbook](https://stgenssa.sccgov.org/debs/program_handbooks/medi-cal/assets/15MAGIMCIncome/SelfEmployment_Income.htm) K-1 income from a partnership (Form 1065) is generally passive/unearned *except* for the portion attributable to a partner's actual labor, which caseworkers determine case-by-case — there's no clean W-2/1099 split to lean on the way there is for an S-Corp.

### 6.3 EITC: only wages count for an S-Corp — K-1 distributions are explicitly excluded
For EITC, "earned income" is net self-employment earnings (Schedule C net profit minus one-half of self-employment tax) for a sole proprietor — but for an **S-Corp shareholder-employee, only the W-2 salary counts**; K-1 distributions from the S-Corp are explicitly *not* earned income for EITC purposes. [IRS — Earned income, self-employment income and business expenses](https://www.irs.gov/tax-professionals/eitc-central/earned-income-self-employment-income-and-business-expenses), [TaxSlayerPro — Is S-Corp K-1 income earned income](https://support.taxslayerpro.com/hc/en-us/articles/5833333111194-Is-Income-on-an-S-Corporation-K-1-Considered-Earned-Income) This creates a real planning wrinkle the screener would need to reflect faithfully: an S-Corp owner who pays themselves a low salary and takes most profit as distributions (the entire point of the "reasonable compensation" tax strategy — see below) will have much *lower* EITC-countable earned income than their total household income would suggest, even though that same total income counts fully for Medicaid MAGI.

### 6.4 The "reasonable compensation" wrinkle
The IRS requires S-Corp shareholder-employees who provide more than minor services to pay themselves "reasonable compensation" as W-2 wages before taking any distributions, based on what a similar business would pay a third party for the same work — there's no safe-harbor split (the commonly cited "60/40 rule" is explicitly not IRS guidance). [IRS — S-Corp compensation and medical insurance issues](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues), [IRS FS-2008-25 (PDF)](https://www.irs.gov/pub/irs-news/fs-08-25.pdf) In practice this means a screener can't just ask "what's your income" for an S-Corp owner — it needs the wage/distribution split as two separate numbers, or the EITC and Medicaid figures will both be wrong in opposite directions (EITC overstated if distributions are wrongly included as earned income; Medicaid understated if distributions are wrongly excluded from MAGI).

### 6.5 What this implies for intake questions
None of this requires the intake to become a tax interview. It suggests one branching follow-up once self-employment is mentioned at all:
- Business structure: sole proprietor/independent contractor (1099), partnership, or S-Corp.
- For sole proprietor/1099: gross receipts *and* a rough monthly business-expense estimate (or accept a net-profit figure directly if that's what the person volunteers — the LLM extraction prompt would need an explicit instruction not to conflate gross receipts with net income, since nothing today tells it to ask which one it's getting).
- For S-Corp: W-2 wages paid to self, separately from any distributions/K-1 amount — because §6.2 and §6.3 need those two numbers combined differently per program.
This is a moderate schema change (a new optional sub-object, not just a field), so it's listed as its own priority tier (§5 item 7) rather than folded into the income fields already there.

## Sources

- [ACCESS NYC Eligibility Screener](https://access.nyc.gov/eligibility/)
- [NYC Benefits Platform Screening API docs](https://screeningapidocs.cityofnewyork.us/)
- [NYC Benefits Platform: Eligibility Screening API — Digital Government Hub](https://digitalgovernmenthub.org/examples/nyc-benefits-platform-eligibility-screening-api/)
- [mRelief SNAP screener](https://www.mrelief.com/)
- [NCOA — What Is BenefitsCheckUp](https://www.ncoa.org/article/what-is-benefitscheckup-and-how-does-it-help-people-find-benefits-assistance/)
- [NCOA — SNAP benefits for veterans](https://www.ncoa.org/article/snap-assistance-are-veterans-entitled-to-benefits/)
- [CBPP — A Quick Guide to SNAP Eligibility and Benefits](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits)
- [KFF — How States Verify Citizenship and Immigration Status in Medicaid](https://www.kff.org/medicaid/how-states-verify-citizenship-and-immigration-status-in-medicaid/)
- [Medicaid.gov — Citizenship and non-citizen eligibility implementation guide (PDF)](https://www.medicaid.gov/resources-for-states/downloads/macpro-ig-citizenship-and-non-citizen-eligibility.pdf)
- [HealthCare.gov — Health coverage for lawfully present immigrants](https://www.healthcare.gov/immigrants/lawfully-present-immigrants/)
- [LIHEAP Clearinghouse — Assets Test by State](https://liheapch.acf.gov/tables/assets.htm)
- [LIHEAP Clearinghouse — Household Identity/required information](https://liheapch.acf.gov/delivery/eligibility-household.htm)
- [IRS — EITC Qualifying Child Rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/qualifying-child-rules)
- [IRS Publication 596 (2025) — Earned Income Credit](https://www.irs.gov/publications/p596)
- [LSNC/CalFresh Guide — How self-employment income is counted](https://calfresh.guide/how-self-employment-income-is-counted-and-what-business-expenses-can-be-deducted/)
- [Montana SNAP Manual 503-1 — Self-Employment Income (PDF)](https://dphhs.mt.gov/assets/hcsd/snapmanual/SNAP503.1nc.pdf)
- [medicaideligibilitycalculator.com — Business Income & Medicaid Eligibility](https://medicaideligibilitycalculator.com/business-income-impact/)
- [Santa Clara County MAGI Medi-Cal Handbook — Self-Employment Income](https://stgenssa.sccgov.org/debs/program_handbooks/medi-cal/assets/15MAGIMCIncome/SelfEmployment_Income.htm)
- [IRS — Earned income, self-employment income and business expenses (EITC Central)](https://www.irs.gov/tax-professionals/eitc-central/earned-income-self-employment-income-and-business-expenses)
- [TaxSlayerPro — Is Income on an S-Corporation K-1 Considered Earned Income?](https://support.taxslayerpro.com/hc/en-us/articles/5833333111194-Is-Income-on-an-S-Corporation-K-1-Considered-Earned-Income)
- [IRS — S corporation compensation and medical insurance issues](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues)
- [IRS FS-2008-25 — Wage Compensation for S Corporation Officers (PDF)](https://www.irs.gov/pub/irs-news/fs-08-25.pdf)
- OpenHand source (this repo): `app/schemas.py`, `app/engine/snap.py`, `app/engine/medicaid.py`, `app/engine/eitc.py`, `app/engine/medicare.py`, `app/llm/intake.py`

## Next Step

This report is research only. Per `/sc:research` boundaries, no schema/engine/intake changes were made. If you want to act on any of the priorities in §5, use `/sc:design` to work through the schema and eligibility-rule changes (especially the sensitive-question framing in §4), or ask directly for implementation.
