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
from app.schemas import Explanation
from app.services import disability_lookup, resource_search
from app.ui import catalog

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Caps the back-and-forth (both the required-facts Clarify loop and
# the post-confirm "anything else?" loop) so a person isn't stuck in
# an endless question loop — after this many rounds (or an earlier
# "end here"/"that's everything" click, see Clarify.jinja and
# Confirm.jinja) we stop asking and finalize with whatever was
# gathered.
MAX_CLARIFY_ROUNDS = 10

EXPLANATION_FALLBACK = Explanation(
    intro="We couldn't generate the plain-language summary just now, "
    "but the program-by-program details below are complete.",
    sections=[],
    closing="",
)


def _error_alert(message: str) -> HTMLResponse:
    return HTMLResponse(catalog.render("ErrorAlert", message=message))


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
        should_finalize = bool(finalize) or round_num >= MAX_CLARIFY_ROUNDS

        try:
            extraction = intake.extract(combined)
        except (LLMNotConfiguredError, anthropic.AuthenticationError):
            logger.exception("intake auth failure")
            return _error_alert(
                "This site isn't connected to its screening assistant "
                "yet (missing or invalid API key). The site owner needs "
                "to configure ANTHROPIC_API_KEY."
            )
        except anthropic.RateLimitError:
            return _error_alert(
                "We're handling a lot of requests right now. Please "
                "wait a minute and try again."
            )
        except anthropic.APIConnectionError:
            return _error_alert(
                "We couldn't reach the screening assistant. Please try "
                "again in a moment."
            )
        except Exception:
            logger.exception("intake failed")
            return _error_alert(
                "Something went wrong reading your message. Nothing you "
                "typed was stored — please try again, and if it keeps "
                "happening, let us know on GitHub."
            )

        if extraction.missing_required and not should_finalize:
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

        if not confirmed and not should_finalize:
            # Required facts are in hand, but the narrative may not
            # mention anything the optional supplemental pass looks
            # for (housing costs, self-employment, disability,
            # veteran status, ...) — give the user one chance to add
            # it before we run the engine, rather than assuming a
            # short narrative means there's nothing else.
            return HTMLResponse(
                catalog.render(
                    "Confirm",
                    prior_narrative=combined,
                    round_num=round_num + 1,
                )
            )

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
        determinations = evaluate(profile)

        write_row(
            Screening(
                profile=profile.model_dump(mode="json"),
                determinations=[
                    d.model_dump(mode="json") for d in determinations
                ],
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

        return HTMLResponse(
            catalog.render(
                "Results",
                explanation=explanation,
                determinations=determinations,
                resource_searches=resource_searches,
            )
        )
    finally:
        request_id_var.reset(token)
