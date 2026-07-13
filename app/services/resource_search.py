"""Tavily web search: a non-authoritative fallback for programs the
federal screen matched poorly.

Explicitly out of scope for the "engine decides" rule — this never
touches eligibility status. It only surfaces state-based or other
online resources, presented as-is, when a determination is
`likely_ineligible` or `undetermined`. Skipped entirely (returns [])
if no TAVILY_API_KEY is configured, or if the search itself fails —
this is supplementary, never allowed to cost the user their results.
"""

import logging
from functools import lru_cache

from tavily import TavilyClient

from app import config
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

    searches: list[ResourceSearchResult] = []
    for d in poor_matches:
        query = (
            f"{d.program_name} alternatives or state assistance "
            f"programs in {profile.state} for someone who may not "
            "qualify for the federal program"
        )
        try:
            response = client.search(
                query=query,
                max_results=MAX_RESULTS_PER_PROGRAM,
                search_depth="basic",
            )
        except Exception:
            logger.exception("tavily search failed for %s", d.program)
            continue
        results = [
            ResourceLink(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", "")[:280],
            )
            for r in response.get("results", [])
        ]
        if results:
            searches.append(
                ResourceSearchResult(
                    program_name=d.program_name, query=query, results=results
                )
            )
    return searches
