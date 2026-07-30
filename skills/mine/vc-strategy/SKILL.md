---
name: vc-strategy
description: "Fundraising strategy for startups: fundability assessment against what VCs actually evaluate, the fundraising narrative and value proposition (positioning, why-now), round design (when to raise, how much, valuation, SAFE vs priced, dilution, milestones), term-sheet economics and negotiation, and devtools/AI-infra positioning (open source, platform risk, developer traction). Use when a founder asks whether or when to raise, how much and on what instrument, needs a value proposition or fundraising narrative, is weighing term-sheet terms, or must position a technical product for investors. Don't use for authoring deck slides (use vc-pitch-deck) or for running investor outreach, meetings, and pipeline (use vc-outreach)."
---

# VC Strategy

Designs the fundraise before any artifact exists: whether and when to raise, the narrative and value proposition, the round's size, price, and instrument, and the terms to accept or fight. Distilled from a 625-source fundraising corpus (Paul Graham's essays, YC, NFX, CRV, Carta/Cooley data, first-hand founder and investor accounts); numbers carry source and vintage because market norms drift fast.

## Paths

`<skill-dir>` = the directory containing this SKILL.md. Every `references/…` path below is relative to `<skill-dir>`; expand to an absolute path before reading when the CWD is elsewhere. All bundled files are reference (read-only).

## Branches

| Invocation | Do |
|---|---|
| Design the fundraise end-to-end | Run Steps 1–5 |
| Fundability check ("can/should we raise?") | Read `references/what-vcs-evaluate.md` in full; run its fundability self-assessment; deliver the verdict |
| Narrative / value proposition only | Read `references/narrative-playbook.md` in full; produce the narrative memo through its stress-test |
| Round sizing, valuation, instrument | Read `references/round-design.md` in full plus `references/stage-benchmarks.md`; produce the round spec |
| Term sheet on the table | Read `references/deal-terms.md` in full; run the red-flag scan; deliver the clause-by-clause read |
| Devtools / AI-infra positioning | Read `references/devtools-positioning.md` in full |

**Devtools / AI-infra companies:** whichever branch runs, read `references/devtools-positioning.md` in full before producing output — layer naming, the rent-duration answer, the platform-incumbent answer, and the OSS→commercial narrative change what every other reference recommends.

## Steps — designing the fundraise

**Step 1: Map the company.**
Collect from the founder and their materials: maturity stage in evidence terms (team / product / repeatable sale / unit economics — not just the round label); traction facts with time context; market and ICP; team and what's in-house; cash, runway, burn; existing cap table including every SAFE at its cap; what they think they're raising and why.
*Done when:* every item is filled in and each SAFE's conversion at cap is modeled.

**Step 2: Diagnose fundability.**
Read `references/what-vcs-evaluate.md` in full. Run the fundability self-assessment and the fund-math arithmetic for the intended investor class (check ≈ 2% of fund size; ownership 10–20%; a credible fund-returning exit). Deliver one of three verdicts: **raise now** / **fix first** (with the specific failing criteria and what closes them) / **different capital** (angels, revenue, smaller round — when venture math doesn't fit).
*Done when:* the verdict is delivered with every failing criterion named and the fund-math computed for at least one named fund profile.

**Step 3: Construct the narrative.**
Read `references/narrative-playbook.md` in full. Produce the narrative memo: archetype and point-of-view template chosen consciously, a why-now that survives its test, the compression ladder (one-liner through two-sentence + example), the earned secret, and the risks section written by the founder's side.
*Done when:* the memo passes every item of the narrative stress-test checklist.

**Step 4: Design the round.**
Read `references/round-design.md` in full and pull current bars from `references/stage-benchmarks.md`. Produce the round spec: amount (milestone-first, cross-checked against burn-first and runway-first — convergence within ~20%); instrument (via the decision matrix in `references/deal-terms.md`); valuation posture (a defensible range, sanity-checked with the ⅓ rule against a realistic next round); dilution budget; and the milestone map that buys the *next* round's bar.
*Done when:* the round spec passes the raise-now-or-wait readiness test and the sizing worksheet is complete with all three methods shown.

**Step 5: Deliver the strategy.**
Assemble one document: verdict + narrative memo + round spec + milestone map + the champion-arming kit (the three sentences, the one-pager, the pre-answered risks) + open gaps stated plainly. Route deck rendering to vc-pitch-deck, pipeline and meetings to vc-outreach, and term-sheet review back here when paper arrives.
*Done when:* the strategy document is delivered and every unresolved risk or evidence gap is listed in it explicitly.

## Corpus deep-dive

When a claim needs source-level evidence beyond these references and `research/vc-funding/` exists in the workspace, search the corpus with `kb search "<query>" --lex --topic vc-funding` run from the `research/` directory (always `--lex`; hybrid and vector modes hang). Compiled articles live at `research/vc-funding/wiki/concepts/`.

## Reference index

- `references/what-vcs-evaluate.md` — fund-returner arithmetic, ownership/check math, the six criteria by stage, the screening gates, the partnership decision system (champion, partner meeting, memo, IC), herd dynamics, fundability self-assessment, champion-arming kit. Load at Step 2 and for any fundability question.
- `references/narrative-playbook.md` — memo-before-deck, narrative archetypes and POV templates, why-now construction and test, compression and legibility tests, category-creation doctrine, the earned secret, narrative stress-test. Load at Step 3 and for any positioning work.
- `references/round-design.md` — readiness test, three sizing methods and worksheet, valuation methods (⅓ rule, 20% ratio, staircase), dilution norms, bridges, alternatives to VC. Load at Step 4.
- `references/deal-terms.md` — instrument decision matrix, SAFE hygiene and conversion math, economics vs control, clause red-flag scan with market prevalence, negotiation moves. Load at Step 4 for the instrument and in full when a term sheet exists.
- `references/stage-benchmarks.md` — the numbers by stage with vintage and conflicts flagged: round sizes, valuations, dilution, ARR bars, graduation rates, timing. Load whenever a current-market number is asserted. (Also the single source vc-pitch-deck points at for stage bars.)
- `references/devtools-positioning.md` — rent-duration test, layer triage, the Siroker four-part answer, moat taxonomy, OSS→commercial narrative (Seibel's incumbent-at-your-size, the Expanso template), usage-based revenue spec, metrics investors trust vs discount, devtools investor map, corpus gaps stated honestly. Load for any technical-product positioning.
