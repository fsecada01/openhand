"""Tavily web search: a non-authoritative fallback for programs the
federal screen matched poorly.

Explicitly out of scope for the "engine decides" rule — this never
touches eligibility status. For each determination that is
`likely_ineligible` or `undetermined` (plus a standing veteran-benefits
pair when the household reports veteran status, since no VA program is
screened by the engine), it runs two searches: one for other state
assistance programs, and one for local mutual aid networks, charities,
and grant-based private assistance — additive to mutual aid rather
than a formal-programs-only view. All results are presented as-is.
Skipped entirely (returns []) if no TAVILY_API_KEY is configured, or
if a given search fails — this is supplementary, never allowed to cost
the user their results.

`search_for_question` is a separate, narrower entry point for phase-2
feedback rounds: one extra search built from the person's own written
follow-up, rather than the fixed per-program queries above.
"""

import logging
from functools import lru_cache

from tavily import TavilyClient

from app import config
from app.logging_utils import log_api_call
from app.schemas import Determination, HouseholdProfile, ResourceLink, Status
from app.schemas import ResourceSearch as ResourceSearchResult

logger = logging.getLogger(__name__)

MAX_PROGRAMS = 3
MAX_RESULTS_PER_PROGRAM = 3
POOR_MATCH_STATUSES = {Status.likely_ineligible, Status.undetermined}


class TavilyNotConfiguredError(RuntimeError):
    """No TAVILY_API_KEY available."""


@lru_cache(maxsize=1)
def _get_client() -> TavilyClient:
    key = config.TAVILY_API_KEY.get_secret_value()
    if not key:
        raise TavilyNotConfiguredError("Set TAVILY_API_KEY in .env.")
    return TavilyClient(api_key=key)


def search_for_gaps(
    profile: HouseholdProfile, determinations: list[Determination]
) -> list[ResourceSearchResult]:
    try:
        client = _get_client()
    except TavilyNotConfiguredError:
        return []

    poor_matches = [
        d for d in determinations if d.status in POOR_MATCH_STATUSES
    ][:MAX_PROGRAMS]

    queries: list[tuple[str, str]] = []
    for d in poor_matches:
        queries.append(
            (d.program_name, _formal_query(d.program_name, profile.state))
        )
        queries.append(
            (
                f"{d.program_name} — mutual aid & private assistance",
                _community_query(d.program_name, profile.state),
            )
        )
    # No VA program is screened by the engine, so veteran status can
    # never surface here via a poor-match Determination — add it as
    # standing extra queries instead, independent of eligibility status.
    if profile.is_veteran:
        queries.append(
            (
                "Veterans benefits",
                "VA disability, pension, and other veterans benefits "
                f"in {profile.state}",
            )
        )
        queries.append(
            (
                "Veterans benefits — mutual aid & private assistance",
                _community_query("veterans", profile.state),
            )
        )

    searches: list[ResourceSearchResult] = []
    for program_name, query in queries:
        try:
            with log_api_call(logger, "tavily.search", program=program_name):
                response = client.search(
                    query=query,
                    max_results=MAX_RESULTS_PER_PROGRAM,
                    search_depth="basic",
                )
        except Exception:
            continue
        results = [
            ResourceLink(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=_clean_snippet(r.get("content", "")),
            )
            for r in response.get("results", [])
        ]
        if results:
            searches.append(
                ResourceSearchResult(
                    program_name=program_name, query=query, results=results
                )
            )
    return searches


def search_for_question(
    question: str, state: str
) -> ResourceSearchResult | None:
    """One targeted search for a phase-2 follow-up question.

    `search_for_gaps` only ever re-runs its fixed per-program queries,
    so a literal question typed into the post-report feedback box
    (e.g. "what about job placement programs?") was previously
    dropped on the floor — the regenerated report re-ran the same
    canned searches regardless of what the person actually asked.
    This runs one extra search using their own words instead.
    """
    question = question.strip()
    if not question:
        return None
    try:
        client = _get_client()
    except TavilyNotConfiguredError:
        return None

    query = (
        f"{question} — public benefits, social services, or assistance "
        f"programs in {state}"
    )
    try:
        with log_api_call(logger, "tavily.search", program="phase2_question"):
            response = client.search(
                query=query,
                max_results=MAX_RESULTS_PER_PROGRAM,
                search_depth="basic",
            )
    except Exception:
        return None

    results = [
        ResourceLink(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=_clean_snippet(r.get("content", "")),
        )
        for r in response.get("results", [])
    ]
    if not results:
        return None
    return ResourceSearchResult(
        program_name="About your question", query=query, results=results
    )


def _formal_query(program_name: str, state: str) -> str:
    return (
        f"{program_name} alternatives or state assistance programs in "
        f"{state} for someone who may not qualify for the federal program"
    )


def _community_query(need: str, state: str) -> str:
    return (
        "local mutual aid networks, charitable organizations, or "
        "grant-based private assistance programs administered by "
        f"social services agencies or nonprofits, for {need} in {state}"
    )


def _clean_snippet(content: str) -> str:
    """Collapse whitespace; keep the full text.

    Truncation is a display concern, not a data concern — the
    template previews this behind a "Read more" toggle instead of the
    snippet being cut short (and mid-word) here.
    """
    return " ".join(content.split())
