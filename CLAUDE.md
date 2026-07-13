# Project Brainstorming Doc: Needs-Based Benefits & Mutual Aid Navigator

## 1. Origin & Problem Statement

This project originated from analysis of a real "Mutual Aid Monday" Facebook group thread. A full capture and categorization of that thread (217 unique comments) showed requests clustering into recurring needs categories: food & groceries, housing/rent/eviction, utilities, transportation/vehicle repair, general medical/health, dental, cancer/serious illness, mental health, income loss/employment transition, children/family/childcare, pet care, domestic violence/relocation/safety, elder/caregiving, disability/chronic illness income, general financial hardship/bills, education, and non-personal community outreach posts. About a third of comments were handle-only asks with no description. Requests frequently stack multiple categories in a single post (e.g., a job loss request that is simultaneously a housing and utility request).

**Core insight:** mutual aid networks are already doing real-time, peer-to-peer triage of needs that overlap heavily with existing government benefit programs (SNAP, Medicaid/CHIP, LIHEAP, EITC, unemployment, HUD housing assistance, etc.), but the people posting rarely know which formal programs they may already qualify for. A tool that helps surface that eligibility information could reduce reliance on ad hoc mutual aid for needs that a benefit program should already be covering — freeing mutual aid capacity for the gaps formal systems don't reach.

## 2. Mission & Design Principles

- **Needs-based, not program-based.** The user-facing organizing principle is "what do you need," not "which government form do you want." Categorization mirrors the taxonomy above.
- **Additive to mutual aid, never a replacement.** The tool should route people toward *both* formal benefits and existing mutual aid resources, not position itself as competing with or displacing community mutual aid networks.
- **Privacy-first by default.** No individual identifying information, payment handles, or personal narratives from any source data (e.g., scraped community posts) should ever be stored, displayed, or used for training/matching. This population is a known target for scams, which raises the bar further.
- **The LLM extracts and explains; it never decides.** This is the single most important architectural rule (see Section 4).

## 3. Prior Art Reviewed

- **NYCOpportunity/ACCESS-NYC-Rules** — the Drools rules engine behind NYC's live ACCESS NYC eligibility screener. Strongest public precedent for "rules as code" benefits eligibility.
- **PolicyEngine US** (`policyengine.org/us/api`) — hosted REST API (OAuth via Auth0) or self-hosted Docker image implementing a full household tax/benefit microsimulation model. Real candidate for the eligibility-computation backend.
- **OpenFisca** — the underlying rules-as-code framework ACCESS NYC and PolicyEngine build on.
- **sumitjindal1100-ui/sumit-public-benefits-navigator** — a solo portfolio project (built with Claude) that independently arrived at the same hybrid architecture recommended here: deterministic Python rules engine decides, Claude only parses intake and explains results, with an eval suite gating the rules engine. No license currently on the repo, so it's a design reference only, not a dependency — evaluate reaching out to the author about collaboration separately.
- **rubyforgood/mutual-aid** — a real (currently on-hiatus) community mutual-aid coordination platform. Relevant as prior art for mutual-aid-side UX/data modeling, not for benefits eligibility.
- Ruled out as building blocks: Benefits.gov (folded into USA.gov Benefit Finder, no API), USA.gov (no developer/API program), SAM.gov (contractor/grants data, not consumer eligibility), USDA/FNS SNAP (only aggregate statistical datasets, no individual eligibility API), Login.gov (integration restricted to registered government agencies via Inter-Agency Agreement).
- Usable federal data sources: CMS Marketplace API (developer.cms.gov — plan search, poverty-percentage calculation, state Medicaid data), HUD Fair Market Rent / Income Limits API and Housing Counselor locator (data.hud.gov) — data/reference sources, not decision engines.

## 4. Recommended Architecture

1. **Conversational intake (LLM).** User describes their situation in plain language or a short form. LLM parses this into a structured household object (household size, income, ages of dependents, state, disability status, etc.), using structured output/schema enforcement, and asks clarifying questions when a required fact is missing rather than guessing.
2. **Deterministic eligibility engine (no LLM).** The structured household object is passed to a rules engine — either a self-hosted OpenFisca-US instance or the PolicyEngine hosted API — which computes actual program-by-program eligibility. This layer must be auditable, testable, and versioned against published federal/state guidelines.
3. **Plain-language explanation (LLM).** A second, tightly-scoped LLM pass turns the engine's determinations into a warm, plain-language, low-reading-level summary with next steps and (separately, non-authoritative) relevant mutual aid resources. This layer is explicitly forbidden from altering or second-guessing the determination.
4. **Eval harness as a hard gate.** Every rules-engine change must pass a hand-verified household eval suite before merge — this is the safety net for the part that legally/ethically has to be right.

## 5. Tech Stack & Delivery Plan

- **Frontend (as built):** server-rendered JinjaX components + HTMX + daisyUI on FastAPI (revised from the original F#/Fable idea during implementation).
- **Target:** a curated, working POC/MVP deployed to the cloud — public-facing so real users can start using it, not just a local demo.
- **Feedback loop:** in-product UI for reporting bugs/feature requests. An LLM step extracts structured ticket fields (title, repro steps, severity/category, feature vs. bug) from free-text feedback and files issues against the public GitHub repo via the GitHub API.
- **Repo:** to be created fresh (not forked from sumit's project, per your decision) — MIT or similar permissive license from day one so this doesn't repeat the licensing ambiguity we just ran into.

## 6. Roadmap Phasing

- **Phase 1 (now):** Working POC/MVP — conversational intake, rules-engine eligibility check for a small initial set of programs (start narrow: SNAP, Medicaid/CHIP, EITC are the best-precedented), plain-language results, cloud-deployed.
- **Phase 2:** In-app feedback → LLM ticket extraction → auto-filed GitHub issues; expand program coverage; add state-level rule variation.
- **Phase 3 (explicitly gated, not near-term):** OAuth integration with financial institutions to pull banking data for instant eligibility determination. Gating conditions before this is even scoped: established user trust, clear data-use disclosures, data gating/siloing so financial data never comingles with other stored data, relevant certifications (SOC 2 and/or GLBA-adjacent safeguards), and financial backing or government-subsidized support to sustain the compliance burden. Standard aggregators (Plaid/MX/Finicity) pulling minimal verification attestations rather than raw transaction history would be the safer version of this if/when pursued.

## 7. Open Risks / Questions to Carry Into Claude Code

- Which state(s) to launch with first, given state-by-state variation in Medicaid expansion, CHIP, and LIHEAP thresholds?
- Where does the self-hosted OpenFisca-US vs. PolicyEngine-hosted-API tradeoff land for cost/control/latency?
- What's the minimal viable set of programs for the Phase 1 POC (recommend starting with SNAP + Medicaid/CHIP + EITC, mirroring the closest prior art)?
- What GitHub repo structure/issue templates best support LLM-generated tickets (labels, required fields)?
- How do we keep the "mutual aid resource" recommendations additive/non-competitive in the UI copy itself, not just in backend logic?