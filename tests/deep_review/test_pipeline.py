from __future__ import annotations

import json
import os
import copy
import hashlib
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from collections import Counter
from unittest.mock import patch


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "mine" / "deep-review"
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import _common  # noqa: E402
import build_manifest  # noqa: E402
import build_knowledge  # noqa: E402
import build_jobs  # noqa: E402


class DeepReviewPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.out = self.repo / ".deep-review" / "test"
        self.out.mkdir(parents=True)
        self._write("AGENTS.md", "# Rules\nUse $python-quality for Python changes.\nKeep public names explicit.\n")
        self._write("src/app.py", "def run():\n    return 1\n")
        self._write("src/nested/CLAUDE.md", "# Nested rules\nHandle errors at this boundary.\n")
        self._write("src/nested/module.py", "def nested():\n    return 2\n")
        self._write(
            ".agents/skills/python-quality/SKILL.md",
            "---\nname: python-quality\ndescription: Review Python code quality.\n---\n"
            "Read `references/rules.md` in full.\n",
        )
        self._write(
            ".agents/skills/python-quality/references/rules.md",
            "# Rules\nPrefer explicit exception boundaries.\n",
        )
        self._write(
            ".agents/skills/terraform-only/SKILL.md",
            "---\nname: terraform-only\ndescription: Review Terraform provider resources.\n---\n",
        )
        self._git("add", "AGENTS.md", "src", ".agents")
        self._git("commit", "-m", "initial fixture")
        self.initial_head = self._git("rev-parse", "HEAD")
        self.manifest = {
            "target": "test",
            "mode": "full",
            "round": 1,
            "base": self.initial_head,
            "effective_base": self.initial_head,
            "head": self.initial_head,
            "diff_command": "git diff base..head -- <file>",
            "worktree_snapshot": _common.freeze_snapshot(self.repo, self.out),
            "counts": {"selected": 2, "ignored": 0, "skipped": 0, "carried": 0},
            "files": [
                {
                    "path": "src/app.py", "status": "M", "adds": 1, "dels": 0,
                    "disposition": "selected",
                    "hunks": [{"start": 1, "lines": 1, "side": "new"}],
                },
                {
                    "path": "src/nested/module.py", "status": "M", "adds": 1, "dels": 0,
                    "disposition": "selected",
                    "hunks": [{"start": 1, "lines": 1, "side": "new"}],
                },
            ],
        }
        self._json(self.out / "manifest.json", self.manifest)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, relative: str, content: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
             "-c", "commit.gpgsign=false", *args],
            cwd=self.repo, check=True, text=True, capture_output=True,
        ).stdout.strip()

    def _run(self, script: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        proc = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS_DIR / script), *args],
            cwd=self.repo, env=env, text=True, capture_output=True,
        )
        if check and proc.returncode:
            self.fail(f"{script} failed:\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

    def _discover(self, decisions: dict | None = None) -> tuple[dict, dict]:
        args = []
        if decisions is not None:
            self._json(self.out / "decisions.json", decisions)
            args = ["--decisions", str(self.out / "decisions.json")]
        self._run("build_knowledge.py", "--out", str(self.out), *args)
        return (
            json.loads((self.out / "knowledge.json").read_text()),
            json.loads((self.out / "rules.template.json").read_text()),
        )

    def _prepare_plan(self, complete_sources: bool = True) -> None:
        knowledge, template = self._discover()
        for row in template["sources"]:
            row["status"] = "not-applicable" if "terraform-only" in row["source"] else "applied"
            row["reason"] = "Terraform is absent" if row["status"] == "not-applicable" else "fixture source read and applicable"
        knowledge, template = self._discover(template)
        for row in template["sources"]:
            if row["status"] == "pending":
                row.update(status="applied", reason="fixture reference read and applicable")
        _, template = self._discover(template)
        if not complete_sources:
            template["sources"] = template["sources"][1:]
        template["rules"] = [
            {
                "id": "R01", "scope": ["src/**"], "source": "AGENTS.md",
                "guideline": "Keep public names explicit.",
            },
            {
                "id": "R02", "scope": ["src/nested/**"], "source": "src/nested/CLAUDE.md",
                "guideline": "Handle errors at this boundary.",
            },
            {
                "id": "R03", "scope": ["src/**/*.py"],
                "source": ".agents/skills/python-quality/SKILL.md",
                "guideline": "Review Python code quality.",
            },
        ]
        self._json(self.out / "rules.json", template)
        self._write_out(
            "context-pack.md",
            "# Context Pack — test\n\n## Intent\nFixture.\n\n## Rubric\nApplied.\n\n## Linters\nUnavailable.\n",
        )
        self._json(
            self.out / "plan.json",
            {
                "cohorts": [{
                    "id": "c01", "name": "python", "risk": "normal",
                    "files": ["src/app.py", "src/nested/module.py"],
                }],
                "sweeps": [{"key": "tests", "lens": "Check shared error-boundary contracts.",
                            "hypothesis": "The two entry points may disagree about propagated errors."}],
            },
        )

    def _write_out(self, relative: str, content: str) -> None:
        path = self.out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _empty_output(job: dict) -> dict:
        return {
            **({"_job_digest": job["job_digest"]} if "job_digest" in job else {}),
            **({"assessment": {"status": "complete", "note": "Fixture assignment and cross-file behavior assessed."}}
               if job.get("required_assessment") else {}),
            "defects": [],
            "advisories": [],
            "suppressions": [],
            "coverage": {
                "hunks": [
                    {
                        "file": row["file"], "hunk": row["hunk"],
                        "checks": [job["coverage_check"]], "outcome": "clear",
                    }
                    for row in job["required_hunks"]
                ],
                "rules": [
                    {"rule_id": rule_id, "status": "compliant", "note": "checked"}
                    for rule_id in job["rule_ids"]
                ],
            },
        }

    @staticmethod
    def _draft(job: dict) -> dict:
        return {
            "job_digest": job["job_digest"], "summary": "Reviewed the fixture boundary.",
            **({"assessment": {"status": "complete", "note": "Fixture assignment and cross-file behavior assessed."}}
               if job.get("required_assessment") else {}),
            "defects": [], "advisories": [], "suppressions": [],
            "coverage": {
                "hunks": [[row["id"], "clear"] for row in job["required_hunks"]],
                "rules": [[rule, "compliant", "Fixture rule checked against assigned source."] for rule in job["rule_ids"]],
            },
        }

    def _jobs(self) -> list[dict]:
        return json.loads((self.out / "jobs.json").read_text())["jobs"]

    def test_pr_manifest_excludes_changes_only_on_the_base_branch(self) -> None:
        def git(*args: str) -> str:
            return subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "-c", "commit.gpgsign=false", *args],
                cwd=self.repo, check=True, text=True, capture_output=True,
            ).stdout.strip()

        ancestor = git("rev-parse", "HEAD")
        base_branch = git("branch", "--show-current")
        git("switch", "-c", "pr-feature")
        self._write("src/app.py", "def run():\n    return 3\n")
        git("commit", "-am", "feature")
        head = git("rev-parse", "HEAD")
        git("switch", base_branch)
        self._write("src/nested/module.py", "def nested():\n    return 4\n")
        self._write("src/base_only.py", "BASE_ONLY = True\n")
        git("add", "src/nested/module.py", "src/base_only.py")
        git("commit", "-m", "advance base")
        base_tip = git("rev-parse", "HEAD")
        git("switch", "pr-feature")
        metadata = {"baseRefOid": base_tip, "headRefOid": head,
                    "title": "Feature", "url": "https://github.com/example/repo/pull/1"}
        real_run = build_manifest.run

        def run_with_github_metadata(cmd, cwd, check=True):
            if cmd[:3] == ["gh", "auth", "status"]:
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if cmd[:3] == ["gh", "pr", "view"]:
                return subprocess.CompletedProcess(cmd, 0, json.dumps(metadata), "")
            return real_run(cmd, cwd, check=check)

        with patch.object(build_manifest, "run", side_effect=run_with_github_metadata):
            base, resolved_head, pr = build_manifest.resolve_pr(self.repo, 1)
            entries = build_manifest.diff_name_status(
                self.repo, build_manifest.diff_spec(base, resolved_head, False, False),
            )

        self.assertEqual({entry["path"] for entry in entries}, {"src/app.py"})
        self.assertEqual(base, ancestor)
        self.assertEqual(resolved_head, head)
        self.assertEqual(pr["baseRefOid"], base_tip)

    def test_knowledge_discovers_nested_instructions_and_project_skills(self) -> None:
        knowledge, template = self._discover()
        sources = {source["path"]: source for source in knowledge["sources"]}
        self.assertEqual(build_knowledge.source_paths(knowledge, sources["AGENTS.md"]), ["src/app.py", "src/nested/module.py"])
        self.assertEqual(build_knowledge.source_paths(knowledge, sources["src/nested/CLAUDE.md"]), ["src/nested/module.py"])
        self.assertTrue(sources[".agents/skills/python-quality/SKILL.md"]["candidate"])
        self.assertEqual(sources[".agents/skills/python-quality/SKILL.md"]["references"], [])
        self.assertNotIn(".agents/skills/python-quality/references/rules.md", sources)
        statuses = {row["source"]: row["status"] for row in template["sources"]}
        self.assertEqual(statuses["AGENTS.md"], "pending")
        self.assertEqual(statuses[".agents/skills/terraform-only/SKILL.md"], "pending")
        self.assertIn("Terraform provider resources", (self.out / "knowledge.md").read_text())

    def test_build_jobs_rejects_unaccounted_knowledge_source(self) -> None:
        self._prepare_plan(complete_sources=False)
        proc = self._run("build_jobs.py", "--out", str(self.out), check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("source accounting mismatch", proc.stderr)

    def test_reference_routing_preserves_applicable_rules_and_source_accounting(self) -> None:
        skill = ".agents/skills/python-quality/SKILL.md"
        required = ".agents/skills/python-quality/references/rules.md"
        optional = ".agents/skills/python-quality/references/async.md"
        route = "For async cancellation, read `references/async.md`."
        self._write(
            skill,
            "---\nname: python-quality\ndescription: Review Python code quality.\n---\n"
            "For exception handling, read `references/rules.md`.\n" + route + "\n",
        )
        self._write(optional, "# Cancellation\nPreserve task cancellation.\n")
        self._prepare_plan()
        knowledge = json.loads((self.out / "knowledge.json").read_text())
        source = next(row for row in knowledge["sources"] if row["path"] == optional)
        self.assertEqual(source["parent_skill"], skill)
        self.assertEqual(source["routing_hints"], [{"line": 6, "text": route}])

        registry = json.loads((self.out / "rules.json").read_text())
        optional_row = next(row for row in registry["sources"] if row["source"] == optional)
        optional_row.update(status="not-applicable", reason="Router limits this reference to async cancellation; selected paths are synchronous.")
        registry["rules"].append({
            "id": "R04", "scope": ["src/**/*.py"], "source": required,
            "guideline": "Prefer explicit exception boundaries.", "sweeps": ["tests"],
        })
        self._json(self.out / "rules.json", registry)
        self._run("build_jobs.py", "--out", str(self.out))
        jobs = json.loads((self.out / "jobs.json").read_text())["jobs"]
        self.assertTrue(jobs)
        for job in jobs:
            self.assertIn("R04", job["rule_ids"])

        optional_row.update(status="pending", reason="Applicability is unresolved.")
        self._json(self.out / "rules.json", registry)
        proc = self._run("build_jobs.py", "--out", str(self.out), check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(optional, proc.stderr)
        self.assertIn("status must be applied|not-applicable", proc.stderr)

    def test_symlink_sources_deduplicate_identity_and_preserve_lexical_scope(self) -> None:
        shared = self.repo / "shared-rules.md"
        shared.write_text("# Shared\nKeep operation boundaries explicit.\n")
        (self.repo / "src/AGENTS.md").symlink_to(shared)
        (self.repo / "src/nested/AGENTS.md").symlink_to(shared)
        alias = self.repo / ".codex/skills/python-alias"
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.repo / ".agents/skills/python-quality", target_is_directory=True)
        knowledge, _ = self._discover()
        sources = knowledge["sources"]
        shared_rows = [row for row in sources if row["path"] == "shared-rules.md"]
        self.assertEqual(len(shared_rows), 1)
        shared_row = shared_rows[0]
        aliases = {row["path"]: row for row in shared_row["aliases"]}
        self.assertEqual(set(aliases), {"src/AGENTS.md", "src/nested/AGENTS.md"})
        self.assertEqual(knowledge["path_sets"][aliases["src/AGENTS.md"]["path_set"]], ["src/app.py", "src/nested/module.py"])
        self.assertEqual(knowledge["path_sets"][aliases["src/nested/AGENTS.md"]["path_set"]], ["src/nested/module.py"])
        self.assertGreater(aliases["src/nested/AGENTS.md"]["precedence"], aliases["src/AGENTS.md"]["precedence"])
        skills = [row for row in sources if row["kind"] == "skill" and row["name"] == "python-quality"]
        self.assertEqual(len(skills), 1)
        self.assertEqual({row["path"] for row in skills[0]["aliases"]}, {
            ".agents/skills/python-quality/SKILL.md", ".codex/skills/python-alias/SKILL.md",
        })

    def test_shared_reference_stays_pending_until_its_own_decision(self) -> None:
        second = ".agents/skills/second-quality/SKILL.md"
        self._write(second, "---\nname: second-quality\ndescription: Another Python boundary.\n---\nRead `references/rules.md`.\n")
        alias = self.repo / ".agents/skills/second-quality/references/rules.md"
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.repo / ".agents/skills/python-quality/references/rules.md")
        _, decisions = self._discover()
        for row in decisions["sources"]:
            row.update(status="applied", reason="Fixture source applies.")
        knowledge, decisions = self._discover(decisions)
        references = [row for row in knowledge["sources"] if row["kind"] == "skill-reference"]
        self.assertEqual(len(references), 1)
        self.assertEqual(set(references[0]["parent_skills"]), {second, ".agents/skills/python-quality/SKILL.md"})
        reference = next(row for row in decisions["sources"] if row["kind"] == "skill-reference")
        self.assertEqual(reference["status"], "pending")
        for row in decisions["sources"]:
            if row["source"] == second:
                row.update(status="not-applicable", reason="Second boundary is irrelevant.")
        _, decisions = self._discover(decisions)
        self.assertEqual(next(row for row in decisions["sources"] if row["kind"] == "skill-reference")["status"], "pending")
        for row in decisions["sources"]:
            if row["kind"] == "skill":
                row.update(status="not-applicable", reason="All parent boundaries are irrelevant.")
        _, decisions = self._discover(decisions)
        self.assertEqual(next(row for row in decisions["sources"] if row["kind"] == "skill-reference")["status"], "not-applicable")

    def test_source_decisions_require_unchanged_evidence(self) -> None:
        knowledge, decisions = self._discover()
        source = decisions["sources"][0]
        source.update(status="applied", reason="Read current source.")
        for field in ("scope_fingerprint", "source_fingerprints"):
            with self.subTest(missing=field):
                bad = copy.deepcopy(decisions)
                bad.pop(field)
                if field == "source_fingerprints":
                    for row in bad["sources"]:
                        row.pop("fingerprint")
                self._json(self.out / "bad-decisions.json", bad)
                proc = self._run("build_knowledge.py", "--out", str(self.out), "--decisions", str(self.out / "bad-decisions.json"), check=False)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("fingerprint", proc.stderr)
        changed_scope = copy.deepcopy(self.manifest)
        changed_scope["files"][0]["hunks"][0]["lines"] = 2
        self._json(self.out / "manifest.json", changed_scope)
        self._json(self.out / "old-decisions.json", decisions)
        proc = self._run("build_knowledge.py", "--out", str(self.out), "--decisions", str(self.out / "old-decisions.json"), check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("stale scope_fingerprint", proc.stderr)
        self._json(self.out / "manifest.json", self.manifest)
        self._write("AGENTS.md", "# New rules\nUse new boundaries.\n")
        self._json(self.out / "old-decisions.json", decisions)
        proc = self._run("build_knowledge.py", "--out", str(self.out), "--decisions", str(self.out / "old-decisions.json"), check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("stale fingerprint", proc.stderr)
        self.assertEqual(json.loads((self.out / "knowledge.json").read_text()), knowledge)

    def test_missing_applied_reference_cannot_disappear_from_accounting(self) -> None:
        self._prepare_plan()
        registry = json.loads((self.out / "rules.json").read_text())
        reference = ".agents/skills/python-quality/references/rules.md"
        registry["sources"] = [row for row in registry["sources"] if row["source"] != reference]
        self._json(self.out / "rules.json", registry)
        proc = self._run("build_jobs.py", "--out", str(self.out), check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(reference, proc.stderr)
        self._write(".agents/skills/python-quality/SKILL.md", "---\nname: python-quality\ndescription: Python rules.\n---\nRead `references/missing.md`.\n")
        _, decisions = self._discover()
        for row in decisions["sources"]:
            row.update(status="applied", reason="Fixture source applies.")
        self._json(self.out / "decisions.json", decisions)
        proc = self._run("build_knowledge.py", "--out", str(self.out), "--decisions", str(self.out / "decisions.json"), check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing.md", proc.stderr)

    def test_pipeline_keeps_advisory_visible_without_blocking_ship(self) -> None:
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        jobs = json.loads((self.out / "jobs.json").read_text())["jobs"]
        self.assertEqual({job["kind"] for job in jobs}, {"cohort", "polish", "sweep"})
        for job in jobs:
            payload = self._empty_output(job)
            if job["kind"] == "polish":
                anchor = job["required_hunks"][0]
                payload["advisories"].append({
                    "file": anchor["file"], "line": 1, "end_line": None,
                    "in_diff": True, "hunk": anchor["hunk"], "rule_ids": ["R01"],
                    "category": "nitpick", "severity": "trivial", "quick_win": True,
                    "title": "Name the fixture boundary explicitly",
                    "body": "The generic name makes the owning boundary harder to scan.",
                    "also_applies": [], "guideline": "Keep public names explicit.",
                    "suggestion": None,
                    "evidence": [
                        "Premise: src/app.py:1 uses a generic public name → Improvement: readers identify the boundary without opening callers → Fix: rename the function to describe the fixture boundary"
                    ],
                })
                payload["coverage"]["hunks"][0]["outcome"] = "reported"
            self._json(self.repo / job["output"], payload)

        self._run("run_jobs.py", "--out", str(self.out), "--validate-only")
        self._run("merge_findings.py", "--out", str(self.out))
        self._write_out(
            "walkthrough.md",
            "<!-- deep-review:walkthrough -->\n## Walkthrough\nFixture.\n\n## Changes\n\n"
            "| Cohort / File(s) | Summary |\n| --- | --- |\n| Python | Fixture |\n\n"
            "## Estimated code review effort\n\n🎯 1 (Trivial) | ⏱️ ~5 minutes\n\n"
            "## Review details\n\n- **Posture**: assertive\n",
        )
        self._run("render_review.py", "--out", str(self.out))
        self._run("render_html.py", "--out", str(self.out))
        review = (self.out / "review.md").read_text()
        html = (self.out / "review.html").read_text()
        ledger = json.loads((self.out / "findings.json").read_text())
        self.assertIn("**Verdict: SHIP**", review)
        self.assertIn("## Advisories", review)
        self.assertEqual(len(ledger["findings"]), 0)
        self.assertEqual(len(ledger["advisories"]), 1)
        self.assertIn('"result_kind": "advisory"', html)
        self.assertNotIn('"profile":', html)
        self.assertTrue(ledger["coverage"]["summary"]["lanes"]["defect"]["complete"])
        self.assertTrue(ledger["coverage"]["summary"]["lanes"]["polish"]["complete"])

    def test_automatic_plan_preserves_all_hunk_lines_once_in_each_lane(self) -> None:
        selected = {
            f"src/item{i:03d}.py": {"status": "M", "adds": 1, "dels": 0,
                                     "hunks": [{"start": 1, "lines": 1, "side": "new"}]}
            for i in range(201)
        }
        selected["src/oversized.py"] = {
            "status": "M", "adds": 32001, "dels": 2,
            "hunks": [{"start": 7, "lines": 32001, "side": "new"},
                      {"start": 4, "lines": 2, "side": "old"}],
        }
        empty_paths = {"src/mode-only.py", "src/empty.py"}
        selected.update({path: {"status": "M" if "mode-only" in path else "A", "adds": 0, "dels": 0, "hunks": []}
                         for path in empty_paths})
        plan = build_jobs.automatic_plan(selected)
        self.assertEqual(plan["limits"]["cohort_files"], 200)
        self.assertEqual(plan["limits"]["cohort_changed_lines"], 15000)
        self.assertEqual(plan["limits"]["polish_files"], 200)
        self.assertEqual(plan["limits"]["polish_changed_lines"], 15000)
        self.assertEqual(plan["sweeps"], [])
        expected = Counter((path, hunk["side"], line) for path, row in selected.items()
                           for hunk in row["hunks"]
                           for line in range(hunk["start"], hunk["start"] + hunk["lines"]))
        for label, defect_files, defect_lines, polish_files, polish_lines in (
            ("defaults", 200, 15000, 200, 15000),
            ("smaller independent limits", 3, 10001, 2, 7000),
            ("larger than defaults", 500, 50000, 700, 60000),
        ):
            configured = plan if label == "defaults" else build_jobs.automatic_plan(selected, max_files=defect_files, max_lines=defect_lines)
            self.assertEqual(configured["limits"]["cohort_files"], defect_files)
            self.assertEqual(configured["limits"]["cohort_changed_lines"], defect_lines)
            lanes = {
                "defect": (configured["cohorts"], defect_files, defect_lines),
                "polish": (build_jobs.polish_cohorts(configured["cohorts"], selected, polish_files, polish_lines), polish_files, polish_lines),
            }
            for lane, (cohorts, file_limit, line_limit) in lanes.items():
                with self.subTest(configuration=label, lane=lane):
                    actual = Counter()
                    for cohort in cohorts:
                        self.assertLessEqual(len(cohort["files"]), file_limit)
                        scope = cohort["hunk_scope"]
                        self.assertLessEqual(sum(h["lines"] for hunks in scope.values() for h in hunks), line_limit)
                        actual.update((path, hunk["side"], line) for path, hunks in scope.items()
                                      for hunk in hunks
                                      for line in range(hunk["start"], hunk["start"] + hunk["lines"]))
                    self.assertEqual(actual, expected)
                    self.assertEqual(Counter(path for cohort in cohorts for path in cohort["files"] if path in empty_paths),
                                     Counter({path: 1 for path in empty_paths}))
                    if label == "larger than defaults":
                        self.assertEqual(len(cohorts), 1)
            self.assertEqual(build_jobs.validate_cohorts(configured["cohorts"], selected, defect_files, defect_lines), [])

        self.manifest["files"][0].update(copy.deepcopy(selected["src/oversized.py"]))
        self._json(self.out / "manifest.json", self.manifest)
        self._prepare_plan()
        widened = build_jobs.automatic_plan(_common.manifest_selected(self.manifest), max_files=500, max_lines=50000)
        widened["limits"].update(polish_files=700, polish_changed_lines=60000)
        self._json(self.out / "plan.json", widened)
        self._run("build_jobs.py", "--out", str(self.out))
        self.assertEqual(json.loads((self.out / "jobs.json").read_text())["limits"], widened["limits"])
        self.assertEqual(Counter(job["lane"] for job in self._jobs()), {"defect": 1, "polish": 1})

    def test_rule_binding_keeps_each_relevant_lane_and_sweep_obligation(self) -> None:
        self._prepare_plan()
        registry = json.loads((self.out / "rules.json").read_text())
        registry["rules"][0].update(lanes=["polish"])
        registry["rules"][1].update(lanes=["defect"], sweeps=["tests"])
        self._json(self.out / "rules.json", registry)
        plan = json.loads((self.out / "plan.json").read_text())
        plan["cohorts"] = [
            {"id": "app", "name": "app", "risk": "normal", "files": ["src/app.py"]},
            {"id": "nested", "name": "nested", "risk": "normal", "files": ["src/nested/module.py"]},
        ]
        self._json(self.out / "plan.json", plan)
        self._run("build_jobs.py", "--out", str(self.out))
        actual = {job["label"]: set(job["rule_ids"]) for job in self._jobs()}
        self.assertEqual(actual, {
            "cohort-app": {"R03"}, "cohort-nested": {"R02", "R03"},
            "polish-app-p01": {"R01", "R03"}, "polish-nested-p01": {"R01", "R03"},
            "sweep-tests": {"R02"},
        })

    def test_compact_submit_requires_explicit_complete_assessments_and_keeps_valid_output(self) -> None:
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        job = next(row for row in self._jobs() if row["kind"] == "cohort")
        draft = self._draft(job)
        self._json(self.repo / job["draft"], draft)
        self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit")
        canonical = (self.repo / job["output"]).read_bytes()
        compiled = json.loads(canonical)
        self.assertEqual(compiled["_job_digest"], job["job_digest"])
        self.assertEqual(compiled["summary"], draft["summary"])
        self.assertEqual(compiled["coverage"], self._empty_output(job)["coverage"] | {
            "rules": [{"rule_id": rule, "status": "compliant", "note": "Fixture rule checked against assigned source."} for rule in job["rule_ids"]],
        })
        mutations = {
            "missing hunk": lambda p: p["coverage"]["hunks"].pop(),
            "duplicate hunk": lambda p: p["coverage"]["hunks"].append(p["coverage"]["hunks"][0][:]),
            "unknown hunk": lambda p: p["coverage"]["hunks"][0].__setitem__(0, "Hunknown"),
            "missing status": lambda p: p["coverage"]["hunks"][0].__setitem__(1, None),
            "missing rule": lambda p: p["coverage"]["rules"].pop(),
            "duplicate rule": lambda p: p["coverage"]["rules"].append(p["coverage"]["rules"][0][:]),
            "unknown rule": lambda p: p["coverage"]["rules"][0].__setitem__(0, "Runknown"),
            "missing rule status": lambda p: p["coverage"]["rules"][0].__setitem__(1, None),
            "stale digest": lambda p: p.__setitem__("job_digest", "stale"),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                bad = copy.deepcopy(draft)
                mutate(bad)
                self._json(self.repo / job["draft"], bad)
                proc = self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit", check=False)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual((self.repo / job["output"]).read_bytes(), canonical)

                status = json.loads((self.out / "runs" / f"{job['label']}-status.json").read_text())
                self.assertTrue(status["jobs"][0]["errors"])
        bad = copy.deepcopy(draft)
        anchor = job["required_hunks"][0]
        bad["defects"] = [{
            "file": "src/wrong.py", "line": 1, "in_diff": True, "hunk": anchor["id"],
            "rule_ids": [], "category": "potential-issue", "severity": "minor", "quick_win": False,
            "title": "Wrong file anchor", "body": "The anchor must belong to the assigned hunk.",
            "evidence": ["Premise: a fixture input crosses the boundary → Path: run accepts it → Verdict: an invalid result escapes"],
        }]
        self._json(self.repo / job["draft"], bad)
        proc = self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit", check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("does not match hunk ID", proc.stdout)
        self.assertEqual((self.repo / job["output"]).read_bytes(), canonical)

    def test_local_validation_isolated_from_pending_peers_and_global_freeze_barrier(self) -> None:
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        job = self._jobs()[0]
        self._json(self.repo / job["draft"], self._draft(job))
        self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit")
        global_status = self.out / "runs/jobs-status.json"
        self._json(global_status, {"sentinel": "orchestrator owns this report"})
        original = global_status.read_bytes()
        self._write("src/app.py", "def run():\n    return 99\n")
        proc = self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--validate-only")
        self.assertIn("pending=0 of 1", proc.stdout)
        self.assertEqual(global_status.read_bytes(), original)
        proc = self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--validate-only", "--status-file", str(global_status), check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(global_status.read_bytes(), original)
        for peer in self._jobs()[1:]:
            self._json(self.repo / peer["draft"], self._draft(peer))
            self._run("run_jobs.py", "--out", str(self.out), "--job", peer["label"], "--submit")
        proc = self._run("run_jobs.py", "--out", str(self.out), "--validate-only", check=False)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("source drifted", proc.stderr)

    def test_sweep_finding_anchors_do_not_duplicate_local_hunk_coverage(self) -> None:
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        index = next(job for job in self._jobs() if job["kind"] == "sweep")
        job = json.loads((self.repo / index["contract"]).read_text())
        self.assertTrue(job["required_assessment"])
        untouched = json.loads((self.out / "agents" / f"{job['label']}.draft.template.json").read_text())
        self.assertEqual(untouched["assessment"], {"status": None, "note": ""})
        self._json(self.repo / job["draft"], untouched)
        proc = self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit", check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("assessment", proc.stdout)
        self.assertFalse((self.repo / job["output"]).exists())
        anchor = job["anchor_hunks"][0]
        draft = self._draft(job)
        self.assertEqual(draft["coverage"]["hunks"], [])
        draft["defects"] = [{
            "file": anchor["file"], "line": 1, "in_diff": True, "hunk": anchor["id"],
            "rule_ids": [], "category": "potential-issue", "severity": "minor", "quick_win": False,
            "title": "Shared fixture boundary disagrees", "body": "Two consumers expect different outcomes from this boundary.",
            "evidence": ["Premise: both fixture consumers share an error boundary → Path: their expectations differ → Verdict: one consumer receives an invalid result"],
        }]
        self._json(self.repo / job["draft"], draft)
        self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit")
        canonical = (self.repo / job["output"]).read_bytes()
        self.assertEqual(json.loads(canonical)["defects"][0]["hunk"], anchor["hunk"])
        for case in ("unselected anchor", "duplicate local coverage", "missing assessment", "blank assessment note"):
            with self.subTest(case=case):
                bad = copy.deepcopy(draft)
                if case == "unselected anchor":
                    bad["defects"][0]["hunk"] = "Hunselected"
                elif case == "duplicate local coverage":
                    bad["coverage"]["hunks"] = [[anchor["id"], "reported"]]
                elif case == "missing assessment":
                    bad.pop("assessment")
                else:
                    bad["assessment"]["note"] = "   "
                self._json(self.repo / job["draft"], bad)
                proc = self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit", check=False)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual((self.repo / job["output"]).read_bytes(), canonical)

        for path in ("src/app.py", "src/nested/module.py"):
            (self.repo / path).chmod(0o755)
        self.out = self.repo / ".deep-review/mode-only"
        self._run("build_manifest.py", "--out", str(self.out), "--base", self.initial_head, "--worktree")
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertTrue(manifest["files"])
        self.assertTrue(all(not row["hunks"] for row in manifest["files"]))
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        for job in self._jobs():
            with self.subTest(no_hunks=job["label"]):
                self.assertTrue(job["required_assessment"])
                self.assertEqual(job["required_hunks"], [])
                draft = self._draft(job)
                draft["assessment"] = {"status": None, "note": ""}
                self._json(self.repo / job["draft"], draft)
                proc = self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit", check=False)
                self.assertEqual(proc.returncode, 1)
                self.assertIn("assessment", proc.stdout)
                self._json(self.repo / job["draft"], self._draft(job))
                self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit")
        self._run("run_jobs.py", "--out", str(self.out), "--validate-only")

    def test_retry_repairs_existing_result_preserves_diagnostics_and_resumes_uniquely(self) -> None:
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        job = self._jobs()[0]
        valid = self.out / "runner-valid.json"
        self._json(valid, self._draft(job))
        runner = self.out / "fixture-runner.py"
        # This subprocess is the provider I/O boundary, replaying fixture data.
        # It deliberately emits one incomplete result before accepting repair.
        runner.write_text(
            "import json, pathlib, sys\n"
            "prompt, draft, valid, counter = map(pathlib.Path, sys.argv[1:])\n"
            "n = int(counter.read_text()) + 1 if counter.exists() else 1\n"
            "counter.write_text(str(n))\n"
            "payload = json.loads(valid.read_text())\n"
            "if n == 1: payload['coverage']['hunks'].pop()\n"
            "else: counter.with_suffix('.prompt').write_text(prompt.read_text())\n"
            "draft.write_text(json.dumps(payload))\n",
        )
        counter = self.out / "runner-count"
        command = shlex.join([sys.executable, str(runner), "{prompt}", "{draft}", str(valid), str(counter)])
        args = ["--out", str(self.out), "--only", job["label"], "--command", command, "--workers", "1", "--attempts", "2"]
        self._run("run_jobs.py", *args)
        self.assertEqual(counter.read_text(), "2")
        report = json.loads((self.out / "runs/jobs-status.json").read_text())
        attempts = report["jobs"][0]["attempts"]
        self.assertEqual(len(attempts), 2)
        self.assertFalse(attempts[0]["repair"])
        self.assertTrue(attempts[1]["repair"])
        repair = counter.with_suffix(".prompt").read_text()
        self.assertIn("Continue from the existing result", repair)
        for error in attempts[0]["errors"]:
            self.assertIn(error, repair)
        archives = sorted((self.out / "runs").glob("*.before.draft.json"))
        self.assertTrue(archives)
        archived = json.loads(archives[0].read_text())
        self.assertEqual(len(archived["coverage"]["hunks"]), len(job["required_hunks"]) - 1)
        original_logs = {path: path.read_bytes() for path in (self.out / "runs").glob("*.attempt-*.status.json")}
        self._run("run_jobs.py", *args)
        self.assertEqual(counter.read_text(), "2")
        broken = copy.deepcopy(self._draft(job))
        broken["coverage"]["hunks"].pop()
        self._json(self.repo / job["draft"], broken)
        self._json(self.repo / job["output"], broken)
        self._run("run_jobs.py", *args)
        self.assertEqual(counter.read_text(), "3")
        current_logs = set((self.out / "runs").glob("*.attempt-*.status.json"))
        self.assertEqual(len(current_logs), len(original_logs) + 1)
        for path, content in original_logs.items():
            self.assertEqual(path.read_bytes(), content)

    def test_valid_output_after_timeout_or_nonzero_exit_is_not_repeated(self) -> None:
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        runner = self.out / "completed-runner.py"
        runner.write_text(
            "import pathlib, sys, time\n"
            "mode = sys.argv[1]\n"
            "prompt, draft, valid, counter = map(pathlib.Path, sys.argv[2:])\n"
            "counter.write_text(str(int(counter.read_text()) + 1 if counter.exists() else 1))\n"
            "draft.write_bytes(valid.read_bytes())\n"
            "if mode == 'timeout': time.sleep(2)\n"
            "sys.exit(7)\n",
        )
        for mode, job in zip(("timeout", "nonzero"), self._jobs()):
            with self.subTest(mode=mode):
                valid = self.out / f"{mode}.valid.json"
                self._json(valid, self._draft(job))
                counter = self.out / f"{mode}.count"
                command = shlex.join([sys.executable, str(runner), mode, "{prompt}", "{draft}", str(valid), str(counter)])
                self._run("run_jobs.py", "--out", str(self.out), "--only", job["label"], "--command", command,
                          "--workers", "1", "--attempts", "3", "--timeout-min", "0.01")
                self.assertEqual(counter.read_text(), "1")
                status = json.loads((self.out / "runs/jobs-status.json").read_text())["jobs"][0]
                self.assertEqual(status["status"], "pass")
                self.assertEqual(len(status["attempts"]), 1)
                self.assertEqual(status["attempts"][0]["timed_out"], mode == "timeout")
                if mode == "nonzero":
                    self.assertEqual(status["exit_code"], 7)
                _common.validate_job_output(self.repo, self.out, job)

    def test_global_freeze_includes_external_symlink_source_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            source = Path(external) / "SKILL.md"
            source.write_text("---\nname: external-quality\ndescription: Review Python boundaries.\n---\nPreserve exception boundaries.\n")
            alias = self.repo / ".agents/skills/external-quality"
            alias.symlink_to(Path(external), target_is_directory=True)
            self._git("add", ".agents/skills/external-quality")
            self._git("commit", "-m", "install external fixture skill")
            self.manifest.update(head=self._git("rev-parse", "HEAD"), worktree_snapshot=_common.freeze_snapshot(self.repo, self.out))
            self._json(self.out / "manifest.json", self.manifest)
            self._prepare_plan()
            self._run("build_jobs.py", "--out", str(self.out))
            for job in self._jobs():
                self._json(self.repo / job["draft"], self._draft(job))
                self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit")
            self._run("run_jobs.py", "--out", str(self.out), "--validate-only")
            snapshot = _common.freeze_snapshot(self.repo, self.out)
            original_source = source.read_text()
            source.write_text(source.read_text() + "New external source obligation.\n")
            self.assertEqual(_common.freeze_snapshot(self.repo, self.out), snapshot)
            proc = self._run("run_jobs.py", "--out", str(self.out), "--validate-only", check=False)
            self.assertEqual(proc.returncode, 3)
            self.assertIn("stale", proc.stderr)
            self.assertIn(str(source), proc.stderr)
            source.write_text(original_source)
            spec = Path(external) / "spec.md"
            spec.write_text("# Contract\nPreserve fixture return values.\n")
            self._json(self.out / "review-context.json", {
                "intent": "Review fixture.", "linters": [],
                "spec_artifacts": [{"path": str(spec), "role": "external specification",
                                    "sha256": hashlib.sha256(spec.read_bytes()).hexdigest()}],
            })
            self._run("run_jobs.py", "--out", str(self.out), "--validate-only")
            spec.write_text(spec.read_text() + "A changed external specification.\n")
            self.assertEqual(_common.freeze_snapshot(self.repo, self.out), snapshot)
            proc = self._run("run_jobs.py", "--out", str(self.out), "--validate-only", check=False)
            self.assertEqual(proc.returncode, 3)
            self.assertIn(str(spec), proc.stderr)

    def test_prepare_decisions_submit_and_report_use_real_cli_pipeline(self) -> None:
        self._write("src/app.py", "def run():\n    return 3\n")
        self._write("src/nested/module.py", "def nested():\n    return 4\n")
        self._write("Makefile", "lint:\n\tpython3 -c \"import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('src').rglob('*.py')]; print('Python syntax valid')\"\n")
        self._write("contracts/result.yaml", "results:\n  app: 3\n  nested: 4\n")
        self._git("add", "Makefile", "contracts/result.yaml")
        self._git("commit", "-m", "install fixture linter")
        self.initial_head = self._git("rev-parse", "HEAD")
        self._git("commit", "-am", "change fixture results")
        self.out = self.repo / ".deep-review/e2e"
        proc = self._run("prepare_review.py", "--out", str(self.out), "--base", self.initial_head, "--spec", "contracts",
                         "--max-cohort-files", "2", "--max-cohort-lines", "3", "--max-polish-files", "1",
                         "--max-polish-lines", "1", "--max-context-lines", "5", check=False)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertFalse((self.out / "jobs.json").exists())
        decisions = json.loads((self.out / "decisions.template.json").read_text())
        decisions["intent"] = "Update both fixture results while preserving explicit boundaries."
        decisions["spec_artifacts"] = [{"path": "contracts/result.yaml", "role": "explicit result contract"}]
        self.assertEqual(decisions["linters"][0]["status"], "pending")
        lint = subprocess.run(["make", "lint"], cwd=self.repo, check=True, text=True, capture_output=True)
        decisions["linters"][0].update(status="ran", result=lint.stdout.strip())
        for row in decisions["sources"]:
            row.update(status="not-applicable" if "terraform-only" in row["source"] else "applied",
                       reason="Python boundary applies; Terraform is outside this change.")
        decisions["rules"] = [
            {"id": "R01", "source": "AGENTS.md", "scope": ["src/**"], "start_line": 3, "end_line": 3},
            {"id": "R02", "source": "src/nested/CLAUDE.md", "scope": ["src/nested/**"], "start_line": 2, "end_line": 2},
        ]
        self._json(self.out / "decisions.json", decisions)
        proc = self._run("prepare_review.py", "--out", str(self.out), "--decisions", str(self.out / "decisions.json"), check=False)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertFalse((self.out / "jobs.json").exists())
        decisions = json.loads((self.out / "decisions.template.json").read_text())
        references = [row for row in decisions["sources"] if row["kind"] == "skill-reference"]
        self.assertEqual(len(references), 1)
        references[0].update(status="applied", reason="Exception boundary rule applies to both entry points.")
        decisions["rules"].append({"id": "R03", "source": references[0]["id"], "scope": ["src/**"], "start_line": 2, "end_line": 2})
        self._json(self.out / "decisions.json", decisions)
        self._run("prepare_review.py", "--out", str(self.out), "--decisions", str(self.out / "decisions.json"))
        limits = {"cohort_files": 2, "cohort_changed_lines": 3, "polish_files": 1, "polish_changed_lines": 1, "context_lines": 5}
        self.assertEqual(json.loads((self.out / "jobs.json").read_text())["limits"], limits)
        self.assertEqual(Counter(job["lane"] for job in self._jobs()), {"defect": 1, "polish": 2, "sweep": 1})
        self._run("prepare_review.py", "--out", str(self.out), "--decisions", str(self.out / "decisions.json"),
                  "--max-polish-files", "2", "--max-polish-lines", "3")
        limits.update(polish_files=2, polish_changed_lines=3)
        self.assertEqual(json.loads((self.out / "jobs.json").read_text())["limits"], limits)
        self.assertEqual(Counter(job["lane"] for job in self._jobs()), {"defect": 1, "polish": 1, "sweep": 1})
        original_manifest = (self.out / "manifest.json").read_bytes()
        decisions["rules"][0]["id"] = "R01-corrected"
        decisions["linters"][0]["status"] = "invalid"
        self._json(self.out / "decisions.json", decisions)
        proc = self._run("prepare_review.py", "--out", str(self.out), "--decisions", str(self.out / "decisions.json"), check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status must be", proc.stderr)
        decisions["linters"][0]["status"] = "ran"
        self._json(self.out / "decisions.json", decisions)
        self._run("prepare_review.py", "--out", str(self.out), "--decisions", str(self.out / "decisions.json"))
        self.assertEqual((self.out / "manifest.json").read_bytes(), original_manifest)
        self.assertEqual(json.loads((self.out / "jobs.json").read_text())["limits"], limits)
        self.assertTrue(all("R01" not in job["rule_ids"] for job in self._jobs()))
        self.assertTrue(any("R01-corrected" in job["rule_ids"] for job in self._jobs()))
        context = json.loads((self.out / "review-context.json").read_text())
        self.assertEqual(context["linters"][0]["status"], "ran")
        self.assertIn("Python syntax valid", context["linters"][0]["result"])
        self.assertEqual(context["spec_artifacts"][0]["path"], "contracts/result.yaml")
        self.assertEqual(context["spec_artifacts"][0]["sha256"], hashlib.sha256((self.repo / "contracts/result.yaml").read_bytes()).hexdigest())
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["head"], self._git("rev-parse", "HEAD"))
        self.assertEqual({row["path"] for row in manifest["files"] if row["disposition"] == "selected"}, {"src/app.py", "src/nested/module.py"})
        self.assertEqual({job["lane"] for job in self._jobs()}, {"defect", "polish", "sweep"})
        self.assertIn("sweep-spec-parity", {job["label"] for job in self._jobs()})
        for job in self._jobs():
            template = json.loads((self.out / "agents" / f"{job['label']}.draft.template.json").read_text())
            self.assertTrue(all(row[1] is None for row in template["coverage"]["hunks"]))
            self.assertTrue(all(row[1] is None for row in template["coverage"]["rules"]))
            self._json(self.repo / job["draft"], self._draft(job))
            self._run("run_jobs.py", "--out", str(self.out), "--job", job["label"], "--submit")
        self._run("run_jobs.py", "--out", str(self.out), "--validate-only")
        self._run("merge_findings.py", "--out", str(self.out))
        self._run("render_review.py", "--out", str(self.out))
        self._run("render_html.py", "--out", str(self.out))
        review = (self.out / "review.md").read_text()
        self.assertIn("**Verdict: SHIP**", review)
        self.assertIn(decisions["intent"], review)
        self.assertIn("Reviewed the fixture boundary.", review)
        self.assertIn("<html", (self.out / "review.html").read_text().lower())
        outputs = {job["output"]: (self.repo / job["output"]).read_bytes() for job in self._jobs()}
        self._run("prepare_review.py", "--out", str(self.out), "--decisions", str(self.out / "decisions.json"))
        self.assertEqual(json.loads((self.out / "jobs.json").read_text())["limits"], limits)
        for path, content in outputs.items():
            self.assertEqual((self.repo / path).read_bytes(), content)
        self._write("src/app.py", "def run():\n    return 5\n")
        self._git("commit", "-am", "advance fixture after completed review")
        proc = self._run("prepare_review.py", "--out", str(self.out), check=False)
        self.assertEqual(proc.returncode, 3)
        proc = self._run("prepare_review.py", "--out", str(self.out), "--refresh", check=False)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        refreshed = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(refreshed["base"], self.initial_head)
        self.assertEqual(refreshed["head"], self._git("rev-parse", "HEAD"))
        self.assertNotEqual(refreshed["worktree_snapshot"], manifest["worktree_snapshot"])
        self.assertFalse((self.out / "jobs.json").exists())
        archive = self.out / "rounds" / f"round-{manifest['round']}"
        self.assertEqual((archive / "review.md").read_text(), review)
        for path, content in outputs.items():
            self.assertEqual((archive / "agents" / Path(path).name).read_bytes(), content)
        interrupted = json.loads((self.out / "decisions.template.json").read_text())
        interrupted["intent"] = "Applicability decisions still in progress."
        self._json(self.out / "decisions.json", interrupted)
        proc = self._run("prepare_review.py", "--out", str(self.out), "--refresh", check=False)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        interrupted_archive = self.out / "rounds" / f"round-{refreshed['round']}"
        self.assertEqual(json.loads((interrupted_archive / "decisions.json").read_text()), interrupted)
        self.assertFalse((self.out / "decisions.json").exists())

    def test_job_validation_rejects_missing_hunk_coverage(self) -> None:
        self._prepare_plan()
        self._run("build_jobs.py", "--out", str(self.out))
        job = next(
            row for row in json.loads((self.out / "jobs.json").read_text())["jobs"]
            if row["kind"] == "cohort"
        )
        payload = self._empty_output(job)
        payload["coverage"]["hunks"].pop()
        self._json(self.repo / job["output"], payload)
        with self.assertRaisesRegex(ValueError, "ownership mismatch"):
            _common.validate_job_output(self.repo, self.out, job)

    def test_certificates_are_class_specific(self) -> None:
        defect_job = {
            "lane": "defect", "coverage_check": "defect",
            "required_hunks": [], "rule_ids": [],
        }
        payload = self._empty_output(defect_job)
        payload["defects"] = [{
            "file": "src/app.py", "line": 1, "end_line": None, "in_diff": False,
            "hunk": None, "rule_ids": [], "category": "potential-issue",
            "severity": "minor", "quick_win": False, "title": "Reject invalid state",
            "body": "A bad state reaches the caller.", "also_applies": [],
            "guideline": None, "suggestion": None,
            "evidence": ["Premise: src/app.py:1 accepts zero → Path: run receives zero → Verdict: the caller receives an invalid state"],
        }]
        self.assertEqual(_common.findings_contract_errors(payload), [])
        payload["defects"][0]["evidence"][0] = (
            "Premise: src/app.py:1 is generic → Improvement: clearer scan → Fix: rename it"
        )
        self.assertTrue(_common.findings_contract_errors(payload))
        advisory = payload["defects"].pop()
        advisory.update(category="nitpick", severity="trivial", quick_win=True)
        payload["advisories"] = [advisory]
        self.assertEqual(_common.findings_contract_errors(payload), [])
        advisory["evidence"][0] = "Premise: src/app.py:1 accepts zero → Path: run receives zero → Verdict: the caller receives an invalid state"
        self.assertTrue(_common.findings_contract_errors(payload))


if __name__ == "__main__":
    unittest.main()
