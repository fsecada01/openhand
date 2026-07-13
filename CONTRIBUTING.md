# Contributing to OpenHand

Thanks for helping! People make real decisions based on what this
tool tells them, so the contribution rules below are mostly about
keeping the eligibility engine trustworthy.

## Dev setup

```bash
git clone https://github.com/fsecada01/openhand.git
cd openhand
uv sync --group dev
cp .env.example .env        # ANTHROPIC_API_KEY only needed for the
                            # LLM flow; engine work runs without it
just test                   # full suite
just lint                   # ruff check + format check
just dev                    # local server at :8000
```

Python 3.14, `uv` for packages, `ruff` for lint/format (80-char
lines), `pytest` for tests, `just` as the task runner.

## The golden rule

> **The LLM extracts and explains; it never decides.**

Nothing in `app/engine/` may import `anthropic` or `app.llm` — a
test enforces this. Eligibility logic must be a pure function of
`(HouseholdProfile, published thresholds)`.

## Changing the eligibility engine

Every engine change is gated by the hand-verified eval suite
(`tests/eval_households.json`). Your PR must:

1. **Cite the official source.** Every threshold in
   `app/engine/thresholds.py` links to the government publication it
   came from (USDA memo, HHS guidelines, IRS revenue procedure, ...).
   Blog posts and news articles don't count.
2. **State the effective dates** and update the program's
   `data_vintage` string — users see it under every result.
3. **Add or update eval households** covering the change, with the
   expected statuses verified by hand (show your arithmetic in the
   PR description).
4. **Keep the whole suite green:** `just test`.

When the data can't support an honest answer, return
`undetermined` with a pointer to who can help — never guess.

### Adding a new program screen

1. Create `app/engine/<program>.py` with a `screen(profile)` function
   returning a `Determination` (or `None` when not applicable).
2. Add thresholds to `thresholds.py` with source + effective dates.
3. Register it in `app/engine/runner.py` and bump `ENGINE_VERSION`.
4. Add eval households + unit tests.
5. If the screen needs new household facts, extend both
   `HouseholdProfile` and `IntakeExtraction` in `app/schemas.py`
   (with a field description — that's what the intake LLM reads).

## UI contributions

The frontend is JinjaX components (`app/components/*.jinja`) with
HTMX and daisyUI. Prefer composing the existing primitives
(`Form`, `SubmitButton`, `StatusBadge`, ...) over one-off markup.
Copy must stay plain-language (~6th-grade reading level) and must
never position benefits as replacing mutual aid.

## Privacy rules (non-negotiable)

- No PII in code, tests, fixtures, issues, or eval households —
  invented households only.
- Never add logging of narratives or extracted profiles.
- `STORE_NARRATIVES` stays `false` by default.

## Pull requests

- Branch from `main`; keep PRs focused.
- `just lint && just test` must pass (CI runs the same).
- Fill in the PR template — the engine checklist is required for any
  change under `app/engine/`.
- By contributing you agree your work is MIT-licensed.

## Not sure where to start?

Check issues labeled `good first issue` and `help wanted`, or the
high-impact list in the README (state data, new programs, eval
households, accessibility). Questions welcome in issues.
