# /mission page — design

## Purpose

`/about` (shipped) is written for the person about to use the intake
form — it answers "can I trust this with my situation?" This spec adds
a second, separate page aimed at a different audience entirely:
partners, funders, and technical collaborators evaluating *why*
OpenHand needs to exist as infrastructure. It makes the systemic case:
government benefit programs are fragmented, most expose no open data
or API for eligibility screening, and that absence is what forces
every screening effort to rebuild the same work from scratch.
OpenHand's architectural answer — decoupling plain-language intake
from per-program deterministic rules — is the page's thesis.

## Non-goals

- No changes to `/about`, `README.md`, or the homepage hero/form.
- No new visual component library — the two-column contrast reuses
  existing Tailwind grid utilities and the app's existing typography
  classes (`font-display`, `opacity-75`, etc.), no new CSS.
- Not a roadmap page — Phase 1 program coverage is mentioned once, for
  honesty, not itemized in detail (that already lives in
  `CLAUDE.md` § Roadmap Phasing for anyone who wants it).
- No new router file — one static page, added to `screen.py` alongside
  `GET /` and `GET /about`.

## Route & rendering

Same convention as `GET /about`:

```python
@router.get("/mission", response_class=HTMLResponse)
async def mission():
    return HTMLResponse(catalog.render("Mission"))
```

New component: `app/components/Mission.jinja`, wrapped in
`<Layout title="Our Mission &mdash; OpenHand">`.

## Footer

`Layout.jinja`'s footer currently (post `/about` work) reads:

```
Not a government service. Estimates only — always confirm with the
program itself. [About this project]
```

Add a second link, "Our mission," alongside the existing one — both
links visible to every visitor on every page (the project owner's
explicit choice: equal footing, not tucked behind `/about`).

## Content structure

Tone is deliberately more analytical/dense than `/about` — this reader
doesn't need reassurance, they need the argument. Still plain
language, no jargon for jargon's sake.

1. **The fragmentation thesis (lead).** Dozens of benefit programs,
   each with its own eligibility logic, almost none of which expose
   that logic as open data or an API. Every screening effort —
   including real prior art (NYC's ACCESS-NYC rules engine,
   PolicyEngine, OpenFisca) — ends up rebuilding the same "translate a
   life situation into eligibility" work per jurisdiction, per
   program, because there's no shared intake layer to plug into.

   > Government benefit programs weren't built to interoperate. Each
   > one has its own eligibility rules, its own application, and — in
   > almost every case — no open data or API a screening tool can
   > query directly. Efforts like NYC's ACCESS-NYC rules engine,
   > PolicyEngine, and OpenFisca have each proven that eligibility
   > logic *can* be modeled as code. What none of them share is a
   > common intake: every project re-asks the same questions about a
   > person's life, then answers them against just its own program.

2. **The overlap problem.** Someone eligible for SNAP is very often
   also eligible for Medicaid, EITC, or LIHEAP — the underlying
   financial thresholds overlap heavily — but each program still
   demands its own separate application, its own proof-gathering, its
   own "is it even worth applying" calculation.

   > Someone who qualifies for SNAP is often already close to
   > qualifying for Medicaid, EITC, or LIHEAP — the income thresholds
   > overlap far more than the applications do. Each program still
   > asks for its own paperwork, on its own portal, on its own
   > timeline. The red tape isn't incidental to the fragmentation —
   > it's a direct structural byproduct of programs that were never
   > designed to talk to each other, or to a shared front door.

3. **OpenHand's architectural thesis**, with a two-column contrast
   (see Visualization below). Core claim, in prose immediately before
   the contrast:

   > OpenHand's bet is that the two halves of this problem don't need
   > to stay coupled: understanding what a person's situation actually
   > is, and deciding whether a specific program's rule applies to
   > that situation. Separate those, and a single conversation can be
   > evaluated against as many programs' rules as have been modeled —
   > without asking that person anything new for each one.

4. **Honest state of the vision.** One short paragraph — no
   overclaiming:

   > Today, that means three programs: SNAP, Medicaid/CHIP, and EITC.
   > The point of this page isn't that OpenHand already covers
   > everything — it's that the architecture is built to extend.
   > Adding a fourth program means modeling that program's rules, not
   > rebuilding the intake.

5. **Call to action.** Closes with a link to the GitHub repo:

   > The engine is built to extend. If you work with eligibility rules
   > for a program not covered yet — or want to help model one — [the
   > repo](https://github.com/fsecada01/openhand) is where that
   > happens.

## Visualization

A plain two-column contrast, directly below section 3's lead
paragraph — no cards, no new components, just a Tailwind grid
(`grid sm:grid-cols-2 gap-6`) with two labeled columns:

```
Today                              OpenHand
─────                              ────────
Separate intake per program        One plain-language intake
Separate rules interpretation      Evaluated against every modeled
per program                        program's rules
Red tape multiplied by however     Adding a program never means
many programs might apply          asking the person anything new
```

Each column is a simple `<div>` with a bold header (`font-semibold`)
and a short `<ul>` of 3 lines (`text-sm opacity-75`) — matching the
existing typographic scale used throughout `About.jinja` and
`Home.jinja`, no new visual language introduced.

## Testing

- A request test for `GET /mission` in `tests/test_web.py`, alongside
  the existing `/about` test: assert 200, and that the response
  contains the core thesis phrase ("don't need to stay coupled") and
  the GitHub repo link (`github.com/fsecada01/openhand`).
- A test that the homepage footer links to `/mission` (mirrors the
  existing `test_homepage_footer_links_to_about` test).
- No new engine/LLM logic — nothing else to unit test.
