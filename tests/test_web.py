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
