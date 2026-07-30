---
name: vc-pitch-deck
description: "Pitch-deck creation and teardown: maps the fundraising narrative onto a slide sequence, enforces per-slide requirements (problem, solution, traction, market, team, ask), and reviews decks against funded-deck patterns and investor attention data. Use when a founder is building an investor deck, reviewing or revising an existing deck, fixing one slide, or adapting between send-ahead, presented, and demo-day variants. Don't use for deciding round size, valuation, terms, or the narrative itself (use vc-strategy), nor for investor lists, outreach, or meetings (use vc-outreach)."
---

# VC Pitch Deck

Turns a startup's fundraising narrative and evidence into the deck artifact — and tears down existing decks the way investors actually read them. Distilled from a 625-source fundraising corpus (YC, Sequoia, NFX, DocSend telemetry, teardowns of funded decks); benchmarks carry source and year because deck norms drift.

## Paths

`<skill-dir>` = the directory containing this SKILL.md. Every `references/…` path below is relative to `<skill-dir>`; expand to an absolute path before reading when the CWD is elsewhere. All bundled files are reference (read-only).

## Branches

| Invocation | Do |
|---|---|
| Build a deck (new or rebuild) | Run Steps 1–5 |
| Review / tear down an existing deck | Read `references/teardown-rubric.md` in full; deliver verdicts per its protocol |
| Fix or draft a single slide | Read that slide's section in `references/slide-anatomy.md`, then run the per-slide checklist in `references/teardown-rubric.md` |
| Choose or adapt variants (send-ahead, presented, demo day, memo) | Read `references/sequences-and-variants.md` in full |

## Steps — building a deck

**Step 1: Assemble the input sheet.**
Collect, asking the founder only for what cannot be derived from their materials: stage and what is being raised; the narrative (one-liner, archetype, why-now, the earned secret); the evidence inventory (traction with time context, market math, team proof, competition, ask + milestones); the artifact needed and its audience. When the narrative is missing or the one-liner fails the three-nouns test (product, problem, customer all present — and ten people would build the same thing from it), invoke the vc-strategy skill to construct it first: the deck renders a narrative, it cannot substitute for one.
*Done when:* every input above is filled in and the one-liner passes the three-nouns test.

**Step 2: Pick the artifact and sequence.**
Read `references/sequences-and-variants.md` in full. Choose the variant for the moment and the sequence for the stage, then write the narrative as 10–15 bullets — one bullet = one slide, the bullet is the slide's title (YC "fundraising vertebrae"). Order the middle most→least impressive.
*Done when:* a slide list exists where each slide carries exactly one message, the titles read in order tell the whole story, and slide 1 states what the company does in one concrete layperson sentence.

**Step 3: Draft every slide.**
Work slide by slide from `references/slide-anatomy.md`, reading the section for each slide drafted. For traction, market, financials, and the ask, also apply `references/proof-slides.md` in full — every number dated, sourced, with time context.
*Done when:* every slide in the list is drafted and individually passes the per-slide checklist in `references/teardown-rubric.md`.

**Step 4: Tear down the draft.**
Read `references/teardown-rubric.md` in full and run it against the draft as a skeptical investor — 15-second pass first, then slide by slide. Fix what it catches and re-run.
*Done when:* the deck-level pre-send checklist passes on every item.

**Step 5: Package and hand off.**
Deliver: the deck content (per slide: title, body ≤30 words, visual spec); an appendix list seeded with every predictable objection; the export rule (PDF exported from the source file, never an editable file); and the process notes — customize per investor when the meeting matters, refine 1–2 hours per day of the raise, grow the appendix to ≥10 slides by mid-process. Route sending, sequencing, and meeting prep to the vc-outreach skill.
*Done when:* deck + appendix list + process notes are delivered and every open evidence gap is named explicitly.

## Devtools / AI-infra deltas

Apply when the company is a devtool or AI-infra product: move product/demo early — the evaluator is often a potential user; make the moat slide mandatory — "why can't a big player do this" is the default objection and weak differentiation is the #1 failure across 4,000+ graded decks (SaaStr, 2026); treat "AI" in the headline as table stakes (>40% of pitches lead with it — CB Insights, 2026) and state instead what is automated, what is augmented, and what stays human; add a GTM slide built on one channel that is already working, with unit economics; expect team pedigree to be overweighted for AI enablers; for a systems-insight argument, consider a memo alongside the deck — Northflank shipped both at seed (2025).

## Corpus deep-dive

When a claim needs source-level evidence beyond these references and `research/vc-funding/` exists in the workspace, search the corpus with `kb search "<query>" --lex --topic vc-funding` run from the `research/` directory (always `--lex`; hybrid and vector modes hang). Compiled articles live at `research/vc-funding/wiki/concepts/`.

## Reference index

- `references/sequences-and-variants.md` — variant matrix (send-ahead / presented / demo-day / memo), canonical sequences by stage, opening spec, slide counts, attention data, compression ladder. Load at Step 2 or when choosing variants.
- `references/slide-anatomy.md` — universal craft rules and per-slide requirements for every standard slide. Load per slide at Step 3.
- `references/proof-slides.md` — traction slide spec, pre-revenue proof stack, metric sets by business model, market-sizing credibility test, projection norms, the ask. Load at Step 3 for any numbers slide.
- `references/teardown-rubric.md` — how investors read decks, review protocol, per-slide and deck-level checklists, red flags with fixes, lessons from real funded-deck teardowns. Load at Step 4 and for any review.
