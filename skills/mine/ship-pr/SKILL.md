---
name: ship-pr
description: Ships a finished feature, bug fix, or refactor end-to-end — explores the change's impact on docs/site/README, generates release notes (via pr-release if present, otherwise inline from git log), writes a complete PR description (including QA screenshots and summary when qa-report/qa-execution artifacts exist), commits staged changes following the repo's commitlint config, opens the PR via gh CLI, and optionally launches a CodeRabbit review watch loop. Use when a feature/bug/refactor is implementation-complete and ready to ship. Do not use for draft PRs without finished work, for amending an already-merged PR, for repo-level release publishing (use pr-release directly), or for in-progress development checkpoints.
disable-model-invocation: true
metadata:
  author: Pedro Nauck
  github: https://github.com/pedronauck
  repository: https://github.com/pedronauck/skills
---
# Ship a PR

Finish the requested delivery scope using the repository's conventions. Reuse the implementation's impact analysis, current checks, and QA evidence. Do not turn preparing a PR into a release or automated review campaign unless requested or required by the project.

1. Inspect branch/base, staged and unstaged changes, relevant instructions, PR template, and current verification. Already-committed work is valid input. Keep unrelated changes out of staging.
2. Trace changed public behavior to its affected documentation, examples, config, and release notes. A focused diff can be inspected locally; bounded independent agents help only for distinct large areas.
3. Update the affected artifacts. Follow repository release-note policy; a binary on PATH does not establish repository adoption. Group related changes instead of creating a note for every bullet.
4. Write a PR description around the resulting behavior, material risks, and actual validation. Use the repository template; omit empty optional sections. Include existing QA artifacts only when they explain the change.
5. Before committing, run required scoped gates or reuse valid evidence as project policy allows. Stage owned paths explicitly and inspect the staged diff. Follow commitlint and hook requirements; no invented model attribution, history rewrite, or hook bypass.
6. When commit/push/PR creation is within the user's request, publish the feature branch and create or update its PR with `gh` using a body file. Respect requested draft status. Follow required CI to the current head; triage failures as they appear.
7. Start an external review watcher only when requested or already part of the authorized delivery workflow. Confirm the installed command and configured provider. Automatic remediation, commits, pushes, and unbounded polling are separate scope choices, not tool-detection defaults.

## References

Load the phase that needs detail: `references/explore-impact.md`, `references/release-notes.md`, `references/pr-description.md`, `references/qa-artifacts.md`, `references/commit-conventions.md`, or `references/coderabbit-watch.md`.

The read-only detector is `bash <ship-pr-dir>/scripts/detect-tooling.sh`, resolved relative to this skill. Its PATH results describe availability, not authorization or project configuration. Missing optional integrations do not block the normal PR flow. Sync Skeeper only for configured repositories with affected spec artifacts.
