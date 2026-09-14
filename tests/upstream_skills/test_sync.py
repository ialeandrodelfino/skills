"""Tooling contract: safe, source-tracked publication of native skill installs."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/upstream-skills.py"
spec = importlib.util.spec_from_file_location("upstream_skills", SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class UpstreamSyncTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.entry = {
            "path": "skills/curated/local-alias", "localName": "local-alias", "status": "verified",
            "source": "example/skills", "upstreamPath": "skills/original", "upstreamName": "original:skill",
        }
        self.other = {"path": "skills/community/unrelated", "status": "local", "source": None}
        self.write("skills/curated/local-alias/SKILL.md", "---\nname: local-alias\n---\nOld content\n")
        self.write("skills/curated/local-alias/stale.txt", "removed upstream")
        self.write("skills/community/unrelated/SKILL.md", "---\nname: unrelated\n---\nUser work\n")
        self.write("skills/mine/private/SKILL.md", "Mine")
        self.write(".agents/skills/sentinel", "Active installation")
        self.write("skills-lock.json", '{"root": "untouched"}\n')
        sync.write_json(self.root / "upstream/sources.json", {
            "version": 1, "cliVersion": "1.5.26", "skills": [self.entry, self.other],
        })
        self.upstream_content = "New content"
        self.native_record = {"source": "example/skills", "sourceType": "github",
                              "skillPath": "skills/original/SKILL.md", "computedHash": "a" * 64}

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def args(self, command="update", bootstrap=True):
        return argparse.Namespace(command=command, skill=["local-alias"], bucket=[], bootstrap=bootstrap)

    def native_install(self, command, *, cwd, **kwargs):
        self.assertEqual(command, ["npx", "--yes", "skills@1.5.26", "add", "example/skills/skills/original",
                                  "--skill", "original:skill", "--agent", "codex", "--copy", "--yes"])
        self.assertEqual(kwargs["env"]["DISABLE_TELEMETRY"], "1")
        installed = cwd / ".agents/skills/original-skill"
        installed.mkdir(parents=True)
        (installed / "SKILL.md").write_text("---\nname: original:skill\ndescription: A useful skill.\n---\n" + self.upstream_content + "\n")
        (installed / "support.txt").write_text("New upstream support")
        sync.write_json(cwd / "skills-lock.json", {"version": 1, "skills": {"original:skill": self.native_record}})
        return subprocess.CompletedProcess(command, 0, "Installed")

    def adopt(self):
        with patch.object(sync.subprocess, "run", side_effect=self.native_install):
            self.assertEqual(sync.run_command(self.root, self.args()), 0)

    def test_alias_install_locks_backups_and_unrelated_state(self):
        unrelated = {"source": "another/repo", "computedHash": "d" * 64}
        sync.write_json(self.root / "upstream/skills-lock.json", {"version": 1, "skills": {"unrelated": unrelated}})
        sync.write_json(self.root / "upstream/catalog-lock.json", {"version": 1, "skills": {self.other["path"]: {"treeHash": "baseline"}}})
        self.adopt()
        installed = self.root / self.entry["path"]
        self.assertEqual(sync.skill_name(installed / "SKILL.md"), "local-alias")
        self.assertFalse((installed / "stale.txt").exists())
        self.assertEqual((installed / "support.txt").read_text(), "New upstream support")
        native, catalog = sync.read_locks(self.root)
        self.assertEqual(native["skills"]["original:skill"], self.native_record)
        self.assertEqual(native["skills"]["unrelated"], unrelated)
        self.assertEqual(catalog["skills"][self.other["path"]], {"treeHash": "baseline"})
        self.assertEqual(catalog["skills"][self.entry["path"]]["treeHash"], sync.tree_hash(installed))
        self.assertEqual((self.root / "skills-lock.json").read_text(), '{"root": "untouched"}\n')
        self.assertEqual((self.root / ".agents/skills/sentinel").read_text(), "Active installation")
        self.assertEqual((self.root / "skills/mine/private/SKILL.md").read_text(), "Mine")
        self.assertIn("User work", (self.root / self.other["path"] / "SKILL.md").read_text())
        backups = list((self.root / ".tmp/upstream-skills").glob("update-*/backup/skills/curated/local-alias/stale.txt"))
        self.assertEqual(len(backups), 1)

    def test_local_changes_refused_even_with_bootstrap(self):
        self.adopt()
        self.write(self.entry["path"] + "/support.txt", "User customization")
        with patch.object(sync.subprocess, "run") as native:
            with self.assertRaisesRegex(sync.SyncError, "Local modifications"):
                sync.run_command(self.root, self.args())
            native.assert_not_called()
        self.assertEqual((self.root / self.entry["path"] / "support.txt").read_text(), "User customization")

    def test_initial_adoption_is_explicit(self):
        with patch.object(sync.subprocess, "run") as native:
            with self.assertRaisesRegex(sync.SyncError, "--bootstrap"):
                sync.run_command(self.root, self.args(bootstrap=False))
            native.assert_not_called()

    def test_check_stages_without_publishing_and_reports_changes(self):
        before = sync.tree_hash(self.root / self.entry["path"])
        with patch.object(sync.subprocess, "run", side_effect=self.native_install):
            self.assertEqual(sync.run_command(self.root, self.args(command="check", bootstrap=False)), 1)
        self.assertEqual(before, sync.tree_hash(self.root / self.entry["path"]))
        self.assertFalse((self.root / "upstream/skills-lock.json").exists())
        self.adopt()
        with patch.object(sync.subprocess, "run", side_effect=self.native_install):
            self.assertEqual(sync.run_command(self.root, self.args(command="check", bootstrap=False)), 0)

    def test_silent_install_skip_or_wrong_source_never_publishes(self):
        before = sync.tree_hash(self.root / self.entry["path"])
        with patch.object(sync.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "Skipped")):
            with self.assertRaises(sync.SyncError):
                sync.run_command(self.root, self.args())
        self.native_record["source"] = "different/repository"
        with patch.object(sync.subprocess, "run", side_effect=self.native_install):
            with self.assertRaisesRegex(sync.SyncError, "Native lock"):
                sync.run_command(self.root, self.args())
        self.assertEqual(before, sync.tree_hash(self.root / self.entry["path"]))

    def test_failed_lock_publication_restores_content_and_both_locks(self):
        self.adopt()
        before_tree = sync.tree_hash(self.root / self.entry["path"])
        before_locks = {name: (self.root / "upstream" / name).read_bytes()
                        for name in ("skills-lock.json", "catalog-lock.json")}
        self.native_record["computedHash"] = "b" * 64
        self.upstream_content = "Changed after adoption"
        real_replace = sync.os.replace

        def fail_catalog(source, destination):
            if destination == self.root / "upstream/catalog-lock.json":
                raise OSError("Disk write failure")
            return real_replace(source, destination)

        with patch.object(sync.subprocess, "run", side_effect=self.native_install), patch.object(sync.os, "replace", side_effect=fail_catalog):
            with self.assertRaisesRegex(OSError, "Disk write failure"):
                sync.run_command(self.root, self.args(bootstrap=False))
        self.assertEqual(before_tree, sync.tree_hash(self.root / self.entry["path"]))
        for name, content in before_locks.items():
            self.assertEqual((self.root / "upstream" / name).read_bytes(), content)

    def test_edits_during_fetch_are_preserved_and_never_reported_clean(self):
        self.adopt()
        edited = self.root / self.entry["path"] / "support.txt"

        def install_and_edit(command, **kwargs):
            result = self.native_install(command, **kwargs)
            edited.write_text("User edit during fetch")
            return result

        with patch.object(sync.subprocess, "run", side_effect=install_and_edit):
            self.assertEqual(sync.run_command(self.root, self.args(command="check", bootstrap=False)), 1)
        self.assertEqual(edited.read_text(), "User edit during fetch")
        # Return the fixture to its adopted baseline before the second scenario.
        edited.write_text("New upstream support")
        before_locks = {name: (self.root / "upstream" / name).read_bytes()
                        for name in ("skills-lock.json", "catalog-lock.json")}
        with patch.object(sync.subprocess, "run", side_effect=install_and_edit):
            with self.assertRaisesRegex(sync.SyncError, "Skill changed during staging"):
                sync.run_command(self.root, self.args(bootstrap=False))
        self.assertEqual(edited.read_text(), "User edit during fetch")
        for name, content in before_locks.items():
            self.assertEqual((self.root / "upstream" / name).read_bytes(), content)

    def test_one_failed_install_leaves_every_selected_skill_untouched(self):
        second = {**self.entry, "path": self.other["path"], "upstreamName": "second"}
        sync.write_json(self.root / "upstream/sources.json", {
            "version": 1, "cliVersion": "1.5.26", "skills": [self.entry, second],
        })
        before = {e["path"]: sync.tree_hash(self.root / e["path"]) for e in (self.entry, second)}

        def install(command, **kwargs):
            if command[command.index("--skill") + 1] == "second":
                return subprocess.CompletedProcess(command, 1, "Remote unavailable")
            return self.native_install(command, **kwargs)

        args = self.args()
        args.skill = []
        with patch.object(sync.subprocess, "run", side_effect=install):
            with self.assertRaisesRegex(sync.SyncError, "Native install failed"):
                sync.run_command(self.root, args)
        for relative, digest in before.items():
            self.assertEqual(sync.tree_hash(self.root / relative), digest)
        self.assertFalse((self.root / "upstream/skills-lock.json").exists())

    def test_source_change_collision_preserves_installed_content_and_lock(self):
        old_record = {**self.native_record, "source": "previous/owner"}
        native_path = self.root / "upstream/skills-lock.json"
        sync.write_json(native_path, {"version": 1, "skills": {"original:skill": old_record}})
        before_lock = native_path.read_bytes()
        before_tree = sync.tree_hash(self.root / self.entry["path"])
        with patch.object(sync.subprocess, "run", side_effect=self.native_install):
            with self.assertRaisesRegex(sync.SyncError, "Native lock name collision"):
                sync.run_command(self.root, self.args())
        self.assertEqual(native_path.read_bytes(), before_lock)
        self.assertEqual(sync.tree_hash(self.root / self.entry["path"]), before_tree)
        self.assertFalse((self.root / "upstream/catalog-lock.json").exists())

    def test_new_destination_bootstraps_alias_but_managed_deletion_is_protected(self):
        destination = self.root / self.entry["path"]
        shutil.rmtree(destination)
        self.adopt()
        self.assertEqual(sync.skill_name(destination / "SKILL.md"), "local-alias")
        shutil.rmtree(destination)
        with patch.object(sync.subprocess, "run") as native:
            with self.assertRaisesRegex(sync.SyncError, "Local modifications"):
                sync.run_command(self.root, self.args())
            native.assert_not_called()
        self.assertFalse(destination.exists())

    def test_failed_new_install_removes_created_directory_and_locks(self):
        destination = self.root / self.entry["path"]
        shutil.rmtree(destination)
        real_replace = sync.os.replace

        def fail_catalog(source, target):
            if target == self.root / "upstream/catalog-lock.json":
                raise OSError("Disk write failure")
            return real_replace(source, target)

        with patch.object(sync.subprocess, "run", side_effect=self.native_install), patch.object(sync.os, "replace", side_effect=fail_catalog):
            with self.assertRaisesRegex(OSError, "Disk write failure"):
                sync.run_command(self.root, self.args())
        self.assertFalse(destination.exists())
        self.assertFalse((self.root / "upstream/skills-lock.json").exists())
        self.assertFalse((self.root / "upstream/catalog-lock.json").exists())

    def test_concurrent_creation_of_new_destination_is_preserved(self):
        destination = self.root / self.entry["path"]
        shutil.rmtree(destination)

        def install_and_create(command, **kwargs):
            result = self.native_install(command, **kwargs)
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("Created by user during fetch")
            return result

        with patch.object(sync.subprocess, "run", side_effect=install_and_create):
            with self.assertRaisesRegex(sync.SyncError, "Skill changed during staging"):
                sync.run_command(self.root, self.args())
        self.assertEqual((destination / "SKILL.md").read_text(), "Created by user during fetch")

    def test_replacements_are_reproducible_and_fail_on_upstream_drift(self):
        self.entry["replacements"] = [{"file": "SKILL.md", "old": "references/eval-guide.md", "new": "eval-guide.md"}]
        sync.write_json(self.root / "upstream/sources.json", {
            "version": 1, "cliVersion": "1.5.26", "skills": [self.entry, self.other],
        })
        self.upstream_content = "Read references/eval-guide.md"
        self.adopt()
        installed = self.root / self.entry["path"] / "SKILL.md"
        self.assertIn("Read eval-guide.md", installed.read_text())
        native, catalog = sync.read_locks(self.root)
        self.assertEqual(native["skills"]["original:skill"], self.native_record)
        self.assertEqual(catalog["skills"][self.entry["path"]]["treeHash"], sync.tree_hash(installed.parent))
        self.upstream_content = "Read eval-guide.md"
        with patch.object(sync.subprocess, "run", side_effect=self.native_install):
            self.assertEqual(sync.run_command(self.root, self.args(command="check", bootstrap=False)), 0)
        self.upstream_content = "Upstream replaced this whole section"
        before = installed.read_bytes()
        with patch.object(sync.subprocess, "run", side_effect=self.native_install):
            with self.assertRaisesRegex(sync.SyncError, "Replacement no longer matches"):
                sync.run_command(self.root, self.args(bootstrap=False))
        self.assertEqual(installed.read_bytes(), before)
        self.entry["replacements"][0]["file"] = "../outside.md"
        sync.write_json(self.root / "upstream/sources.json", {
            "version": 1, "cliVersion": "1.5.26", "skills": [self.entry],
        })
        with self.assertRaisesRegex(sync.SyncError, "Unsafe path"):
            sync.load_manifest(self.root)

    def test_parent_selection_includes_transitive_dependencies_only(self):
        child = {**self.other, "requiredBy": [self.entry["path"]]}
        grandchild = {"path": "skills/curated/guide", "requiredBy": [child["path"]]}
        unrelated = {"path": "skills/marketing/independent"}
        manifest = {"skills": [self.entry, child, grandchild, unrelated]}
        selected = sync.select_entries(manifest, ["local-alias"], [])
        self.assertEqual([entry["path"] for entry in selected], [self.entry["path"], child["path"], grandchild["path"]])
        selected_child = sync.select_entries(manifest, [child["path"]], [])
        self.assertEqual([entry["path"] for entry in selected_child], [child["path"], grandchild["path"]])

    def test_symlink_and_mine_destinations_are_rejected(self):
        (self.root / self.entry["path"] / "outside").symlink_to(self.root / "skills/mine/private")
        with self.assertRaisesRegex(sync.SyncError, "Symlinks"):
            sync.run_command(self.root, self.args())
        manifest = {"version": 1, "cliVersion": "1.5.26", "skills": [{**self.entry, "path": "skills/mine/private"}]}
        sync.write_json(self.root / "upstream/sources.json", manifest)
        with self.assertRaisesRegex(sync.SyncError, "Invalid or duplicate"):
            sync.load_manifest(self.root)


if __name__ == "__main__":
    unittest.main()
