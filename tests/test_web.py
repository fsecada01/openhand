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
    assert "one more thing" in resp.text.lower()
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
    assert screen_router.EXPLANATION_FALLBACK.intro[:30] in resp.text
