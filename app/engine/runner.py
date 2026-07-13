"""Run every program screen against a household profile."""

from app.engine import eitc, medicaid, medicare, snap
from app.schemas import Determination, HouseholdProfile

ENGINE_VERSION = "0.2.0-poc"


def evaluate(profile: HouseholdProfile) -> list[Determination]:
    results: list[Determination | None] = [
        snap.screen(profile),
        medicaid.screen_adult(profile),
        medicaid.screen_children(profile),
        medicaid.screen_pregnant(profile),
        medicare.screen(profile),
        eitc.screen(profile),
    ]
    return [d for d in results if d is not None]
