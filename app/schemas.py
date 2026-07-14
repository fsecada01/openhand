"""Pydantic schemas shared by the intake LLM pass and the engine.

`IntakeExtraction` doubles as the structured-output schema for
`client.messages.parse()` — every household field is optional so the
model can report what it could NOT find instead of guessing.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

REQUIRED_FIELDS = ("state", "household_size", "monthly_gross_income")


class FilingStatus(StrEnum):
    single = "single"
    head_of_household = "head_of_household"
    married_joint = "married_joint"
    other = "other"


class DisabilityCategory(StrEnum):
    mental_health = "mental_health"
    physical = "physical"
    other = "other"


class BusinessStructure(StrEnum):
    sole_proprietor = "sole_proprietor"
    s_corp = "s_corp"
    partnership = "partnership"
    other = "other"


class HouseholdProfile(BaseModel):
    """Validated input to the deterministic eligibility engine."""

    state: str = Field(min_length=2, max_length=2)
    household_size: int = Field(ge=1, le=20)
    monthly_gross_income: float = Field(ge=0)
    monthly_earned_income: float | None = Field(default=None, ge=0)
    num_children: int = Field(default=0, ge=0)
    filing_status: FilingStatus = FilingStatus.single
    has_elderly_or_disabled: bool = False
    is_pregnant: bool = False
    adult_age: int | None = Field(default=None, ge=0, le=130)
    annual_investment_income: float | None = Field(default=None, ge=0)
    receives_ssdi: bool = False
    months_on_ssdi: int | None = Field(default=None, ge=0)
    has_als_or_esrd: bool = False
    # Populated by app.services.disability_lookup at the router layer
    # — a deterministic SQLite keyword scan of the raw narrative, not
    # an LLM-extracted field (IntakeFacts is already right at Claude's
    # structured-output schema complexity limit). Never a decision,
    # only context for the Medicare-pathway wording.
    disability_diagnosis_match: str | None = Field(default=None, max_length=200)

    # --- Supplemental facts (app.llm.supplemental.SupplementalFacts) ---
    # All optional, extracted in a second LLM pass so IntakeFacts stays
    # under Claude's structured-output schema complexity limit. Never
    # gate the clarifying-question loop — they only sharpen results
    # when volunteered.
    monthly_housing_cost: float | None = Field(default=None, ge=0)
    monthly_utility_cost: float | None = Field(default=None, ge=0)
    liquid_assets: float | None = Field(default=None, ge=0)
    has_disability: bool = False
    is_veteran: bool = False
    monthly_dependent_care_cost: float | None = Field(default=None, ge=0)
    monthly_medical_expenses: float | None = Field(default=None, ge=0)
    is_self_employed: bool = False
    business_structure: BusinessStructure | None = None
    monthly_gross_receipts: float | None = Field(default=None, ge=0)
    monthly_business_expenses: float | None = Field(default=None, ge=0)
    monthly_w2_wages_from_business: float | None = Field(default=None, ge=0)
    monthly_k1_distributions: float | None = Field(default=None, ge=0)

    @property
    def earned(self) -> float:
        if self.monthly_earned_income is not None:
            return self.monthly_earned_income
        return self.monthly_gross_income

    @property
    def annual_income(self) -> float:
        return self.monthly_gross_income * 12

    @property
    def self_employment_net_monthly(self) -> float | None:
        """Net profit (gross receipts minus business expenses).

        None when no gross receipts were reported — callers fall back
        to the household's plain income fields in that case.
        """
        if self.monthly_gross_receipts is None:
            return None
        return max(
            self.monthly_gross_receipts - (self.monthly_business_expenses or 0),
            0,
        )

    @property
    def magi_income_monthly(self) -> float:
        """Medicaid MAGI income, self-employment/S-Corp aware.

        S-Corp: shareholder W-2 wages AND K-1 distributions both count
        toward MAGI. Sole proprietor/1099: net profit, not gross
        receipts. Anyone else: unchanged monthly_gross_income.
        """
        if self.business_structure == BusinessStructure.s_corp and (
            self.monthly_w2_wages_from_business is not None
            or self.monthly_k1_distributions is not None
        ):
            return (self.monthly_w2_wages_from_business or 0) + (
                self.monthly_k1_distributions or 0
            )
        if self.self_employment_net_monthly is not None:
            return self.self_employment_net_monthly
        return self.monthly_gross_income

    @property
    def eitc_earned_income_monthly(self) -> float:
        """EITC "earned income", self-employment/S-Corp aware.

        S-Corp: ONLY W-2 wages count — K-1 distributions are
        explicitly excluded from EITC earned income by the IRS.
        Sole proprietor/1099: net profit, not gross receipts. Anyone
        else: unchanged `.earned`.
        """
        if self.business_structure == BusinessStructure.s_corp:
            return self.monthly_w2_wages_from_business or 0
        if self.self_employment_net_monthly is not None:
            return self.self_employment_net_monthly
        return self.earned

    def updated_with(
        self,
        facts: "IntakeFacts",
        supplemental: "SupplementalFacts | None" = None,
    ) -> "HouseholdProfile":
        """This profile overlaid with any newly-stated facts.

        Phase-2 feedback rounds extract ONLY that round's new text
        (see the screen router), so most fields come back None. None
        means "not mentioned this round", never "unset it" — the
        carried value survives. Non-null values override, so a
        correction ("actually my rent is $2,000") takes effect.

        Only `IntakeFacts`/`SupplementalFacts` fields are overlaid —
        `IntakeExtraction`'s bookkeeping fields are control flow, not
        household facts. The result is re-validated, so a bad overlay
        raises instead of reaching the engine.
        """
        updates = facts.model_dump(
            include=set(IntakeFacts.model_fields), exclude_none=True
        )
        if supplemental is not None:
            updates.update(supplemental.model_dump(exclude_none=True))
        if "state" in updates:
            updates["state"] = updates["state"].upper()
        return HouseholdProfile(**{**self.model_dump(), **updates})


class IntakeFacts(BaseModel):
    """Structured-output schema for the intake LLM call itself.

    Kept lean (facts only, no `missing_required`/`clarifying_question`)
    because Claude's structured-outputs feature rejects schemas past a
    complexity threshold — this model sits right under that limit.
    Deciding what's missing and how to ask for it is control flow, not
    an extracted fact, so it lives in Python (see `IntakeExtraction`
    and `app.llm.intake.extract`) rather than in this schema.

    Facts are extracted only when explicitly stated; anything unknown
    stays None.
    """

    state: str | None = Field(
        default=None,
        description="Two-letter US state/DC code, e.g. 'TX'.",
    )
    household_size: int | None = Field(
        default=None,
        description="People who buy and prepare food together.",
    )
    monthly_gross_income: float | None = Field(
        default=None,
        description="Total household income per month before taxes, "
        "in dollars. Convert annual/weekly amounts to monthly.",
    )
    monthly_earned_income: float | None = Field(
        default=None,
        description="Portion of monthly income from work (wages or "
        "self-employment), if distinguishable.",
    )
    num_children: int | None = Field(
        default=None, description="Children under 19 in the household."
    )
    filing_status: FilingStatus | None = None
    has_elderly_or_disabled: bool | None = Field(
        default=None,
        description="Anyone in the household aged 60+ or disabled.",
    )
    is_pregnant: bool | None = None
    adult_age: int | None = Field(
        default=None, description="Age of the person asking, if stated."
    )
    annual_investment_income: float | None = None
    receives_ssdi: bool | None = Field(
        default=None,
        description="True if someone in the household receives SSDI "
        "(Social Security Disability Insurance) payments.",
    )
    months_on_ssdi: int | None = Field(
        default=None,
        description="How many months SSDI has been received, if "
        "stated ('two years on disability' = 24).",
    )
    has_als_or_esrd: bool | None = Field(
        default=None,
        description="True if ALS (Lou Gehrig's disease) or end-stage "
        "renal/kidney disease (dialysis or transplant) is mentioned.",
    )


class SupplementalHousingFacts(BaseModel):
    """First of two supplemental structured-output schemas.

    Split from a single `SupplementalFacts` call into this plus
    `SupplementalSelfEmploymentFacts` — two smaller sequential calls
    instead of one call carrying all 13 fields, to reduce exposure to
    Claude's structured-output grammar-compilation ceiling. Neither
    half is ever required.
    """

    monthly_housing_cost: float | None = Field(
        default=None,
        description="Monthly rent or mortgage payment, in dollars.",
    )
    monthly_utility_cost: float | None = Field(
        default=None,
        description="Monthly utility bills (electric, gas, water), "
        "separate from rent/mortgage.",
    )
    liquid_assets: float | None = Field(
        default=None,
        description="Cash on hand plus bank account balances, "
        "combined into one number.",
    )
    has_disability: bool | None = Field(
        default=None,
        description="True if the person or someone in the household "
        "has a disability — distinct from being elderly.",
    )
    is_veteran: bool | None = Field(
        default=None,
        description="True if the person or someone in the household "
        "is a military veteran.",
    )
    monthly_dependent_care_cost: float | None = Field(
        default=None,
        description="Monthly cost of child care or care for a "
        "dependent that enables work or job searching.",
    )
    monthly_medical_expenses: float | None = Field(
        default=None,
        description="Monthly out-of-pocket medical expenses for an "
        "elderly or disabled household member.",
    )


class SupplementalSelfEmploymentFacts(BaseModel):
    """Second of two supplemental structured-output schemas.

    See `SupplementalHousingFacts` for why this is a separate call.
    """

    is_self_employed: bool | None = Field(
        default=None,
        description="True if the person's income comes from their "
        "own business rather than an employer.",
    )
    business_structure: BusinessStructure | None = Field(
        default=None,
        description="How the person's business is structured, if "
        "self-employed and stated.",
    )
    monthly_gross_receipts: float | None = Field(
        default=None,
        description="Total business revenue per month before "
        "expenses, for a sole proprietor/1099 contractor.",
    )
    monthly_business_expenses: float | None = Field(
        default=None,
        description="Monthly business expenses/costs of doing "
        "business, to subtract from gross receipts.",
    )
    monthly_w2_wages_from_business: float | None = Field(
        default=None,
        description="Monthly W-2 salary the person pays themselves "
        "from their own S-Corp, separate from distributions.",
    )
    monthly_k1_distributions: float | None = Field(
        default=None,
        description="Monthly K-1 profit distributions from an "
        "S-Corp, separate from W-2 wages.",
    )


class SupplementalFacts(
    SupplementalHousingFacts, SupplementalSelfEmploymentFacts
):
    """Combined supplemental facts, merged from two extraction calls.

    `app.llm.supplemental.extract_supplemental` runs the housing and
    self-employment schemas as two separate `messages.parse` calls and
    merges the results into this type, which is what the rest of the
    app (routers, `HouseholdProfile.to_profile`, tests) still consumes
    — the two-call split is an internal detail of the extraction step,
    not a change to callers' contract.
    """


class IntakeExtraction(IntakeFacts):
    """`IntakeFacts` plus the missing-fact bookkeeping the app needs.

    `app.llm.intake.extract` builds this from the LLM's `IntakeFacts`
    output and Python-computed `missing_required`/`clarifying_question`
    — never from a second model field the LLM fills in itself.
    """

    missing_required: list[str] = Field(
        default_factory=list,
        description="Required fields (state, household_size, "
        "monthly_gross_income) that could not be extracted.",
    )
    clarifying_question: str | None = Field(
        default=None,
        description="ONE friendly question asking for all missing "
        "required facts at once. None if nothing is missing.",
    )

    def to_profile(
        self, supplemental: SupplementalFacts | None = None
    ) -> HouseholdProfile:
        """Build an engine profile; raises if required facts missing."""
        extra = (
            supplemental.model_dump(exclude_none=True) if supplemental else {}
        )
        return HouseholdProfile(
            state=(self.state or "").upper(),
            household_size=self.household_size or 0,
            monthly_gross_income=(
                self.monthly_gross_income
                if self.monthly_gross_income is not None
                else -1
            ),
            monthly_earned_income=self.monthly_earned_income,
            num_children=self.num_children or 0,
            filing_status=self.filing_status or FilingStatus.single,
            has_elderly_or_disabled=bool(self.has_elderly_or_disabled),
            is_pregnant=bool(self.is_pregnant),
            adult_age=self.adult_age,
            annual_investment_income=self.annual_investment_income,
            receives_ssdi=bool(self.receives_ssdi),
            months_on_ssdi=self.months_on_ssdi,
            has_als_or_esrd=bool(self.has_als_or_esrd),
            **extra,
        )


class Status(StrEnum):
    likely_eligible = "likely_eligible"
    possibly_eligible = "possibly_eligible"
    likely_ineligible = "likely_ineligible"
    undetermined = "undetermined"


class Determination(BaseModel):
    """Auditable per-program result from the deterministic engine."""

    program: str
    program_name: str
    status: Status
    reasons: list[str]
    estimated_benefit: str | None = None
    apply_url: str
    data_vintage: str
    source_url: str


class ExplanationSection(BaseModel):
    """One program's plain-language write-up in the summary card."""

    heading: str = Field(
        description="The program name this section covers, or a "
        "short label like 'Next steps'."
    )
    points: list[str] = Field(
        description="2-4 short, plain-language bullet points: what "
        "the result means, then the single next step."
    )


class Explanation(BaseModel):
    """Structured-output schema for the explanation LLM pass.

    Rendered as real headings/lists (see ExplanationCard.jinja)
    instead of markdown-in-plain-text, so formatting can't leak as
    literal asterisks/hashes.
    """

    intro: str = Field(
        description="1-2 warm opening sentences, no program specifics."
    )
    sections: list[ExplanationSection]
    closing: str = Field(
        description="Closing note: these are screening estimates, "
        "and local mutual aid remains a great resource alongside "
        "these programs."
    )


class ResourceLink(BaseModel):
    """A single web-search result — informational, not a determination."""

    title: str
    url: str
    snippet: str = ""


class ResourceSearch(BaseModel):
    """Tavily results for one poorly-matched program.

    Explicitly non-authoritative and possibly state-specific —
    kept separate from `Determination` so the UI never conflates
    "provided as-is" web results with the deterministic federal
    screening above.
    """

    program_name: str
    query: str
    results: list[ResourceLink]
