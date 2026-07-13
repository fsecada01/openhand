"""JSON API (v1)."""

import logging
from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
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
from app.models import Screening
from app.schemas import (
    Determination,
    Explanation,
    HouseholdProfile,
    ResourceSearch,
)
from app.services import disability_lookup, resource_search

router = APIRouter(prefix="/api/v1")
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


class ScreenRequest(BaseModel):
    narrative: str = Field(min_length=1, max_length=5000)
    explain: bool = False
    search_resources: bool = False


class ScreenResponse(BaseModel):
    complete: bool
    clarifying_question: str | None = None
    missing_required: list[str] = []
    profile: HouseholdProfile | None = None
    determinations: list[Determination] = []
    explanation: Explanation | None = None
    resource_searches: list[ResourceSearch] = []
    engine_version: str = ENGINE_VERSION


@router.post("/screen", response_model=ScreenResponse)
@limiter.limit(config.RATE_LIMIT_SCREEN)
async def screen(
    request: Request,
    body: ScreenRequest,
    session: Annotated[Session, Depends(get_session)],
):
    try:
        extraction = intake.extract(body.narrative)
    except (LLMNotConfiguredError, anthropic.AuthenticationError) as exc:
        logger.exception("intake auth failure")
        raise HTTPException(
            status_code=503,
            detail="Screening assistant is not configured "
            "(missing or invalid ANTHROPIC_API_KEY).",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Upstream rate limit hit — retry shortly.",
        ) from exc
    except anthropic.APIError as exc:
        logger.exception("intake failed")
        raise HTTPException(
            status_code=502,
            detail="Screening assistant is unavailable — retry shortly.",
        ) from exc

    if extraction.missing_required:
        return ScreenResponse(
            complete=False,
            clarifying_question=extraction.clarifying_question,
            missing_required=extraction.missing_required,
        )

    try:
        supplemental = supplemental_mod.extract_supplemental(body.narrative)
    except Exception:
        logger.exception("supplemental extraction failed")
        supplemental = None

    profile = extraction.to_profile(supplemental)
    profile.disability_diagnosis_match = disability_lookup.lookup(
        session, body.narrative
    )
    determinations = evaluate(profile)
    write_row(
        Screening(
            profile=profile.model_dump(mode="json"),
            determinations=[d.model_dump(mode="json") for d in determinations],
            engine_version=ENGINE_VERSION,
            narrative=(body.narrative if config.STORE_NARRATIVES else None),
        ),
        session,
    )
    explanation = None
    if body.explain:
        # The engine already decided; a summary failure must never
        # cost the caller their determinations.
        try:
            explanation = explain_mod.explain(profile, determinations)
        except Exception:
            logger.exception("explanation failed")

    resource_searches: list[ResourceSearch] = []
    if body.search_resources:
        try:
            resource_searches = resource_search.search_for_gaps(
                profile, determinations
            )
        except Exception:
            logger.exception("resource search failed")

    return ScreenResponse(
        complete=True,
        profile=profile,
        determinations=determinations,
        explanation=explanation,
        resource_searches=resource_searches,
    )


@router.post("/evaluate", response_model=list[Determination])
async def evaluate_profile(profile: HouseholdProfile):
    """Deterministic engine only — no LLM, no persistence."""
    try:
        return evaluate(profile)
    except KeyError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail=str(exc)) from exc
