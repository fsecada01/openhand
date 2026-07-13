"""Explanation pass: engine determinations -> plain-language summary.

This pass is tightly scoped: it rewords the deterministic engine's
output at a low reading level and adds next steps. It is explicitly
forbidden from altering, second-guessing, or adding to the
determinations. Streaming is used server-side to avoid request
timeouts; callers get the final text.
"""

import json

from app import config
from app.llm.client import get_client
from app.schemas import Determination, HouseholdProfile

SYSTEM = """\
You turn benefit-screening results into a short, warm summary for the
person who asked. Write at a 6th-grade reading level.

Hard rules:
- The JSON determinations you receive are FINAL. Never change a
  status, add a program, remove one, or speculate about eligibility
  beyond what the reasons say. If a status is "undetermined", say
  plainly that the screener couldn't tell and who can.
- These are screening estimates, not decisions — only the agency that
  runs each program can decide. Say this once, simply.
- For each program: what the result means in one or two sentences,
  then the single next step (the apply link).
- Close by noting that local mutual aid networks remain a great
  resource alongside these programs — this tool adds options, it
  doesn't replace community help.
- No names, no personal details beyond what's in the profile.
- Output is rendered as plain pre-wrapped text, NOT markdown — never
  use **bold**, #headings, bullet dashes, or any markdown syntax.
  Use a program name on its own line followed by a blank line to set
  it apart, nothing else.
"""


def explain(
    profile: HouseholdProfile, determinations: list[Determination]
) -> str:
    payload = {
        "household": profile.model_dump(mode="json"),
        "determinations": [d.model_dump(mode="json") for d in determinations],
    }
    client = get_client()
    with client.messages.stream(
        model=config.ANTHROPIC_EXPLAIN_MODEL,
        max_tokens=8000,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": "Screening results to explain:\n"
                + json.dumps(payload, indent=2),
            }
        ],
    ) as stream:
        message = stream.get_final_message()
    return next((b.text for b in message.content if b.type == "text"), "")
