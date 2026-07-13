"""Deterministic eligibility engine — no LLM code allowed here.

Every module in this package must be a pure function of
(HouseholdProfile, published thresholds). The LLM extracts and
explains; it never decides.
"""

from app.engine.runner import ENGINE_VERSION, evaluate

__all__ = ["ENGINE_VERSION", "evaluate"]
