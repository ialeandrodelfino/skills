#!/usr/bin/env python3
"""Update published skill copies through an isolated, pinned native skills CLI."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BUCKETS = ("curated", "community", "marketing", "deprecated")
STATUSES = ("verified", "local", "unresolved", "retired")


class SyncError(Exception):
    pass


def read_json(path: Path, default=None):
    if not path.exists() and default is not None:
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise SyncError(f"Cannot read {path}: {exc}") from exc


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def safe_path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if not parts or relative.startswith("/") or ".." in parts or "\\" in relative:
        raise SyncError(f"Unsafe path: {relative}")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise SyncError(f"Symlinks are not supported: {path}")
    return path


def tree_hash(path: Path) -> str:
    if not path.is_dir() or path.is_symlink():
        raise SyncError(f"Missing directory or symlink: {path}")
    digest = hashlib.sha256()
    for directory, dirs, files in os.walk(path, followlinks=False):
        base = Path(directory)
        for name in dirs + files:
            if (base / name).is_symlink():
                raise SyncError(f"Symlinks are not supported: {base / name}")
        dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__", "__pypackages__"})
        for name in sorted(files):
            if name == ".DS_Store":
                continue
            file = base / name
            mode = file.stat().st_mode
            if not stat.S_ISREG(mode):
                raise SyncError(f"Not a regular file: {file}")
            content = file.read_bytes()
            digest.update(file.relative_to(path).as_posix().encode() + b"\0")
            digest.update(str(mode & 0o111).encode() + b"\0")
            digest.update(str(len(content)).encode() + b"\0" + content)
    return digest.hexdigest()


def skill_name(path: Path) -> str:
    text = path.read_text()
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    name = re.search(r"^name:\s*(.*?)\s*$", match[1], re.M) if match else None
    if not name:
        raise SyncError(f"Missing frontmatter name: {path}")
    value = name[1]
    if value.startswith('"'):
        try:
            return json.loads(value)
        except ValueError as exc:
            raise SyncError(f"Invalid quoted skill name: {path}") from exc
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value.split(" #", 1)[0].strip()


def preserve_name(path: Path, local_name: str):
    text = path.read_text()
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not frontmatter:
        raise SyncError(f"Missing frontmatter: {path}")
    changed = re.sub(r"^name:.*$", lambda _: "name: " + json.dumps(local_name), frontmatter[1], count=1, flags=re.M)
    path.write_text(text[:frontmatter.start(1)] + changed + text[frontmatter.end(1):])


def load_manifest(root: Path):
    manifest = read_json(safe_path(root, "upstream/sources.json"))
    if manifest.get("version") != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("cliVersion", "")):
        raise SyncError("Expected sources.json version 1 and a pinned cliVersion")
    seen = set()
    for entry in manifest.get("skills", []):
        path = entry.get("path", "")
        parts = PurePosixPath(path).parts
        if path != PurePosixPath(path).as_posix() or len(parts) != 3 or parts[0] != "skills" or parts[1] not in BUCKETS or path in seen:
            raise SyncError(f"Invalid or duplicate manifest destination: {path}")
        safe_path(root, path)
        seen.add(path)
        if entry.get("status") not in STATUSES:
            raise SyncError(f"Invalid status: {path}")
        if entry["status"] == "verified":
            if not re.fullmatch(r"[\w.-]+/[\w.-]+", entry.get("source", "")):
                raise SyncError(f"Expected GitHub owner/repo for {path}")
            upstream = entry.get("upstreamPath")
            if not isinstance(upstream, str) or upstream.startswith("/") or ".." in PurePosixPath(upstream).parts or "\\" in upstream:
                raise SyncError(f"Invalid upstreamPath for {path}")
            if not isinstance(entry.get("upstreamName"), str) or not entry["upstreamName"]:
                raise SyncError(f"Missing upstreamName for {path}")
        replacements = entry.get("replacements", [])
        if not isinstance(replacements, list):
            raise SyncError(f"Expected replacements list: {path}")
        for replacement in replacements:
            if (not isinstance(replacement, dict) or not isinstance(replacement.get("file"), str)
                    or not isinstance(replacement.get("old"), str) or not replacement["old"]
                    or not isinstance(replacement.get("new"), str) or not replacement["new"]):
                raise SyncError(f"Invalid replacement: {path}")
            safe_path(root / path, replacement["file"])
    for entry in manifest["skills"]:
        parents = entry.get("requiredBy", [])
        if not isinstance(parents, list) or any(not isinstance(parent, str) or parent not in seen for parent in parents):
            raise SyncError(f"Invalid requiredBy dependency: {entry['path']}")
    return manifest


def select_entries(manifest, names, buckets):
    entries = manifest["skills"]
    for name in names:
        matches = [e for e in entries if name in (e["path"], Path(e["path"]).name)]
        if not matches:
            raise SyncError(f"Unknown skill: {name}")
        if len(matches) > 1 and "/" not in name:
            raise SyncError(f"Ambiguous skill {name}; use its full skills/bucket/name path")
    selected = [e for e in entries if (not names or any(n in (e["path"], Path(e["path"]).name) for n in names))
                and (not buckets or Path(e["path"]).parts[1] in buckets)]
    if not selected:
        raise SyncError("No skills match the selection")
    included = {entry["path"] for entry in selected}
    while True:
        dependencies = {entry["path"] for entry in entries if included.intersection(entry.get("requiredBy", []))}
        if dependencies <= included:
            break
        included.update(dependencies)
    return [entry for entry in entries if entry["path"] in included]


def stage_skill(entry, version: str, staging: Path):
    staging.mkdir(parents=True)
    source = entry["source"] + ("/" + entry["upstreamPath"].strip("/") if entry["upstreamPath"] not in ("", ".") else "")
    command = ["npx", "--yes", f"skills@{version}", "add", source, "--skill", entry["upstreamName"], "--agent", "codex", "--copy", "--yes"]
    try:
        result = subprocess.run(command, cwd=staging, env={**os.environ, "DISABLE_TELEMETRY": "1"},
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError(f"Native install failed for {entry['path']}: {exc}") from exc
    (staging / "install.log").write_text(result.stdout)
    if result.returncode:
        raise SyncError(f"Native install failed for {entry['path']}; see {staging / 'install.log'}")
    lock = read_json(staging / "skills-lock.json")
    record = lock.get("skills", {}).get(entry["upstreamName"])
    expected_path = "/".join(p for p in (("" if entry["upstreamPath"] in ("", ".") else entry["upstreamPath"].strip("/")) , "SKILL.md") if p)
    if (lock.get("version") != 1 or not isinstance(record, dict) or record.get("source") != entry["source"]
            or record.get("sourceType") != "github" or record.get("skillPath") != expected_path
            or not re.fullmatch(r"[0-9a-f]{64}", record.get("computedHash", ""))):
        raise SyncError(f"Native lock does not match selected source/path/name: {entry['path']}")
    installed_root = safe_path(staging, ".agents/skills")
    installed = list(installed_root.iterdir()) if installed_root.is_dir() else []
    if len(installed) != 1:
        raise SyncError(f"Expected exactly one native installed skill: {entry['path']}")
    skill = installed[0]
    tree_hash(skill)
    if skill_name(skill / "SKILL.md") != entry["upstreamName"]:
        raise SyncError(f"Installed skill name mismatch: {entry['path']}")
    local_name = entry.get("localName", Path(entry["path"]).name)
    if local_name != entry["upstreamName"]:
        preserve_name(skill / "SKILL.md", local_name)
    for replacement in entry.get("replacements", []):
        file = safe_path(skill, replacement["file"])
        content = file.read_text()
        if replacement["old"] in content:
            file.write_text(content.replace(replacement["old"], replacement["new"]))
        elif replacement["new"] not in content:
            raise SyncError(f"Replacement no longer matches upstream: {entry['path']}/{replacement['file']}")
    return skill, record


def read_locks(root):
    native = read_json(safe_path(root, "upstream/skills-lock.json"), {"version": 1, "skills": {}})
    catalog = read_json(safe_path(root, "upstream/catalog-lock.json"), {"version": 1, "skills": {}})
    for lock in (native, catalog):
        if lock.get("version") != 1 or not isinstance(lock.get("skills"), dict):
            raise SyncError("Expected native and catalog lock version 1")
    return native, catalog


def local_state(root, entry, catalog):
    path = safe_path(root, entry["path"])
    current = tree_hash(path) if path.exists() else None
    baseline = catalog["skills"].get(entry["path"])
    state = "unmanaged" if baseline is None else "clean" if current is not None and baseline.get("treeHash") == current else "local-modified"
    return state, current


def publish(root, prepared, native, catalog, run, originals, lock_bytes):
    backup = run / "backup"
    backup.mkdir()
    for entry, staged, record, digest in prepared:
        destination = safe_path(root, entry["path"])
        current = tree_hash(destination) if destination.exists() else None
        if current != originals[entry["path"]]:
            raise SyncError(f"Skill changed during staging: {entry['path']}")
        if current is not None:
            shutil.copytree(destination, backup / entry["path"])
    for name, before in lock_bytes.items():
        path = root / "upstream" / name
        if (path.read_bytes() if path.exists() else None) != before:
            raise SyncError(f"Lock changed during staging: {name}")
        if before is not None:
            (backup / name).write_bytes(before)
    # Backups remain available after success or failure for review/recovery.
    touched = []
    try:
        for entry, staged, record, digest in prepared:
            destination = safe_path(root, entry["path"])
            touched.append(entry["path"])
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(staged, destination)
        write_json(root / "upstream/skills-lock.json", native)
        write_json(root / "upstream/catalog-lock.json", catalog)
    except BaseException:
        for relative in touched:
            destination = safe_path(root, relative)
            if destination.exists():
                shutil.rmtree(destination)
            if originals[relative] is not None:
                shutil.copytree(backup / relative, destination)
        for name, before in lock_bytes.items():
            path = root / "upstream" / name
            if before is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(before)
        raise
    print(f"Backup: {backup}")


def run_command(root: Path, args):
    manifest = load_manifest(root)
    selected = select_entries(manifest, args.skill, args.bucket)
    native, catalog = read_locks(root)
    originals = {}
    actionable = False
    for entry in selected:
        state, current = local_state(root, entry, catalog)
        originals[entry["path"]] = current
        if args.command == "status" or entry["status"] != "verified":
            print(f"{entry['status']:10} {state:14} {entry['path']}")
        if entry["status"] == "verified" and args.command == "update":
            if state == "local-modified":
                raise SyncError(f"Local modifications in {entry['path']}; reconcile them before updating")
            if state == "unmanaged" and not args.bootstrap:
                raise SyncError(f"Unmanaged skill {entry['path']}; initial adoption requires --bootstrap")
        if (entry["status"] == "verified" and state != "clean") or entry["status"] == "unresolved":
            actionable = True
    if args.command == "status":
        # Coverage is checked against the whole manifest even with a filtered view.
        known = {e["path"] for e in manifest["skills"]}
        unlisted = 0
        for bucket in BUCKETS:
            for path in (root / "skills" / bucket).glob("*/SKILL.md"):
                relative = path.parent.relative_to(root).as_posix()
                if relative not in known:
                    print(f"unlisted                  {relative}")
                    unlisted += 1
        counts = Counter(e["status"] for e in manifest["skills"])
        summary = ", ".join(f"{counts[status]} {status}" for status in STATUSES)
        print(f"Manifest: {len(known)} skills ({summary}). Selected: {len(selected)}. Unlisted: {unlisted}.")
        return 0
    verified = [e for e in selected if e["status"] == "verified"]
    if not verified:
        print("No verified upstreams in selection; nothing installed.")
        return int(actionable) if args.command == "check" else 0
    work = safe_path(root, ".tmp/upstream-skills")
    work.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=args.command + "-", dir=work))
    lock_bytes = {name: (root / "upstream" / name).read_bytes() if (root / "upstream" / name).exists() else None
                  for name in ("skills-lock.json", "catalog-lock.json")}
    prepared = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for index, entry in enumerate(verified):
            print(f"Fetching {entry['path']} from {entry['source']} …", flush=True)
            futures.append(executor.submit(stage_skill, entry, manifest["cliVersion"], run / "stage" / str(index)))
        # All installations finish before any published directory is touched.
        staged_results = [future.result() for future in futures]
    for entry, (staged, record) in zip(verified, staged_results):
        digest = tree_hash(staged)
        state, current = local_state(root, entry, catalog)
        label = "current" if digest == current else "outdated"
        print(f"{label:10} {state:14} {entry['path']}")
        actionable = actionable or label == "outdated" or state != "clean"
        if args.command == "check":
            continue
        key = entry["upstreamName"]
        previous = native["skills"].get(key)
        if previous and (previous.get("source"), previous.get("skillPath")) != (record["source"], record["skillPath"]):
            raise SyncError(f"Native lock name collision: {key}")
        native["skills"][key] = record
        catalog["skills"][entry["path"]] = {
            "treeHash": digest, "source": entry["source"], "upstreamPath": entry["upstreamPath"],
            "upstreamName": key, "localName": entry.get("localName", Path(entry["path"]).name),
            "computedHash": record["computedHash"],
        }
        prepared.append((entry, staged, record, digest))
    if args.command == "check":
        return int(actionable)
    publish(root, prepared, native, catalog, run, originals, lock_bytes)
    print(f"Updated {len(prepared)} skill(s).")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "check", "update"))
    parser.add_argument("--skill", action="append", default=[], help="Skill folder name or full skills/bucket/name; repeatable")
    parser.add_argument("--bucket", action="append", choices=BUCKETS, default=[])
    parser.add_argument("--bootstrap", action="store_true", help="Adopt previously unmanaged copies, preserving backups")
    args = parser.parse_args(argv)
    if args.bootstrap and args.command != "update":
        parser.error("--bootstrap is only valid with update")
    lock_fd = None
    mutex = ROOT / ".tmp/upstream-skills/update.lock"
    try:
        if args.command == "update":
            mutex = safe_path(ROOT, ".tmp/upstream-skills/update.lock")
            mutex.parent.mkdir(parents=True, exist_ok=True)
            try:
                lock_fd = os.open(mutex, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                raise SyncError(f"Another update owns {mutex}; inspect it before removing a stale lock") from exc
            os.write(lock_fd, f"{os.getpid()}\n".encode())
        return run_command(ROOT, args)
    except (SyncError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            mutex.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
