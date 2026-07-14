"""Server-rendered screening flow (JinjaX components + HTMX)."""

import logging
import uuid
from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session
from sqlmodel_crud_utils import write_row

from app import config
from app.db import get_session
from app.engine import ENGINE_VERSION, evaluate
from app.llm import explain as explain_mod
from app.llm import intake
from app.llm import supplemental as supplemental_mod
from app.llm.client import LLMNotConfiguredError
from app.llm.intake import ASK_PROMPTS
from app.logging_utils import request_id_var
from app.models import Screening
from app.schemas import Explanation, HouseholdProfile, IntakeExtraction
from app.services import disability_lookup, resource_search
from app.ui import catalog

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Single round budget for the ENTIRE conversation (gathering +
# post-report feedback combined) — after this many /screen
# round-trips (or an earlier "end here"/"that's everything" click,
# see Clarify.jinja and Confirm.jinja) we stop asking and finalize
# with whatever was gathered.
MAX_TOTAL_ROUNDS = 10

# Soft target for the gathering phase (required facts + one
# supplemental Confirm pass): by this round we proactively generate
# the initial report even without an explicit "that's everything"
# confirmation, so the report doesn't wait on the user closing the
# chat. A person can still finish earlier by confirming sooner — this
# is a ceiling, not a floor.
SOFT_GATHER_ROUNDS = 5

# Cycled by `confirm_round` (see `screen()`) so a person who clicks
# "Add & continue" more than once doesn't see the exact same "did we
# miss anything?" sentence verbatim every time — that reads as a
# stuck/broken loop rather than a real back-and-forth.
CONFIRM_PROMPTS = [
    (
        "Before we show your results",
        "did we miss anything? For example: self-employment income, "
        "housing or utility costs, savings, disability or veteran "
        "status, or child/dependent care or medical costs.",
    ),
    (
        "Thanks for that",
        "anything else worth mentioning before we run the numbers? "
        "Even a second job, child support, or a recent move can "
        "matter.",
    ),
    (
        "Just double-checking",
        "is there anything else about your income, housing, health, "
        "or family we should factor in before showing results?",
    ),
    (
        "One last check",
        "anything you'd like to add or correct before we generate "
        "your results?",
    ),
]

EXPLANATION_FALLBACK = Explanation(
    intro="We couldn't generate the plain-language summary just now, "
    "but the program-by-program details below are complete.",
    sections=[],
    closing="",
)


def _error_alert(message: str) -> HTMLResponse:
    # Error alerts are delivered as HTTP 200 (they're rendered into
    # the conversation, not handled by the htmx error toast), so the
    # form's "disable yourself once sent" behavior would otherwise
    # treat them as success and lock the user's still-unprocessed
    # text in a disabled form right next to a "please try again"
    # message. This header tells Form.jinja to leave the form live.
    return HTMLResponse(
        catalog.render("ErrorAlert", message=message),
        headers={"X-OpenHand-Error": "1"},
    )


def _extract_or_alert(
    narrative: str, round_num: int
) -> tuple[IntakeExtraction | None, HTMLResponse | None]:
    """Run the intake extraction, mapping failures to error alerts.

    Returns (extraction, None) on success, (None, response) on
    failure — shared by the gather phase (full narrative) and phase-2
    refresh rounds (this round's new text only).
    """
    try:
        return intake.extract(narrative, round_num=round_num), None
    except (LLMNotConfiguredError, anthropic.AuthenticationError):
        logger.exception("intake auth failure")
        return None, _error_alert(
            "This site isn't connected to its screening assistant "
            "yet (missing or invalid API key). The site owner needs "
            "to configure ANTHROPIC_API_KEY."
        )
    except anthropic.RateLimitError:
        return None, _error_alert(
            "We're handling a lot of requests right now. Please "
            "wait a minute and try again."
        )
    except anthropic.APIConnectionError:
        return None, _error_alert(
            "We couldn't reach the screening assistant. Please try "
            "again in a moment."
        )
    except Exception:
        logger.exception("intake failed")
        return None, _error_alert(
            "Something went wrong reading your message. Nothing you "
            "typed was stored — please try again, and if it keeps "
            "happening, let us know on GitHub."
        )


def _parse_carried_profile(profile_json: str) -> HouseholdProfile | None:
    """Parse the profile Results carried forward in a hidden field.

    It round-trips through the browser, so it arrives as untrusted
    input — any parse/validation failure (or an empty field, e.g. a
    report generated before profiles were carried) just returns None
    and the caller falls back to full re-extraction.
    """
    if not profile_json:
        return None
    try:
        return HouseholdProfile.model_validate_json(profile_json)
    except Exception:
        logger.warning("carried profile failed validation; ignoring")
        return None


@router.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(catalog.render("Home"))


@router.post("/screen", response_class=HTMLResponse)
@limiter.limit(config.RATE_LIMIT_SCREEN)
async def screen(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    # FastAPI's Form() treats a submitted empty string as a missing
    # required field, not an empty value — the "end here" button
    # (formnovalidate, so it can submit a blank textarea) needs a
    # default so that submission doesn't 422.
    narrative: Annotated[str, Form()] = "",
    prior_narrative: Annotated[str, Form()] = "",
    round_num: Annotated[int, Form()] = 1,
    finalize: Annotated[str, Form()] = "",
    confirmed: Annotated[str, Form()] = "",
    # Set once the initial report has been generated (see
    # Results.jinja's feedback form) — marks every later round as
    # phase-2 feedback/refinement rather than intake, so it re-enters
    # here without looping back through Clarify/Confirm.
    reported: Annotated[str, Form()] = "",
    # How many times Confirm has already been shown in this
    # conversation — 0 the first time (see CONFIRM_PROMPTS above).
    # Deliberately separate from `round_num`, which also counts any
    # Clarify rounds that preceded it, so the FIRST Confirm always
    # gets the familiar opening phrasing regardless of how many
    # rounds it took to get there.
    confirm_round: Annotated[int, Form()] = 0,
    # The already-extracted household profile, carried forward by
    # Results' feedback form so phase-2 rounds only have to process
    # this round's NEW text (see _phase2_refresh) instead of
    # re-extracting the whole accumulated narrative every round.
    profile_json: Annotated[str, Form()] = "",
):
    token = request_id_var.set(uuid.uuid4().hex[:8])
    try:
        addition = narrative.strip()
        combined = prior_narrative.strip()
        if addition:
            combined = (
                f"{combined}\n\nAdditional info: {addition}"
                if combined
                else addition
            )
        at_round_limit = round_num >= MAX_TOTAL_ROUNDS

        if reported:
            # Phase 2: the gathering phase is already over and a
            # report already exists — this round is feedback/more
            # detail to refine it (and its resource search), not
            # intake, so it never goes back through Clarify/Confirm.
            # Results carries the already-extracted profile forward,
            # so only this round's NEW text needs LLM processing —
            # and when it changes nothing, the engine, explanation,
            # and gap searches are all skipped (see _phase2_refresh).
            carried = _parse_carried_profile(profile_json)
            if carried is not None:
                return _phase2_refresh(
                    carried,
                    addition,
                    combined,
                    session,
                    round_num=round_num,
                    offer_feedback=not at_round_limit,
                )

        extraction, error = _extract_or_alert(combined, round_num)
        if error is not None:
            return error

        if reported:
            # Phase-2 fallback when no valid carried profile came
            # back with the form (e.g. a report generated before
            # profiles were carried forward): the legacy full
            # re-extraction of the accumulated narrative. `addition`
            # still drives one extra, targeted resource search so a
            # literal follow-up question gets an actual answer.
            return _render_results(
                combined,
                extraction,
                session,
                round_num=round_num,
                offer_feedback=not at_round_limit,
                question=addition or None,
            )

        # Required facts (state/household_size/income) have to be in
        # hand before any report is possible, so this loop gets the
        # full round budget — NOT the soft gather ceiling below —
        # only an explicit "end here" or the hard round limit cuts it
        # short.
        hard_finalize = bool(finalize) or at_round_limit

        if extraction.missing_required and not hard_finalize:
            return HTMLResponse(
                catalog.render(
                    "Clarify",
                    question=extraction.clarifying_question,
                    prior_narrative=combined,
                    round_num=round_num + 1,
                )
            )

        if extraction.missing_required:
            # Round limit hit, or the user clicked "end here", and we
            # still don't have enough to run the deterministic engine
            # safely — finalize with what we know instead of guessing.
            return HTMLResponse(
                catalog.render(
                    "IncompleteResults",
                    missing=[
                        ASK_PROMPTS[f] for f in extraction.missing_required
                    ],
                )
            )

        # From here required facts are in hand, so the soft gather
        # ceiling applies: generate the initial report proactively by
        # this round even without an explicit confirmation, rather
        # than waiting on the user to explicitly say they're done.
        should_finalize = hard_finalize or round_num >= SOFT_GATHER_ROUNDS

        if not confirmed and not should_finalize:
            # Required facts are in hand, but the narrative may not
            # mention anything the optional supplemental pass looks
            # for (housing costs, self-employment, disability,
            # veteran status, ...) — give the user one chance to add
            # it before we run the engine, rather than assuming a
            # short narrative means there's nothing else.
            headline, body = CONFIRM_PROMPTS[
                confirm_round % len(CONFIRM_PROMPTS)
            ]
            return HTMLResponse(
                catalog.render(
                    "Confirm",
                    headline=headline,
                    body=body,
                    prior_narrative=combined,
                    round_num=round_num + 1,
                    confirm_round=confirm_round + 1,
                )
            )

        return _render_results(
            combined,
            extraction,
            session,
            round_num=round_num,
            offer_feedback=not at_round_limit,
        )
    finally:
        request_id_var.reset(token)


def _phase2_refresh(
    carried: HouseholdProfile,
    addition: str,
    combined: str,
    session: Session,
    round_num: int,
    offer_feedback: bool,
) -> HTMLResponse:
    """Phase-2 round with a carried profile: process ONLY the new text.

    The initial report already extracted the full narrative into a
    profile, which Results carries forward in a hidden field.
    Re-extracting the whole accumulated narrative every round both
    re-spends tokens and can silently flip already-settled facts (the
    LLM re-reading the same words doesn't always land on the same
    extraction). Instead, this extracts just this round's addition and
    overlays any newly-stated facts onto the carried profile. When the
    merged profile is identical — the addition was a question, not new
    facts — the engine, explanation, and gap searches are all skipped
    and only the question-driven search runs.
    """
    question = addition or None
    merged = carried.model_copy()
    if addition:
        extraction, error = _extract_or_alert(addition, round_num)
        if error is not None:
            return error
        try:
            supplemental = supplemental_mod.extract_supplemental(addition)
        except Exception:
            logger.exception("supplemental extraction failed")
            supplemental = None
        try:
            merged = carried.updated_with(extraction, supplemental)
        except Exception:
            # A bad overlay (nonsense extraction failing profile
            # validation) must not cost the person their
            # conversation — keep the carried profile and still
            # answer the question.
            logger.exception("profile overlay failed; keeping carried")
            merged = carried.model_copy()

    # The diagnosis scan is deterministic and cheap — always rerun it
    # on the full narrative so a newly-mentioned diagnosis counts as
    # a profile change like any other new fact.
    merged.disability_diagnosis_match = disability_lookup.lookup(
        session, combined
    )

    if merged == carried:
        question_search = None
        if question:
            try:
                question_search = resource_search.search_for_question(
                    question, carried.state
                )
            except Exception:
                logger.exception("question-driven resource search failed")
        return HTMLResponse(
            catalog.render(
                "QuestionUpdate",
                question=question,
                search=question_search,
                prior_narrative=combined,
                profile_json=carried.model_dump_json(),
                round_num=round_num + 1,
                offer_feedback=offer_feedback,
            )
        )

    return _render_report(
        merged,
        combined,
        session,
        round_num=round_num,
        offer_feedback=offer_feedback,
        question=question,
    )


def _render_results(
    combined: str,
    extraction,
    session: Session,
    round_num: int,
    offer_feedback: bool,
    question: str | None = None,
) -> HTMLResponse:
    """Extract supplemental facts, build the profile, render a report.

    Used for the initial report (end of the gather phase) and the
    legacy phase-2 fallback; phase-2 rounds with a carried profile go
    through `_phase2_refresh` instead.
    """
    # Optional second pass (housing/utility cost, assets, disability,
    # veteran status, self-employment breakdown, ...) — never
    # required, so any failure here must never cost the user their
    # results.
    try:
        supplemental = supplemental_mod.extract_supplemental(combined)
    except Exception:
        logger.exception("supplemental extraction failed")
        supplemental = None

    profile = extraction.to_profile(supplemental)
    profile.disability_diagnosis_match = disability_lookup.lookup(
        session, combined
    )
    return _render_report(
        profile,
        combined,
        session,
        round_num=round_num,
        offer_feedback=offer_feedback,
        question=question,
    )


def _render_report(
    profile: HouseholdProfile,
    combined: str,
    session: Session,
    round_num: int,
    offer_feedback: bool,
    question: str | None = None,
) -> HTMLResponse:
    """Run the engine + explanation + resource searches and render
    Results for an already-built profile.

    `question`, when given, is this round's newly-added text (phase-2
    only) — it drives one extra, targeted resource search on top of
    the standard per-program ones, since neither the engine, the
    explanation pass, nor `search_for_gaps` ever look at the raw
    narrative.
    """
    determinations = evaluate(profile)

    write_row(
        Screening(
            profile=profile.model_dump(mode="json"),
            determinations=[d.model_dump(mode="json") for d in determinations],
            engine_version=ENGINE_VERSION,
            narrative=combined if config.STORE_NARRATIVES else None,
        ),
        session,
    )

    # The engine already decided; a summary failure must never cost
    # the user their results.
    try:
        explanation = explain_mod.explain(profile, determinations)
    except Exception:
        logger.exception("explanation failed")
        explanation = EXPLANATION_FALLBACK

    try:
        resource_searches = resource_search.search_for_gaps(
            profile, determinations
        )
    except Exception:
        logger.exception("resource search failed")
        resource_searches = []

    if question:
        try:
            question_search = resource_search.search_for_question(
                question, profile.state
            )
        except Exception:
            logger.exception("question-driven resource search failed")
            question_search = None
        if question_search:
            resource_searches = [question_search] + resource_searches

    return HTMLResponse(
        catalog.render(
            "Results",
            explanation=explanation,
            determinations=determinations,
            resource_searches=resource_searches,
            prior_narrative=combined,
            profile_json=profile.model_dump_json(),
            round_num=round_num + 1,
            offer_feedback=offer_feedback,
        )
    )
