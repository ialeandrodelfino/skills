# Dispatch Rules

The `explorer` launched by this skill runs as a **native subagent of the parent harness by default** (in Claude Code: one `Agent` tool call per slice), and through an official harness CLI (`claude`, `codex`, `cursor-agent`) only when the operator requests an external harness or model. There is no agent registry and nothing to install: the explorer's role travels inside the slice prompt — `assets/explorer-prompt.md` embedded verbatim at the top, followed by the slice specifics, this file, and the seven-section schema. Every dispatched run operates under a strict **scoped-write** contract — exactly one file-write to the named target path, every other action read-only. The rules below MUST be embedded in every dispatched prompt verbatim.

## Scoped-Write Contract

1. The parent prompt MUST name three things:
   - The slice scope (primary source paths, directories, URLs, or topical bounds).
   - The slug and ordinal (`NN_analysis_<slug>`).
   - The exact target analysis file path (`<path>/analysis/NN_analysis_<slug>.md`).
     If any of the three is missing or ambiguous, the agent returns a clarification request and writes nothing.
2. The agent MAY perform exactly one file-write, and only at the target path the parent named.
3. The agent MUST NOT edit any existing file. MUST NOT write to any other path. MUST NOT create directories outside the named analysis directory.
4. The agent reads only the slice scope the parent named (local paths or URLs). For web-scoped slices, web fetch/search is allowed but must stay aligned with the slice question.
5. The agent MUST NOT run state-mutating shell commands: no `git`, `make`, `bun`, `npm`, `pnpm`, `mv`, `rm`, `cp` of non-trivial trees, `>`, `>>`, or any command that touches the working tree outside `<path>/analysis/`.
6. If the agent encounters a source that requires interpretation by another tool (compiled binary, encrypted blob, paywalled URL), it records a note in the **Open Questions** section and continues.

## Tool Restrictions

- **Allowed:** read-only filesystem inspection (`Read`, `Grep`, `Glob`, `find`, `wc -l`, `head`, `cat`, `ls`, `file`, `rg`), web fetch/search when the slice scope authorizes it, and exactly one file-write at the named target path.
- **Forbidden:** edits to any existing file; writes to any path other than the named target; mutating shell commands (`rm`, `mv`, `>`, `>>`, `git`, `make`, package managers).

## Parent Responsibilities

- The parent agent MUST resolve the dispatch route before composing prompts (SKILL.md **Dispatch Routing**): native subagents unless the operator requested an external harness or model. When the CLI route is chosen, the parent MUST verify the chosen binary is on `PATH`; if missing, abort — never silently reroute to a different harness or model than requested.
- The parent agent MUST ensure `<path>/analysis/` exists before dispatch (the agent will refuse to write into a missing directory rather than creating it).
- **Native route:** the parent MUST issue one subagent call per slice — `prompt` = the composed slice prompt verbatim — in a single parallel batch, forwarding the operator's pinned model when one was given; otherwise the subagent inherits the session's model and reasoning effort.
- **CLI route:** the parent MUST invoke each slice with the exact command shape for the resolved CLI (SKILL.md Step 4: `claude -p …`, `codex exec …`, `cursor-agent -p …`), forwarding `--model` and `--reasoning`. `scripts/dispatch-slices.sh` is the recommended runner.
- The parent agent MUST embed all three names — slice scope, slug+ordinal, target file path — explicitly in the slice prompt, along with `assets/explorer-prompt.md`, this `dispatch-rules.md`, and the seven-section schema from `assets/analysis-template.md`, verbatim.
- The parent agent MUST scout the territory itself first (Step 3 of the SKILL.md) so each slice is non-overlapping and independently answerable.

## Parallelism

- All slice invocations in a research round run in parallel — native route: a single batch of subagent calls via the harness's async/background facility; CLI route: backgrounded processes (`&` + `wait`). Do not stagger.
- Wait for every slice to finish before verification. A partial set is unacceptable.
- The hard cap is 8 concurrent invocations per round. Use fewer when the scout reveals fewer non-overlapping slices.

## Output Validation

Each dispatched run writes a file containing all seven sections from `assets/analysis-template.md` (Overview, Mechanisms/Patterns, Relevant Sources, Transferable Patterns, Risks/Mismatches, Open Questions, Evidence). After dispatch the parent:

1. Confirms every slice finished clean — native: the subagent returned its confirmation message (path written, seven sections); CLI: the process exited with code 0. Anything else is a slice failure that must be re-dispatched.
2. Lists `<path>/analysis/` and confirms one file per dispatched slice at the expected `NN_analysis_<slug>.md` path.
3. Re-reads each file to confirm all seven sections are present.
4. Sample-checks at least one cited source per file — `Read` for local paths, well-formedness check for URLs — to confirm evidence is real, not fabricated.
5. If any section is empty or any cited source is fake, re-dispatches the offending slice with the schema and a request to fill the gap. The parent never authors the missing content — the dispatched agent owns the write.

## Failure Handling

- If a slice invocation fails or returns malformed output, retry once on the same route with a stricter prompt restating the scoped-write contract.
- If the dispatched agent reports the slice scope is empty or unreachable, it returns a clarification request and writes nothing. The parent decides whether to merge that slice into an adjacent slice or drop it.
- If the dispatched agent violates the scoped-write contract (writes outside the named path, edits an existing file, runs `git`/`make`/etc.), treat it as a contract violation: stop, re-read this file, and re-dispatch with the contract restated verbatim in the slice prompt.
- If the operator requested an external harness whose CLI is missing from `PATH`, abort the round with a one-line install message. Do not reroute the request to a different harness or model.
- Do not synthesize a missing slice as if its analysis succeeded.
