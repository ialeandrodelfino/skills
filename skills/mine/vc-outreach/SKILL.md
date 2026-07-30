---
name: vc-outreach
description: "VC outreach and raise execution: investor target lists (partner-level, tiered), warm-intro and cold-email plays that convert to first calls, meeting prep and objection handling, the parallel-process pipeline (batching, momentum, follow-ups), and diligence through close (data room, references, term-sheet-to-wire). Use when a founder needs an investor list, wants intros or cold emails to VCs, is preparing for or debriefing an investor meeting, is managing an active raise pipeline, or is assembling a data room. Don't use for deck authoring (use vc-pitch-deck) or for round sizing, narrative, and term economics (use vc-strategy)."
---

# VC Outreach

Runs the investor-facing raise motion: list → meeting → pipeline → close. Distilled from a 625-source fundraising corpus (NFX, Paul Graham, First Round, YC, Hustle Fund, real founder funnels with numbers); the raise is treated as an instrumented pipeline with health benchmarks, not a vibes campaign.

## Paths

`<skill-dir>` = the directory containing this SKILL.md. Every `references/…` path below is relative to `<skill-dir>`; expand to an absolute path before reading when the CWD is elsewhere. All bundled files are reference (read-only).

## Branches

| Invocation | Do |
|---|---|
| Run the raise end-to-end | Run Steps 1–5 |
| Build or refine the investor list | Read `references/targeting.md` in full; deliver the tiered, disqualified, referrer-mapped list |
| Get meetings (warm intro or cold email) | Read `references/getting-the-meeting.md` in full; produce the blurb/emails and the send plan |
| Prep or debrief an investor meeting | Read `references/meetings.md` in full; run its prep or follow-up checklist |
| Pipeline health, momentum, investor updates | Read `references/process-and-pipeline.md` in full; run the weekly review or produce the update |
| Data room, diligence, term-sheet-to-wire | Read `references/diligence-and-close.md` in full |

## Steps — running the raise

**Step 1: Verify the inputs.**
Confirm the strategy exists (narrative memo, round spec, milestone map — invoke vc-strategy if missing) and the deck exists (teaser + full — invoke vc-pitch-deck if missing). Then stage the machine: data room seeded before kickoff, running FAQ document started, CRM live with the eight pipeline stages, calendar blocked (a 2–3-week pitch window plus daily raise hours), momentum answer scripted.
*Done when:* every pre-kickoff readiness item in `references/process-and-pipeline.md` is checked.

**Step 2: Build the list.**
Read `references/targeting.md` in full. Build 100–200 partner-level names, run the disqualification pass (expect to cut ~30%), tier A/B/C (~30/30/40) crossed with access quality, and map 2–3 candidate referrers per Tier A target.
*Done when:* every surviving target has a tier, a research note with a nameable opening signal, and Tier A targets have referrers mapped.

**Step 3: Launch outreach.**
Read `references/getting-the-meeting.md` in full. Fire all intro requests in the same window (the blitzkrieg) so meetings cluster; cold-email only where no warm path exists, per the spec; sequence practice-tier before Tier A.
*Done when:* every target has outreach sent and logged with a dated next step, and first meetings are landing inside the chosen window.

**Step 4: Run meetings and pipeline.**
Read `references/meetings.md` and `references/process-and-pipeline.md` in full. For every meeting: prep checklist, run sheet, ≤24-hour follow-up, same-day logging, new tough questions converted to appendix slides. Weekly: the pipeline review with its numeric triggers, the objections-ledger review, and the same-pace correction so no lukewarm fund runs ahead of a favourite.
*Done when:* a term sheet is in hand — or a stop rule has fired (~6 partner meetings with unfixable feedback; 30–40 hard nos; air in the straw), in which case deliver the halt-and-diagnose verdict instead of pushing on.

**Step 5: Close.**
Read `references/diligence-and-close.md` in full. Staged disclosure through diligence; route term-sheet economics and negotiation to vc-strategy; keep selling until wired ("your round is not closed until the funds wire"); then set the post-close machine: investor-update cadence and the next round's target list.
*Done when:* funds are wired and the update cadence is scheduled — or the raise was halted and the post-mortem delivered.

## Corpus deep-dive

When a claim needs source-level evidence beyond these references and `research/vc-funding/` exists in the workspace, search the corpus with `kb search "<query>" --lex --topic vc-funding` run from the `research/` directory (always `--lex`; hybrid and vector modes hang). Compiled articles live at `research/vc-funding/wiki/concepts/`.

## Reference index

- `references/targeting.md` — list sizing, partner-level targeting, tiering, the disqualification pass, per-investor research, funnel math with real numbers. Load at Step 2.
- `references/getting-the-meeting.md` — the four access channels, forwardable blurb anatomy, referrer machinery, the cold-email spec with real exemplars, follow-up cadences and stop rules, deliverability engineering, pre-raise nurture. Load at Step 3.
- `references/meetings.md` — first-call run sheet, the question drills with answer scripts, partner-meeting mechanics, signal reading, the objections ledger, rejection handling and stop rules. Load at Step 4 and for any meeting prep or debrief.
- `references/process-and-pipeline.md` — pre-kickoff readiness, pipeline stages, batching and the same-pace rule, ethical momentum, weekly review with numeric triggers, raise telemetry, investor updates (pre- and post-raise). Load at Steps 1 and 4.
- `references/diligence-and-close.md` — staged disclosure gates, the data room (two access tiers + master index), reference-call management, reverse diligence on the investor, term-sheet-to-wire mechanics, signaling and round construction, announcement timing. Load at Step 5.
