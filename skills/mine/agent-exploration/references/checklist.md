# Output Validation Checklist

Run this checklist after every research round, before authoring `summary.md`. Every item must pass; failing items trigger a re-dispatch of the offending slice.

## 1. Runtime

- [ ] The dispatch route was resolved per SKILL.md **Dispatch Routing** and announced (native subagents by default; external CLI only on operator request).
- [ ] CLI route only: the chosen binary (`claude`, `codex`, or `cursor-agent`) is reachable on `PATH`.
- [ ] No silent reroute: every slice ran on the harness and model the operator requested (or the documented native default).

## 2. Inputs

- [ ] `--path` resolved to an absolute path that exists.
- [ ] `--agents` is between 1 and 8 inclusive.
- [ ] `--prompt` is non-empty and quoted in every dispatched slice prompt verbatim.
- [ ] `--model`/`--harness` resolved to a single route (default: native, inheriting the session model).
- [ ] `--reasoning` resolved to `low|medium|high|xhigh` on CLI routes (native subagents inherit the session's effort).
- [ ] `<path>/analysis/` exists before dispatch.

## 3. Scout

- [ ] The parent performed a read-only scout of 8–15 tool calls.
- [ ] Slice count matches `--agents` OR was reduced with operator notice.
- [ ] Slices are non-overlapping and independently answerable.
- [ ] Every slice has a two-digit ordinal and a kebab-case slug.

## 4. Dispatch

- [ ] Every slice was dispatched on the resolved route — native: one subagent call per slice in a single parallel batch; CLI: `scripts/dispatch-slices.sh` or the manual command shapes, with `--model`/`--reasoning` forwarded.
- [ ] Every slice prompt was written to its own file under `<path>/.dispatch/prompts/` (the CLI route consumes them; the native route keeps them for audit and re-dispatch).
- [ ] Every slice prompt embedded `assets/explorer-prompt.md`, `references/dispatch-rules.md`, and the seven-section schema from `assets/analysis-template.md` verbatim.
- [ ] Every slice prompt named slice scope, slug+ordinal, and target path.
- [ ] All slices dispatched in parallel (no staggering).
- [ ] Every slice finished clean — native: the subagent returned its written-path confirmation; CLI: exit 0 (when `dispatch-slices.sh` was used, its final summary line reads `failed=0/N`). Failures triggered slice re-dispatch.

## 5. Files

- [ ] Exactly `N` files exist under `<path>/analysis/` matching the dispatched ordinals/slugs.
- [ ] No file is empty or stub-only.
- [ ] No file was written outside `<path>/analysis/`.

## 6. Schema

- [ ] Every file contains all seven sections (Overview, Mechanisms/Patterns, Relevant Sources, Transferable Patterns, Risks/Mismatches, Open Questions, Evidence).
- [ ] No section is empty without a one-line gap-note and a matching Open Question.
- [ ] At least one cited source per file was sample-checked and confirmed real.

## 7. Summary

- [ ] `summary.md` is parent-authored, not produced by a dispatched agent.
- [ ] `summary.md` cites every slice file by path.
- [ ] Convergences and Divergences sections both have content (or explicit notes that none surfaced).
- [ ] Recommended Next Steps cite the slice file(s) that support them.
