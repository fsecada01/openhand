"""JSON API (v1)."""

from typing import Annotated

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
from app.models import Screening
from app.schemas import Determination, HouseholdProfile

router = APIRouter(prefix="/api/v1")
limiter = Limiter(key_func=get_remote_address)


class ScreenRequest(BaseModel):
    narrative: str = Field(min_length=1, max_length=5000)
    explain: bool = False


class ScreenResponse(BaseModel):
    complete: bool
    clarifying_question: str | None = None
    missing_required: list[str] = []
    profile: HouseholdProfile | None = None
    determinations: list[Determination] = []
    explanation: str | None = None
    engine_version: str = ENGINE_VERSION


@router.post("/screen", response_model=ScreenResponse)
@limiter.limit(config.RATE_LIMIT_SCREEN)
async def screen(
    request: Request,
    body: ScreenRequest,
    session: Annotated[Session, Depends(get_session)],
):
    extraction = intake.extract(body.narrative)
    if extraction.missing_required:
        return ScreenResponse(
            complete=False,
            clarifying_question=extraction.clarifying_question,
            missing_required=extraction.missing_required,
        )

    profile = extraction.to_profile()
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
    explanation = (
        explain_mod.explain(profile, determinations) if body.explain else None
    )
    return ScreenResponse(
        complete=True,
        profile=profile,
        determinations=determinations,
        explanation=explanation,
    )


@router.post("/evaluate", response_model=list[Determination])
async def evaluate_profile(profile: HouseholdProfile):
    """Deterministic engine only — no LLM, no persistence."""
    try:
        return evaluate(profile)
    except KeyError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail=str(exc)) from exc
