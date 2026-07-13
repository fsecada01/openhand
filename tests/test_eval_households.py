"""Hand-verified household eval suite — the hard gate for engine
changes. If one of these fails, the engine (or its thresholds) changed
behavior and must be re-verified against published guidelines.
"""

import json
from pathlib import Path

import pytest

from app.engine import evaluate
from app.schemas import HouseholdProfile

CASES = json.loads(
    (Path(__file__).parent / "eval_households.json").read_text()
)["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_household(case):
    profile = HouseholdProfile(**case["profile"])
    results = {d.program: d for d in evaluate(profile)}

    for program, status in case["expected"].items():
        assert program in results, f"{program} missing from results"
        actual = results[program].status.value
        assert actual == status, (
            f"{program}: expected {status}, got {actual} "
            f"(reasons: {results[program].reasons})"
        )

    for program in case.get("absent", []):
        assert program not in results, f"{program} should be absent"
