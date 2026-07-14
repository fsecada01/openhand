# /about page — design

## Purpose

OpenHand currently has no in-app page that explains what it is, how it
works, or why it exists — that story only lives in `README.md`, which
end users on `openhandnavigator.org` never see. This spec adds a
public `/about` page aimed at the person about to type their
financial situation into the intake form, answering the question they
have before they trust it with that: *can this be trusted, and is it
just an AI guessing?*

## Non-goals

- No changes to `README.md` (it already covers this ground in depth
  for the GitHub/contributor audience).
- No header nav changes — the homepage's fast path to the form stays
  uncluttered.
- No new router file — this is one static page, added to the existing
  `screen.py` router alongside `GET /`.

## Route & rendering

Follows the existing full-page GET convention exactly
(`app/routers/screen.py:152-154`, the `GET /` route):

```python
@router.get("/about", response_class=HTMLResponse)
async def about():
    return HTMLResponse(catalog.render("About"))
```

New component: `app/components/About.jinja`, wrapped in
`<Layout title="About &mdash; OpenHand">`, same pattern as
`Home.jinja`.

## Footer link

`Layout.jinja`'s footer currently reads:

```
Not a government service. Estimates only — always confirm with the
program itself.
```

Add an "About this project" link to `/about` next to this line —
footer, not header, so the homepage CTA stays the focal point.

## Content structure

Voice matches the rest of the app: plain verbs, sentence case, no
filler, low reading level (see `Home.jinja`, `Confirm.jinja`).

1. **Trust/mechanism (lead section).** Opens with the split that
   matters most before someone types their situation into a
   stranger's form:

   > A language model reads what you type. A rules engine — the same
   > kind of logic real eligibility screeners use — decides what you
   > qualify for. The model never gets a vote on your results; it
   > only translates the outcome into plain English.

   Followed immediately by the 3-card visual (below) so the claim is
   reinforced visually, not just asserted in prose.

2. **Origin story.** Short paragraph, kept general rather than
   quantified: OpenHand grew out of watching real mutual aid requests
   and noticing how often what people were asking their community for
   was something a government program was already meant to cover. No
   specific numbers, source, or category breakdown — the point is the
   insight, not the methodology.

3. **Additive-to-mutual-aid stance.** One paragraph: mutual aid
   networks already do real-time, peer-to-peer triage faster than any
   government form ever will. OpenHand doesn't replace that — it
   routes what a formal program already owes someone so their
   community's capacity goes toward the gaps formal systems don't
   reach.

4. **Privacy, in plain terms.** Warm, not technical — no mention of
   sessions, storage internals, or system architecture. The point to
   land: OpenHand isn't trying to find out *who you are*, only what
   you need. It never asks for your name, address, ID numbers, or
   anything used to pay you back. Something like:

   > We're not trying to find out who you are — just what you need.
   > OpenHand never asks for your name, your address, or anything
   > that could pay you back or identify you. Describe your situation
   > in your own words; that's all it takes.

   This goes a level deeper than the homepage's "🔒 Nothing you type
   is stored" badge by naming *what kind of information is out of
   scope* (identity, contact, payment details), not just restating
   that nothing is stored.

5. **Closing link back to the form** (e.g., a button/link to `/`) so
   the page doesn't dead-end — someone reading About should be able
   to go straight back into the flow.

## Visualization

A 3-step, on-brand visual for the trust/mechanism section — built
from existing UI primitives, not a Mermaid flowchart (the README's
Mermaid diagram is for a technical audience; this page is for the
person about to use the form, and a raw flowchart would be the only
diagram anywhere in the UI, clashing with the app's plain-language
design principle).

```
[🗣️ You describe it]  →  [⚖️ Rules engine decides]  →  [💬 Plain-language answer]
   "no forms, no             "same rules real                "what to apply for,
    account"                  screeners use"                  where, what to bring"
```

Three `card bg-base-100 shadow-lg border border-base-300/60` cards in
a row (stacking on mobile via existing Tailwind/daisyUI responsive
utilities), each with an emoji, a 3-5 word label, and one short
supporting line — same visual language as `Confirm.jinja`'s 🤲 avatar
treatment and the homepage's trust badges, so it reads as part of the
app rather than a bolted-on diagram.

## Testing

- A request test for `GET /about` in `tests/test_web.py`, alongside
  the existing `client.get("/")` homepage test (`test_web.py:21`):
  assert 200 and that the response contains the trust-mechanism
  sentence.
- No new engine/LLM logic — nothing else to unit test.
