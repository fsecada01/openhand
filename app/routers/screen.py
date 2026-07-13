"""Server-rendered screening flow (JinjaX components + HTMX)."""

import logging
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
from app.llm.client import LLMNotConfiguredError
from app.models import Screening
from app.schemas import Explanation
from app.services import disability_lookup, resource_search
from app.ui import catalog

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

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
    narrative: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    prior_narrative: Annotated[str, Form()] = "",
):
    combined = narrative.strip()
    if prior_narrative.strip():
        combined = (
            f"{prior_narrative.strip()}\n\nAdditional info: {narrative.strip()}"
        )

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

    if extraction.missing_required:
        return HTMLResponse(
            catalog.render(
                "Clarify",
                question=extraction.clarifying_question,
                prior_narrative=combined,
            )
        )

    profile = extraction.to_profile()
    profile.disability_diagnosis_match = disability_lookup.lookup(
        session, combined
    )
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

    return HTMLResponse(
        catalog.render(
            "Results",
            explanation=explanation,
            determinations=determinations,
            resource_searches=resource_searches,
        )
    )
