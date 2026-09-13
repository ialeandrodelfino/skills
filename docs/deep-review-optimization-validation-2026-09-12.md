# Deep-review optimization validation

Implemented the changes accepted from the [performance audit](deep-review-performance-audit-2026-09-12.md). That audit records the earlier installation and historical runs; the measurements below describe this implementation.

## Delivered behavior

| Audited cost | Implemented change |
| --- | --- |
| Handwritten bootstrap scripts, partitions and report scaffolding | `prepare_review.py` creates the manifest, staged decision templates, compiled context, deterministic plan and job contracts. The report renderer generates the walkthrough after review. |
| Repository-wide instruction scans, alias duplication and premature reference expansion | Discovery follows selected-path ancestors, preserves canonical aliases/scopes/precedence, normalizes shared path sets, catalogues router metadata and expands references after parent applicability decisions. Missing applicable references and stale evidence fail explicitly. |
| Rewriting full source paths, ranges and metadata in reviewer output | Stable hunk/rule IDs and a provided draft template feed the compact submission compiler. Scripts expand canonical metadata; the reviewer must still supply every outcome, rule assessment and finding's evidence. |
| Workers repeatedly validating every other pending job | Local `--job LABEL --submit` validates only the assigned contract. The orchestrator owns the global coverage/evidence gate. Invalid status rows contain a targeted repair prompt. |
| Restarting reviews to repair formatting or after provider timeouts | Repairs use the existing artifact and complete diagnostics. Valid outputs survive invalid submissions. External attempts keep unique logs and backups; valid output written before timeout/nonzero exit is accepted without another provider call. |
| Repeated broad context and overlapping sweeps | Workers receive only their rendered prompt and per-job contract, with relevant rules and linter evidence. Rules bind explicit lanes/lenses; extra sweeps require a concrete cross-cohort hypothesis. Spec conformance still generates its own sweep. |

Both lanes default to **200 files / 15,000 changed lines** per cohort, with no total file or line cap on the PR. All four batch limits are configurable with positive integers, including values above the defaults. Oversized hunks are partitioned without losing or duplicating lines. `--max-context-lines` is optional and changes grouping, not selection. Native dispatch preserves the user's selected model and effort.

The global gate pins the checkout, source applicability evidence, external specification bytes and compiled job inputs. Preparation can rebuild derived artifacts after a corrected decision without mistaking its own partial compilation for source drift. Sweeps and jobs without hunks require an explicit completed assessment with an investigation note; untouched templates cannot pass.

## Comparative discovery measurement

Three real CLI runs per version used the same current Compozy repository and a copy of the historical `acp-runtime-catalog` manifest selecting 337 files. The baseline was the installed version before synchronization. No model or paid provider was invoked. Raw samples, source hashes and manifest hash are in [the benchmark data](deep-review-optimization-benchmark-2026-09-12.json).

| Metric | Installed before | Optimized |
| --- | ---: | ---: |
| Helper elapsed time, median | 4.4381 s | 0.1897 s |
| Helper elapsed time, three samples | 7.2571 / 4.4381 / 4.3889 s | 0.1883 / 0.1897 / 0.1923 s |
| `knowledge.json` bytes | 7,185,274 | 194,717 |
| `rules.template.json` bytes | 173,634 | 44,505 |
| Initial pending source decisions | 433 | 105 |
| Initial references expanded | 335 | 0 |
| Compact `knowledge.md` queue | Not generated | 35,788 bytes |

The helper was **23.4 times faster by median**, and its knowledge registry was **97.3% smaller**. Initial decisions fell 75.8%; additional references remain accountable and appear when their parent skills are applied. The baseline selected 95 routers through word matching; the new metadata catalog exposes 99 for semantic triage, so it does not silently exclude routers to achieve these numbers.

These are discovery/runtime and artifact-size measurements, **not a measurement of total review latency, model token consumption, cost, or finding quality**. A matched Luna Max review has not been run. The historical audit's multi-hour figures must not be compared directly to these helper timings.

## Validation

`python3 -B -m unittest discover -s tests/deep_review -v` passed **20/20 tests in 10.836 seconds** after the production fixes. All cases remain in the existing `tests/deep_review/test_pipeline.py` suite.

The real CLI integration creates and commits a temporary Git repository, runs its `make lint`, discovers and classifies instructions/skills/references, prepares jobs, submits compact drafts, runs the global gate, merges findings, renders Markdown/HTML, resumes unchanged work and archives completed/interrupted rounds on explicit refresh. It also proves recovery after invalid linter decisions and supports an explicit YAML contract in a spec directory without Markdown.

Other suite cases cover ownership in both lanes, oversized/sliced hunks, mode-only and empty-file changes, scoped symlink aliases, shared reference decisions, missing/stale source evidence, rule/lens binding, invalid compact assessments, certificate grammar, preserved valid outputs, isolated local validation, external spec drift and retry behavior. External provider tests use a subprocess fixture at the provider I/O boundary; no live provider behavior or review quality is claimed from that fixture.

Python syntax parsing, production helper file-size limits, bundled Markdown links, skill metadata validation and `git diff --check` passed. The independent integration review found four defects; all were fixed and exercised in the existing suite: empty sweep acceptance, zero-hunk ownership, failed-prepare resume and non-Markdown spec selection.

## Installation

Synchronized `skills/mine/deep-review` into `/Users/pedronauck/Dev/compozy/compozy/.agents/skills/deep-review`: 16 changed/added files, with exact byte parity across all 23 skill files, excluding Python cache files. The prior installation was backed up before copying. Paths and per-file hashes are in [the synchronization record](deep-review-optimization-sync-2026-09-12.json).

The existing real CLI integration was rerun with its script directory targeting the installed copy: **1/1 passed in 1.819 seconds**. Installed `prepare_review.py --help` also executed successfully. Unrelated work was preserved; no commit, push or publication was performed.

## Configurable batch limits follow-up

The user clarified that batching thresholds must be configurable for large PRs. Both the preparation and direct job-building CLI now expose:

| Lane | Files per batch | Changed lines per batch |
| --- | --- | --- |
| Defect | `--max-cohort-files N` | `--max-cohort-lines N` |
| Polish | `--max-polish-files N` | `--max-polish-lines N` |

Preparation persists these choices and the optional context budget across decision stages, resume and refresh. An explicit flag overrides only that setting. Direct job building inherits the plan's limits. Every selected file and hunk remains assigned regardless of total PR size.

The existing partition and CLI integration tests now cover smaller custom limits, larger limits of 500 files / 50,000 lines for defects and 700 / 60,000 for polish, complete ownership, direct CLI inheritance, staged persistence and individual overrides. The expanded suite passed 20/20; the installed CLI integration passed 1/1 in 3.007 seconds. Source and installed files were synchronized again; the synchronization record contains the updated hashes.
