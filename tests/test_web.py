"""Web-layer smoke tests (no LLM calls — engine-only endpoints)."""

import re

from fastapi.testclient import TestClient

from app.main import app


def _hidden_value(html: str, name: str) -> str | None:
    """Value of a `<input type="hidden" name="{name}" ...>` field,
    tolerant of the attribute wrapping onto its own line (see the
    Confirm/Clarify components).
    """
    m = re.search(rf'name="{name}"[^>]*value="([^"]*)"', html, re.S)
    return m.group(1) if m else None


def test_index_renders():
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "OpenHand" in resp.text
    assert "hx-post" in resp.text


def test_about_page_renders():
    with TestClient(app) as client:
        resp = client.get("/about")
    assert resp.status_code == 200
    assert "never gets a vote on your results" in resp.text
    assert "no user accounts" in resp.text.lower()
    assert "anthropic" in resp.text.lower()


def test_homepage_footer_links_to_about():
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert 'href="/about"' in resp.text


def test_mission_page_renders():
    with TestClient(app) as client:
        resp = client.get("/mission")
    assert resp.status_code == 200
    assert "don't need to stay coupled" in resp.text
    assert "github.com/fsecada01/openhand" in resp.text


def test_evaluate_endpoint_is_deterministic():
    payload = {
        "state": "TX",
        "household_size": 3,
        "monthly_gross_income": 2000,
        "monthly_earned_income": 2000,
        "num_children": 2,
        "filing_status": "head_of_household",
        "adult_age": 30,
    }
    with TestClient(app) as client:
        r1 = client.post("/api/v1/evaluate", json=payload)
        r2 = client.post("/api/v1/evaluate", json=payload)
    assert r1.status_code == 200
    assert r1.json() == r2.json()
    programs = {d["program"]: d["status"] for d in r1.json()}
    assert programs["snap"] == "likely_eligible"
    assert programs["medicaid_adult"] == "undetermined"


def test_evaluate_rejects_bad_profile():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/evaluate",
            json={"state": "Texas", "household_size": 0},
        )
    assert resp.status_code == 422


def test_screen_intake_failure_renders_error_alert(monkeypatch):
    from app.routers import screen as screen_router

    def boom(narrative):
        raise RuntimeError("simulated intake failure")

    monkeypatch.setattr(screen_router.intake, "extract", boom)
    with TestClient(app) as client:
        resp = client.post("/screen", data={"narrative": "help"})
    assert resp.status_code == 200
    assert "alert-error" in resp.text
    assert "Nothing you typed was stored" in resp.text
    # Error alerts ride on HTTP 200, so this header is the only thing
    # stopping Form.jinja from disabling the form the person needs to
    # retry with (see _error_alert).
    assert resp.headers.get("X-OpenHand-Error") == "1"


def test_screen_clarify_carries_round_num(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH",
            missing_required=["household_size", "monthly_gross_income"],
            clarifying_question="How many people, and about how much income?",
        ),
    )
    with TestClient(app) as client:
        resp = client.post("/screen", data={"narrative": "help"})
    assert resp.status_code == 200
    assert 'name="round_num" value="2"' in resp.text


def test_screen_finalizes_at_round_limit_with_missing_facts(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH",
            missing_required=["household_size", "monthly_gross_income"],
            clarifying_question="How many people, and about how much income?",
        ),
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "still don't know",
                "round_num": screen_router.MAX_TOTAL_ROUNDS,
            },
        )
    assert resp.status_code == 200
    assert "Start over" in resp.text
    assert "Clarify" not in resp.text


def test_screen_end_here_finalizes_early_with_missing_facts(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH",
            missing_required=["household_size", "monthly_gross_income"],
            clarifying_question="How many people, and about how much income?",
        ),
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "",
                "prior_narrative": "help",
                "round_num": 3,
                "finalize": "1",
            },
        )
    assert resp.status_code == 200
    assert "Start over" in resp.text


def test_screen_end_here_with_complete_facts_shows_results(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "",
                "prior_narrative": "help",
                "round_num": 3,
                "finalize": "1",
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text


def test_screen_supplemental_extraction_failure_keeps_results(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )

    def boom(narrative):
        raise RuntimeError("simulated supplemental failure")

    monkeypatch.setattr(
        screen_router.supplemental_mod, "extract_supplemental", boom
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen", data={"narrative": "help", "confirmed": "1"}
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text


def test_screen_complete_facts_shows_confirm_before_results(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    with TestClient(app) as client:
        resp = client.post("/screen", data={"narrative": "help"})
    assert resp.status_code == 200
    assert "did we" in resp.text.lower()
    assert 'name="confirmed" value="1"' in resp.text
    assert "SNAP" not in resp.text


def test_screen_adding_details_at_confirm_loops_back_for_more(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    with TestClient(app) as client:
        # "Add & continue" does NOT submit confirmed=1 — the handler
        # should show Confirm again (round 3), not jump to results,
        # so a person can add more than once within the round budget.
        resp = client.post(
            "/screen",
            data={
                "narrative": "I also have $500/mo in rent",
                "prior_narrative": "help",
                "round_num": 2,
            },
        )
    assert resp.status_code == 200
    assert "did we" in resp.text.lower()
    assert 'name="round_num" value="3"' in resp.text
    assert "SNAP" not in resp.text


def test_screen_confirm_prompt_varies_across_repeated_loops(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    with TestClient(app) as client:
        first = client.post(
            "/screen", data={"narrative": "help", "round_num": 1}
        )
        # "Add & continue" carries the confirm_round the first Confirm
        # card handed back — the second display must use a different
        # headline/body, not repeat the first verbatim.
        second = client.post(
            "/screen",
            data={
                "narrative": "one more thing",
                "prior_narrative": "help",
                "round_num": 2,
                "confirm_round": 1,
            },
        )
    assert screen_router.CONFIRM_PROMPTS[0][0] in first.text
    assert _hidden_value(first.text, "confirm_round") == "1"
    assert screen_router.CONFIRM_PROMPTS[1][0] in second.text
    assert screen_router.CONFIRM_PROMPTS[0][0] not in second.text
    assert _hidden_value(second.text, "confirm_round") == "2"


def test_screen_confirm_prompt_wraps_around(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    wrap_at = len(screen_router.CONFIRM_PROMPTS)
    with TestClient(app) as client:
        # round_num stays well under SOFT_GATHER_ROUNDS/MAX_TOTAL_ROUNDS
        # so this still shows Confirm again rather than finalizing —
        # only confirm_round (a separate counter) reaches the wrap
        # point being tested here.
        resp = client.post(
            "/screen",
            data={
                "narrative": "one more thing",
                "prior_narrative": "help",
                "round_num": 2,
                "confirm_round": wrap_at,
            },
        )
    assert screen_router.CONFIRM_PROMPTS[0][0] in resp.text


def test_screen_confirm_finalizes_at_round_limit(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    with TestClient(app) as client:
        # Still adding details, but the round cap is hit — finalize
        # with what we have instead of looping forever.
        resp = client.post(
            "/screen",
            data={
                "narrative": "one more thing",
                "prior_narrative": "help",
                "round_num": screen_router.MAX_TOTAL_ROUNDS,
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text


def test_screen_missing_facts_keep_asking_past_soft_gather_ceiling(
    monkeypatch,
):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH",
            missing_required=["monthly_gross_income"],
            clarifying_question="About how much income?",
        ),
    )
    with TestClient(app) as client:
        # Required facts still missing at the SOFT_GATHER_ROUNDS
        # ceiling — the soft ceiling governs the optional Confirm
        # step, not the required-facts Clarify loop, so this must
        # keep asking (up to the full MAX_TOTAL_ROUNDS budget)
        # instead of prematurely giving up with IncompleteResults.
        resp = client.post(
            "/screen",
            data={
                "narrative": "still not sure",
                "prior_narrative": "help",
                "round_num": screen_router.SOFT_GATHER_ROUNDS,
            },
        )
    assert resp.status_code == 200
    assert "one quick question" in resp.text.lower()
    assert "Start over" not in resp.text


def test_screen_soft_gather_limit_generates_results_without_confirm(
    monkeypatch,
):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    with TestClient(app) as client:
        # No `confirmed` and no `finalize` — but the soft gather
        # ceiling (round 5) should proactively generate the report
        # instead of showing Confirm again and waiting for an
        # explicit "that's everything".
        resp = client.post(
            "/screen",
            data={
                "narrative": "one more thing",
                "prior_narrative": "help",
                "round_num": screen_router.SOFT_GATHER_ROUNDS,
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text
    assert "did we" not in resp.text.lower()


def test_results_offers_feedback_form_within_round_budget(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "help",
                "round_num": 2,
                "confirmed": "1",
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text
    assert 'name="reported" value="1"' in resp.text
    assert 'name="round_num" value="3"' in resp.text
    assert "Update results" in resp.text


def test_screen_phase_two_feedback_regenerates_results(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_question", lambda q, s: None
    )
    with TestClient(app) as client:
        # `reported=1` means a report already exists — this round is
        # feedback, so it must go straight back to Results, never
        # back through Clarify/Confirm.
        resp = client.post(
            "/screen",
            data={
                "narrative": "actually my rent just went up",
                "prior_narrative": "help",
                "round_num": 3,
                "reported": "1",
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text
    assert "did we" not in resp.text.lower()
    assert 'name="round_num" value="4"' in resp.text


def test_screen_phase_two_question_triggers_targeted_search(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import (
        Explanation,
        IntakeExtraction,
        ResourceLink,
        ResourceSearch,
        SupplementalFacts,
    )

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="NY", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    seen = {}

    def fake_search_for_question(question, state):
        seen["question"] = question
        seen["state"] = state
        return ResourceSearch(
            program_name="About your question",
            query="job placement programs in NY",
            results=[
                ResourceLink(
                    title="NY job placement help",
                    url="https://example.com/jobs",
                    snippet="...",
                )
            ],
        )

    monkeypatch.setattr(
        screen_router.resource_search,
        "search_for_question",
        fake_search_for_question,
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": (
                    "What about job searching/placement programs in NYC?"
                ),
                "prior_narrative": "help",
                "round_num": 3,
                "reported": "1",
            },
        )
    assert resp.status_code == 200
    assert seen["question"] == (
        "What about job searching/placement programs in NYC?"
    )
    assert seen["state"] == "NY"
    assert "About your question" in resp.text
    assert "NY job placement help" in resp.text


def test_screen_no_new_text_skips_question_search(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )

    def fail_if_called(question, state):
        raise AssertionError(
            "search_for_question must not run without new text"
        )

    monkeypatch.setattr(
        screen_router.resource_search, "search_for_question", fail_if_called
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "",
                "prior_narrative": "help",
                "round_num": 3,
                "reported": "1",
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text


def test_results_no_feedback_form_at_round_limit(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_question", lambda q, s: None
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "help",
                "round_num": screen_router.MAX_TOTAL_ROUNDS,
                "reported": "1",
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text
    assert "Update results" not in resp.text
    assert "maximum number of rounds" in resp.text.lower()


def test_screen_supplemental_facts_merge_affects_engine_result(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="KS", household_size=1, monthly_gross_income=800
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(liquid_assets=5000),
    )
    monkeypatch.setattr(
        screen_router.explain_mod,
        "explain",
        lambda profile, determinations: Explanation(
            intro="intro", sections=[], closing=""
        ),
    )
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen", data={"narrative": "help", "confirmed": "1"}
        )
    assert resp.status_code == 200
    assert "asset" in resp.text.lower()


def test_screen_explanation_failure_keeps_results(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(
            state="OH", household_size=3, monthly_gross_income=2000
        ),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )

    def boom(profile, determinations):
        raise RuntimeError("simulated explain failure")

    monkeypatch.setattr(screen_router.explain_mod, "explain", boom)
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen", data={"narrative": "help", "confirmed": "1"}
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text
    # the fallback intro contains an apostrophe, which autoescape
    # renders as an entity — compare against the escaped form
    from markupsafe import escape

    assert (
        str(escape(screen_router.EXPLANATION_FALLBACK.intro[:30])) in resp.text
    )


def test_screen_phase_two_unchanged_profile_skips_rerun(monkeypatch):
    """A question that states no new facts must NOT re-run the
    engine/explanation/gap searches — only the question search."""
    from app.routers import screen as screen_router
    from app.schemas import (
        HouseholdProfile,
        IntakeExtraction,
        ResourceLink,
        ResourceSearch,
        SupplementalFacts,
    )

    seen = {}

    def fake_extract(narrative, **_):
        seen["extract_arg"] = narrative
        return IntakeExtraction()

    monkeypatch.setattr(screen_router.intake, "extract", fake_extract)
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )

    def fail(*args, **kwargs):
        raise AssertionError("must not run when the profile is unchanged")

    monkeypatch.setattr(screen_router.explain_mod, "explain", fail)
    monkeypatch.setattr(screen_router.resource_search, "search_for_gaps", fail)
    monkeypatch.setattr(
        screen_router.resource_search,
        "search_for_question",
        lambda q, s: ResourceSearch(
            program_name="About your question",
            query="job programs NY",
            results=[
                ResourceLink(
                    title="NY jobs help", url="https://example.com/jobs"
                )
            ],
        ),
    )

    profile = HouseholdProfile(
        state="NY", household_size=4, monthly_gross_income=12_000
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "What about job placement programs in NYC?",
                "prior_narrative": "help",
                "round_num": 4,
                "reported": "1",
                "profile_json": profile.model_dump_json(),
            },
        )
    assert resp.status_code == 200
    # only this round's new text went to the LLM, not the whole
    # accumulated narrative
    assert seen["extract_arg"] == ("What about job placement programs in NYC?")
    assert "still stand" in resp.text
    assert "About your question" in resp.text
    assert "NY jobs help" in resp.text
    # the follow-up form keeps carrying the profile and round counter
    assert _hidden_value(resp.text, "round_num") == "5"
    carried = _hidden_value(resp.text, "profile_json")
    assert carried is not None and "&#34;state&#34;:&#34;NY&#34;" in carried


def test_screen_phase_two_new_fact_regenerates_report(monkeypatch):
    """New facts in phase-2 overlay the carried profile and re-run the
    full report — without re-extracting the prior narrative."""
    from app.routers import screen as screen_router
    from app.schemas import (
        Explanation,
        HouseholdProfile,
        IntakeExtraction,
        SupplementalFacts,
    )

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n, **_: IntakeExtraction(monthly_gross_income=1_000),
    )
    monkeypatch.setattr(
        screen_router.supplemental_mod,
        "extract_supplemental",
        lambda n: SupplementalFacts(),
    )
    seen = {}

    def fake_explain(profile, determinations):
        seen["profile"] = profile
        return Explanation(intro="intro", sections=[], closing="")

    monkeypatch.setattr(screen_router.explain_mod, "explain", fake_explain)
    monkeypatch.setattr(
        screen_router.resource_search, "search_for_gaps", lambda p, d: []
    )
    monkeypatch.setattr(
        screen_router.resource_search,
        "search_for_question",
        lambda q, s: None,
    )

    profile = HouseholdProfile(
        state="NY", household_size=4, monthly_gross_income=12_000
    )
    with TestClient(app) as client:
        resp = client.post(
            "/screen",
            data={
                "narrative": "my income dropped to $1,000 a month",
                "prior_narrative": "help",
                "round_num": 4,
                "reported": "1",
                "profile_json": profile.model_dump_json(),
            },
        )
    assert resp.status_code == 200
    assert "SNAP" in resp.text
    # the new fact overrode the carried income; everything else the
    # phase-2 extraction didn't mention survived from the carried
    # profile
    assert seen["profile"].monthly_gross_income == 1_000
    assert seen["profile"].household_size == 4
    assert seen["profile"].state == "NY"
