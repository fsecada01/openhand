"""Server-rendered screening flow (JinjaX components + HTMX)."""

from typing import Annotated

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
from app.models import Screening
from app.ui import catalog

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


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

    extraction = intake.extract(combined)
    if extraction.missing_required:
        return HTMLResponse(
            catalog.render(
                "Clarify",
                question=extraction.clarifying_question,
                prior_narrative=combined,
            )
        )

    profile = extraction.to_profile()
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

    explanation = explain_mod.explain(profile, determinations)
    return HTMLResponse(
        catalog.render(
            "Results",
            explanation=explanation,
            determinations=determinations,
        )
    )
