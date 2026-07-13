"""Web-layer smoke tests (no LLM calls — engine-only endpoints)."""

from fastapi.testclient import TestClient

from app.main import app


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
        lambda n: IntakeExtraction(
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
        lambda n: IntakeExtraction(
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
                "round_num": screen_router.MAX_CLARIFY_ROUNDS,
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
        lambda n: IntakeExtraction(
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
        lambda n: IntakeExtraction(
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
        lambda n: IntakeExtraction(
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
        resp = client.post("/screen", data={"narrative": "help"})
    assert resp.status_code == 200
    assert "SNAP" in resp.text


def test_screen_supplemental_facts_merge_affects_engine_result(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import Explanation, IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n: IntakeExtraction(
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
        resp = client.post("/screen", data={"narrative": "help"})
    assert resp.status_code == 200
    assert "asset" in resp.text.lower()


def test_screen_explanation_failure_keeps_results(monkeypatch):
    from app.routers import screen as screen_router
    from app.schemas import IntakeExtraction, SupplementalFacts

    monkeypatch.setattr(
        screen_router.intake,
        "extract",
        lambda n: IntakeExtraction(
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
        resp = client.post("/screen", data={"narrative": "help"})
    assert resp.status_code == 200
    assert "SNAP" in resp.text
    assert screen_router.EXPLANATION_FALLBACK.intro[:30] in resp.text
