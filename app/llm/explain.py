"""Explanation pass: engine determinations -> plain-language summary.

This pass is tightly scoped: it rewords the deterministic engine's
output at a low reading level and adds next steps. It is explicitly
forbidden from altering, second-guessing, or adding to the
determinations. Output is structured (see `Explanation`) so the UI
can render real headings/lists instead of parsing markdown-in-text.
"""

import json
import logging

from app import config
from app.llm.client import get_client
from app.logging_utils import log_api_call
from app.schemas import Determination, Explanation, HouseholdProfile

logger = logging.getLogger(__name__)

SYSTEM = """\
You turn benefit-screening results into a short, warm summary for the
person who asked. Write at a 6th-grade reading level.

Hard rules:
- The JSON determinations you receive are FINAL. Never change a
  status, add a program, remove one, or speculate about eligibility
  beyond what the reasons say. If a status is "undetermined", say
  plainly that the screener couldn't tell and who can.
- These are screening estimates, not decisions — only the agency that
  runs each program can decide. Say this once, simply, in the intro
  or closing — not repeated per program.
- One section per program in `sections`, heading = the program's
  display name. Each section's `points`: what the result means in
  plain language, then the single next step (mention the apply link
  exists, the UI renders the actual link itself).
- `closing`: note that local mutual aid networks remain a great
  resource alongside these programs — this tool adds options, it
  doesn't replace community help.
- No names, no personal details beyond what's in the profile.
"""


def explain(
    profile: HouseholdProfile, determinations: list[Determination]
) -> Explanation:
    payload = {
        "household": profile.model_dump(mode="json"),
        "determinations": [d.model_dump(mode="json") for d in determinations],
    }
    client = get_client()
    with log_api_call(
        logger, "anthropic.explain", model=config.ANTHROPIC_EXPLAIN_MODEL
    ):
        response = client.messages.parse(
            model=config.ANTHROPIC_EXPLAIN_MODEL,
            max_tokens=4096,
            system=SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": "Screening results to explain:\n"
                    + json.dumps(payload, indent=2),
                }
            ],
            output_format=Explanation,
        )
    return response.parsed_output
