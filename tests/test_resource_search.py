"""Unit tests for app.services.resource_search (no live Tavily calls)."""

from app.schemas import Determination, HouseholdProfile, Status
from app.services import resource_search


class FakeTavilyClient:
    def __init__(self):
        self.queries: list[str] = []

    def search(self, query: str, max_results: int, search_depth: str):
        self.queries.append(query)
        return {
            "results": [
                {
                    "title": f"Result for {query[:20]}",
                    "url": "https://example.com",
                    "content": "snippet",
                }
            ]
        }


def _profile(**overrides) -> HouseholdProfile:
    base = dict(state="OH", household_size=1, monthly_gross_income=800)
    base.update(overrides)
    return HouseholdProfile(**base)


def test_search_for_gaps_queries_state_and_community_resources(monkeypatch):
    fake = FakeTavilyClient()
    monkeypatch.setattr(resource_search, "_get_client", lambda: fake)

    determinations = [
        Determination(
            program="snap",
            program_name="SNAP",
            status=Status.undetermined,
            reasons=[],
            apply_url="https://example.com/snap",
            data_vintage="2026",
            source_url="https://example.com/snap-source",
        )
    ]

    searches = resource_search.search_for_gaps(_profile(), determinations)

    labels = [s.program_name for s in searches]
    assert "SNAP" in labels
    assert "SNAP — mutual aid & private assistance" in labels

    community_query = next(
        s.query
        for s in searches
        if s.program_name == "SNAP — mutual aid & private assistance"
    )
    assert "mutual aid" in community_query
    assert "grant-based private assistance" in community_query
    assert "OH" in community_query


def test_search_for_gaps_adds_veteran_pair_independent_of_status(monkeypatch):
    fake = FakeTavilyClient()
    monkeypatch.setattr(resource_search, "_get_client", lambda: fake)

    searches = resource_search.search_for_gaps(
        _profile(is_veteran=True), determinations=[]
    )

    labels = [s.program_name for s in searches]
    assert "Veterans benefits" in labels
    assert "Veterans benefits — mutual aid & private assistance" in labels


def test_search_for_gaps_skips_likely_eligible_determinations(monkeypatch):
    fake = FakeTavilyClient()
    monkeypatch.setattr(resource_search, "_get_client", lambda: fake)

    determinations = [
        Determination(
            program="snap",
            program_name="SNAP",
            status=Status.likely_eligible,
            reasons=[],
            apply_url="https://example.com/snap",
            data_vintage="2026",
            source_url="https://example.com/snap-source",
        )
    ]

    searches = resource_search.search_for_gaps(_profile(), determinations)

    assert searches == []
    assert fake.queries == []


def test_search_for_gaps_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr(
        resource_search,
        "_get_client",
        lambda: (_ for _ in ()).throw(
            resource_search.TavilyNotConfiguredError()
        ),
    )
    assert resource_search.search_for_gaps(_profile(), []) == []


def test_search_for_question_uses_the_persons_own_words(monkeypatch):
    fake = FakeTavilyClient()
    monkeypatch.setattr(resource_search, "_get_client", lambda: fake)

    result = resource_search.search_for_question(
        "What about job searching/placement programs in NYC?", "NY"
    )

    assert result is not None
    assert result.program_name == "About your question"
    assert "job searching/placement programs" in result.query
    assert "NY" in result.query
    assert fake.queries == [result.query]


def test_search_for_question_blank_text_skips_the_search(monkeypatch):
    fake = FakeTavilyClient()
    monkeypatch.setattr(resource_search, "_get_client", lambda: fake)

    assert resource_search.search_for_question("   ", "NY") is None
    assert fake.queries == []


def test_search_for_question_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(
        resource_search,
        "_get_client",
        lambda: (_ for _ in ()).throw(
            resource_search.TavilyNotConfiguredError()
        ),
    )
    assert resource_search.search_for_question("job help", "NY") is None


def test_search_for_question_returns_none_when_search_fails(monkeypatch):
    class FailingClient:
        def search(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(resource_search, "_get_client", lambda: FailingClient())
    assert resource_search.search_for_question("job help", "NY") is None
