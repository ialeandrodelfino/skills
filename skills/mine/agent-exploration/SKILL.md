---
name: agent-exploration
description: >-
  Dispatches scoped-write explorer agents in parallel — native harness
  subagents by default, official harness CLIs (claude, codex, cursor-agent)
  only when the operator requests an external harness or model — for
  multi-area research that must produce written artifacts — one seven-section
  analysis file per slice plus a parent-authored summary. Use when a research
  question spans several distinct areas and chat output is not enough. Do not
  use for single-file lookups (use Explore) or edits to existing code.
disable-model-invocation: true
argument-hint: "[--path <dir>] [--agents <num>] [--prompt <text>] [--model <model>] [--harness claude|codex|cursor-agent] [--reasoning <effort>]"
metadata:
  author: Pedro Nauck
  github: https://github.com/pedronauck
  repository: https://github.com/pedronauck/skills
---
# Agent Exploration

Generic parallel-research workflow. Use when a question requires deep reads across multiple distinct areas and the operator needs written artifacts (not chat output). The skill dispatches scoped-write `explorer` agents in parallel; each invocation writes one analysis file. The parent then synthesizes a final summary.

**Native subagents are the default dispatch route.** Each slice runs as a subagent of the current harness (in Claude Code: one `Agent` tool call per slice), inheriting the session's model and reasoning effort unless the operator pins a model. External CLIs are the exception, not the norm: only when the operator requests a harness or a model the native subagent cannot serve does a slice run through an official harness CLI — `claude` (Claude models), `codex` (gpt-*), `cursor-agent` (Grok). There is no agent registry and nothing to install: the explorer's role, contract, and schema travel inside each slice prompt, identical on both routes.

## Required Reading Router

Match your step to the row. Read the listed files **in full before** producing output. They are not appendices — they are load-bearing. Inline content in this SKILL.md is a pointer, not a substitute.

| Step                                                    | MUST read                                                                                      |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Step 4 — composing every slice prompt                   | `references/dispatch-rules.md` + `assets/explorer-prompt.md` + `assets/analysis-template.md`   |
| Step 5 — verifying outputs                              | `references/checklist.md` + `assets/analysis-template.md`                                      |
| Step 6 — synthesizing `summary.md`                      | every `<path>/analysis/NN_analysis_<slug>.md` from this round                                  |
| Any contract violation, fabricated evidence, or retry   | `references/dispatch-rules.md` (re-read; do not paraphrase from memory)                        |

## Reference Index

- `references/dispatch-rules.md` — the scoped-write contract: what the dispatched agent may write, may read, may run; tool allow/forbid lists; parent responsibilities per dispatch route; parallelism cap; failure handling. **Must be embedded verbatim in every slice prompt.**
- `references/checklist.md` — seven-section output validation checklist (runtime, inputs, scout, dispatch, files, schema, summary). Run before authoring `summary.md`.
- `assets/analysis-template.md` — the canonical seven-section schema every dispatched agent fills (Overview, Mechanisms/Patterns, Relevant Sources, Transferable Patterns, Risks/Mismatches, Open Questions, Evidence) plus a Scope header.
- `assets/explorer-prompt.md` — the explorer role prompt (the scoped-write contract and workflow from the dispatched agent's perspective). **Embedded verbatim at the top of every slice prompt** — native subagent or CLI, same text.
- `scripts/dispatch-slices.sh` — CLI-route parallel dispatch runner. Takes `--cli`/`--model`/`--reasoning` plus 1-8 prompt files, backgrounds one headless CLI process per file, waits via `wait $pid`, captures per-slice stdout/stderr/exit, and reports a summary. Zero external dependencies (native bash + the chosen CLI binary). Not used on the native route.

## Bundled Path Rule

Resolve every bundled helper relative to the directory that holds this `SKILL.md`. When a command appears below as `scripts/<name>`, treat the actual invocation as `<agent-exploration-dir>/scripts/<name>` — expand `<agent-exploration-dir>` to the absolute skill directory before running.

## Required Inputs

- `--path <dir>` (required): Output directory. Analysis files are written under `<path>/analysis/`. Any project-relative or absolute directory works (for example `docs/research/<topic>/`, `tasks/<slug>/`, or a path outside the repo). The skill is not tied to any specific project layout.
- `--agents <num>` (optional, default 3, hard cap 8): Number of explorer invocations to dispatch in parallel.
- `--prompt <text>` (required): The research question. Quoted multi-line strings are supported. If omitted, the parent asks the operator before continuing.
- `--model <name>` (optional; default: inherit the parent session's model on the native route): The model to run each slice on — and the routing signal. See **Dispatch Routing** for how a model name selects native subagents vs. an external CLI.
- `--harness <claude|codex|cursor-agent>` (optional): Force the external-CLI route on that binary regardless of model. Omit for native subagents.
- `--reasoning <effort>` (optional): `low`, `medium`, `high`, `xhigh`. Native route: not forwardable — subagents inherit the session's effort; the flag applies to CLI dispatches (`claude --effort`, `codex -c model_reasoning_effort=…`; `cursor-agent` ignores it — effort is baked into the Grok model id). Default `xhigh` on CLI routes.

If `--path` or `--prompt` is missing, the parent asks the operator a single clarification before continuing. Never invent defaults for either. Apply the documented defaults for `--model`, `--harness`, `--reasoning` silently when omitted; reject an invalid `--harness` rather than falling back.

## Dispatch Routing

Native unless the operator explicitly requests otherwise. A model or harness request routes to the one runtime that can serve it — never silently substitute a different harness or model than requested.

| Request                                                          | Route                                                                                     |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| No `--model` / `--harness` (default)                             | Native subagents; each slice inherits the session's model and effort.                      |
| `--model sonnet\|opus\|haiku\|fable` and the parent harness exposes it natively (Claude Code does) | Native subagents with a per-call model override.                     |
| `--model` names a Claude model the parent harness cannot serve natively | `claude` CLI.                                                                       |
| `--model gpt-*`                                                  | `codex` CLI.                                                                               |
| `--model` names a Grok variant (`grok`, `cursor-grok-*`)         | `cursor-agent` CLI.                                                                        |
| `--harness <cli>`                                                | That CLI, regardless of model.                                                             |

CLI model notes:

- **claude** — accepts aliases (`fable`, `opus`, `sonnet`) or full names (`claude-fable-5`); effort via `--effort low|medium|high|xhigh|max`.
- **codex** — omit `-m` to use the operator's `~/.codex/config.toml` default; effort via `-c model_reasoning_effort=low|medium|high|xhigh`.
- **cursor-agent** — exact ids from `cursor-agent models`. Grok ids embed effort and fast mode: `cursor-grok-4.5-{low,medium,high}[-fast]`. Default Grok profile: `cursor-grok-4.5-high-fast` (breadth research, cost-sensitive runs, high slice counts).

## Output Layout

```
<path>/analysis/
├── 01_analysis_<slug-a>.md
├── 02_analysis_<slug-b>.md
├── 03_analysis_<slug-c>.md
└── summary.md
```

- File numbering is zero-padded to two digits (`01`, `02`, …, `08`).
- Each slug is a short kebab-case identifier the parent assigns during the scout (Step 3), reflecting that slice's focus.
- `summary.md` is parent-authored synthesis, not a dispatched output.

## Procedures

**Step 1: Resolve the dispatch route**

1. Apply **Dispatch Routing** to the operator's `--model`/`--harness` inputs and announce the resolved route in one line (e.g. `route: native (session model)` or `route: codex CLI (gpt-5.3-codex, xhigh)`).
2. Native route: there is nothing to install or verify — the harness's own subagent facility is the runtime. If the parent harness has no native subagent facility at all, use the CLI route with the `claude` binary and tell the operator.
3. CLI route: confirm the chosen binary is on `PATH` (`command -v claude|codex|cursor-agent`). If missing, abort with a one-line message telling the operator to install that harness's official CLI. Never silently reroute an explicitly requested harness or model to a different one.

**Step 2: Resolve inputs**

1. Parse `--path`, `--agents`, `--prompt`, `--model`, `--harness`, `--reasoning` from the invocation. If `--path` or `--prompt` is missing, ask the operator and stop.
2. Default `--agents` to `3` when omitted. Reject values below 1 or above 8 — ask the operator to choose a value in range.
3. Validate `--harness` against the accepted list (`claude`, `codex`, `cursor-agent`) and `--reasoning` against `low`, `medium`, `high`, `xhigh`; reject invalid values with a clear message instead of silent fallback. Do not validate `--model` ahead of time — let the harness or CLI surface incompatibilities; when one does, re-dispatch that slice with a compatible model.
4. Resolve `--path` to an absolute path. If the directory does not exist, ask the operator whether to create it before continuing; if creation fails, stop and report the filesystem error.
5. Create `<path>/analysis/` if absent. The dispatched agents refuse to write into a missing directory.

**Step 3: Parent-led initial scout (MANDATORY — do not skip)**

The scout is the load-bearing step that prevents wasted parallel dispatch. The parent must do this work itself before any slice is launched.

1. Perform a brief read-only exploration of the problem space using `Glob`, `Grep`, and targeted `Read` calls. The scout's job is to learn enough about the territory to divide it well — not to produce analysis content. Cap the scout at 8–15 tool calls; deep reading belongs to the dispatched agents.
2. From the scout, identify exactly `--agents` distinct slices that are:
   - **Non-overlapping** — two slices should not require reading the same primary files for the same purpose.
   - **Independently answerable** — a slice's analysis must not depend on another slice's output.
   - **Aligned with the operator's `--prompt`** — every slice serves the original research question.
3. For each slice, assign:
   - A two-digit ordinal (`01`..`08`).
   - A short kebab-case slug (≤ 4 words) reflecting that slice's focus (e.g. `state-machine`, `event-bus`, `auth-boundaries`).
   - A focused per-slice prompt that names the slice question, the primary source paths/URLs to read, and any cross-references the dispatched agent should use.
4. Briefly tell the operator the slice list (one line per slice: `NN – slug – focus`) before dispatching. Do not ask for approval unless the slices look thin or overlap; just announce and proceed.

If the scout reveals that fewer than `--agents` non-overlapping slices exist, reduce the dispatch count and tell the operator. Do not pad slices to hit the requested count.

**Step 4: Dispatch explorer agents in parallel**

Gist tripwires — the contract items the parent must enforce in every dispatched prompt:

- The prompt names three things: slice scope, slug+ordinal, exact target file path. If any is missing, the dispatched agent must refuse and ask back.
- The dispatched agent gets exactly one file-write — at the named target path — and nothing else. No edits, no `git`/`make`/package managers, no writes outside `<path>/analysis/`.
- All slices dispatch in parallel — native route: one subagent call per slice issued in a single batch; CLI route: one backgrounded process per slice. Wait for every slice to finish before verification.

**STOP. Read `references/dispatch-rules.md` in full before composing any slice prompt.** That file contains the complete scoped-write contract, tool allow/forbid lists, parent responsibilities per route, and failure handling. The bullets above are tripwires, not the contract — the contract must be embedded verbatim in every slice prompt.

**STOP. Read `assets/explorer-prompt.md` in full before composing any slice prompt.** That file is the explorer's role prompt — it must open every slice prompt verbatim so the dispatched agent knows its contract regardless of route.

**STOP. Read `assets/analysis-template.md` in full before composing any slice prompt.** That file is the canonical seven-section schema every dispatched agent fills. The schema must be embedded in the prompt; do not paraphrase it.

Compose one slice prompt per slice. Every prompt MUST include, in this order:
- `assets/explorer-prompt.md` content embedded verbatim (the explorer's role and contract).
- The operator's original `--prompt` verbatim, prefixed by a short orientation line.
- The slice's focused question and the primary sources to read.
- The exact target path: `<path>/analysis/NN_analysis_<slug>.md` (absolute path).
- `references/dispatch-rules.md` content embedded verbatim (copy-paste, do not paraphrase).
- The seven-section schema from `assets/analysis-template.md`.

Write each composed prompt to its own file at `<path>/.dispatch/prompts/NN_<slug>.txt`. The CLI route consumes these files directly; on the native route they keep the round auditable and re-dispatchable. The file basename (without extension) is the slice id used for per-slice log naming.

**Native route (default).** Issue one subagent call per slice — all in a single parallel batch, using whatever async/background facility your harness exposes. In Claude Code: one `Agent` tool call per slice with the general-purpose agent type (the explorer needs `Read`/`Grep`/`Glob` plus one `Write`), `prompt` = the slice prompt file content verbatim, and a `model` override only when the operator pinned one. Wait for every subagent to complete before Step 5. A subagent that errors, or returns without its written-path confirmation, is a failed slice — re-dispatch it.

**CLI route (exception): `scripts/dispatch-slices.sh`.** The bundled script backgrounds one headless CLI process per prompt file, waits for every PID, captures per-slice stdout/stderr/exit under `<logs-dir>`, and exits non-zero if any slice failed.

```
<agent-exploration-dir>/scripts/dispatch-slices.sh \
  --cli <claude|codex|cursor-agent> --model <model> --reasoning <reasoning> \
  --add-dir <path> \
  --logs <path>/.dispatch/logs \
  -- <path>/.dispatch/prompts/01_<slug-a>.txt \
     <path>/.dispatch/prompts/02_<slug-b>.txt \
     <path>/.dispatch/prompts/03_<slug-c>.txt
```

- The script prints `dispatched: <slug> pid=<N>` per launch and `exited: <slug> rc=<N>` per completion, ending with a `summary: total=Xs ok=N/M failed=K/M` line.
- The script hard-caps at 8 slices per invocation, matching the parallelism cap in `references/dispatch-rules.md`.

**Manual alternative** (if you cannot run a bash script): invoke each slice with the exact command shape for the resolved CLI. Use whatever async/background facility your harness exposes; wait for every invocation to exit before continuing.

```
# claude — Claude models (aliases fable|opus|sonnet, or full names)
claude -p --model <model> --effort <reasoning> \
  --permission-mode dontAsk \
  --allowedTools "Read Glob Grep WebFetch WebSearch Write Bash(rg *) Bash(ls *) Bash(cat *) Bash(head *) Bash(wc *) Bash(file *) Bash(find *)" \
  --add-dir <path> < <prompt-file>

# codex — gpt-* models (omit -m to use the ~/.codex/config.toml default)
codex exec -m <model> -c model_reasoning_effort=<reasoning> \
  -s workspace-write -c sandbox_workspace_write.network_access=true \
  --skip-git-repo-check --add-dir <path> \
  -o <path>/.dispatch/logs/<slug>.last.md - < <prompt-file>

# cursor-agent — Grok (effort/fast baked into the model id)
cursor-agent -p --output-format text --force \
  --model cursor-grok-4.5-high-fast \
  --add-dir <path> "$(cat <prompt-file>)" < /dev/null
```

Notes that apply to both paths:

- `--add-dir <path>` (supported by all three CLIs) is required whenever `<path>` lies outside the working tree the CLI is launched in; harmless otherwise.
- The `claude` allowlist mirrors the contract's read-only helpers plus one `Write`; `--permission-mode dontAsk` auto-denies everything else — harness-level enforcement of the scoped-write contract.
- `codex` `workspace-write` disables network by default; the `sandbox_workspace_write.network_access=true` override keeps web-scoped slices working. Drop it for purely local slices if you want the tighter sandbox.
- Treat any failed slice — non-zero exit on the CLI route, an errored or confirmation-less subagent on the native route — as a slice failure and re-dispatch it with the contract restated. Never synthesise a missing slice's analysis as if its dispatch succeeded.

**Step 5: Verify outputs**

Gist tripwires — the floor items that catch most failures:

- Every slice finished clean — native: the subagent returned its confirmation (path written, seven sections); CLI: the process exited 0. Anything else is a slice failure, not a warning.
- Exactly `N` files at the expected `NN_analysis_<slug>.md` paths under `<path>/analysis/`.
- All seven schema sections present in each file; no empty sections without a gap-note + Open Question.
- At least one cited source per file sample-checked (`Read` for local paths, well-formedness for URLs).

**STOP. Read `references/checklist.md` in full before declaring outputs verified.** That file is the seven-section output validation checklist (runtime, inputs, scout, dispatch, files, schema, summary). Every item must pass; failing items trigger a re-dispatch of the offending slice. The bullets above are tripwires, not the contract.

If a section is empty, a file is missing, a cited path is fake, or the schema is incomplete, re-dispatch the offending slice on the same route with the schema embedded and a request to fill the gap. The parent never authors the missing analysis content — the dispatched agent owns the write.

**Step 6: Synthesize `summary.md`**

1. Read every `<path>/analysis/NN_analysis_<slug>.md` in full.
2. Author `<path>/analysis/summary.md` with these sections:
   - **Research Question** — the operator's `--prompt`, verbatim.
   - **Slice Map** — table mapping each `NN – slug` to its slice question and one-line finding.
   - **Convergences** — patterns or risks that appear in two or more analyses, with cross-citations to the slice files.
   - **Divergences** — places where slices disagree or where one slice surfaces a finding the others miss.
   - **Risks & Open Questions** — consolidated, deduplicated list pulled from each analysis's Open Questions and Risks/Mismatches sections.
   - **Recommended Next Steps** — short, actionable list. Each step cites the slice file(s) that support it.
   - **Index** — bullet list of `<path>/analysis/NN_analysis_<slug>.md` paths so a future reader can drill in.
3. `summary.md` is parent-authored. Do not dispatch a slice for this step.

## When Not To Use

- **Single-file lookups** ("where is X defined?", "what does function Y return?"): use `Explore` or direct `Grep`/`Read`. This skill is overkill.
- **Edits to existing code**: the explorer is scoped-write — it can only create new analysis files, not modify anything else.
- **Tightly scoped competitor / reference-repo research** in projects that already ship a more specialized variant (for example a project-local skill that mirrors a fixed competitor catalog). Use that variant when it exists; use this skill as the generic fallback.

## Error Handling

Input, routing, and scout failures are handled inline where they occur — each item in Steps 1–3 names its own recovery. Contract violations, fabricated evidence, schema-incomplete analyses, and retries route through the Required Reading Router: **STOP, re-read `references/dispatch-rules.md` in full**, then re-dispatch the offending slice — the dispatched agent owns the write. Two round-level rules live only here:

- **Requested harness CLI missing from `PATH`:** abort the round with a one-line install message. Never silently reroute to a different harness or model than the operator requested.
- **Network/disk error during dispatch:** fail the round entirely — a half-set of analyses is unacceptable. Re-dispatch after the error is resolved.
