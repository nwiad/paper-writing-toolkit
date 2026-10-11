#!/usr/bin/env python3
"""Save, verify and restore local writing snapshots (Python 3.9+, macOS/Linux)."""

import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    "snapshots", "restored", ".git", ".scratch", "__pycache__", ".venv",
    "venv", "node_modules", ".codex", ".agents", ".cache", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".DS_Store",
}


def local_path(value, field):
    """Configuration paths are relative to the writing project, never external."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty project-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or "\\" in value:
        raise ValueError(f"{field} must stay inside the project: {value}")
    if any(part in EXCLUDED for part in path.parts):
        raise ValueError(f"{field} points into an excluded directory: {value}")
    return path.as_posix()


def within(path, directory):
    return path == directory or path.startswith(directory + "/")


@contextmanager
def source_file(root, relative):
    """Open a regular file through directory descriptors without following links."""
    parts = PurePosixPath(relative).parts
    if not parts or ".." in parts or PurePosixPath(relative).is_absolute():
        raise ValueError(f"Invalid relative path: {relative}")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"Only regular files can be archived: {relative}")
            yield stream, before
    finally:
        os.close(directory)


def fingerprint(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_record(root, relative, destination=None):
    h = hashlib.sha256()
    size = 0
    with source_file(root, relative) as (stream, before):
        output = destination.open("xb") if destination else None
        try:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
                size += len(chunk)
                if output:
                    output.write(chunk)
            if fingerprint(before) != fingerprint(os.fstat(stream.fileno())):
                raise ValueError(f"File changed while being read: {relative}")
        finally:
            if output:
                output.close()
        if destination:
            destination.chmod(stat.S_IMODE(before.st_mode) & 0o777)
    return {"sha256": h.hexdigest(), "bytes": size}


def settings():
    with source_file(ROOT, "project.json") as (stream, _):
        config = json.load(stream)
    paths = config.get("output_paths") or {}
    manuscript = config.get("manuscript") or {}
    if not isinstance(paths, dict) or not isinstance(manuscript, dict):
        raise ValueError("output_paths and manuscript must be JSON objects")
    build = local_path(paths.get("build") or "build", "output_paths.build")
    protected = ["scripts", "instructions", "prompts", "evidence", "inputs", "delivery", "project.json",
                 "README.md", "AGENTS.md", "blueprint.md"]
    for key in ("paper", "review"):
        protected.append(local_path(paths.get(key) or key, f"output_paths.{key}"))
    for key in ("entrypoint", "template_path"):
        if manuscript.get(key) is not None:
            protected.append(local_path(manuscript[key], f"manuscript.{key}"))
    for path in protected:
        if within(path, build) or within(build, path):
            raise ValueError(f"Build directory overlaps source/materials path: {path}")
    expected = manuscript.get("expected_output")
    if expected is not None:
        expected = local_path(expected, "manuscript.expected_output")
        if expected == build or (ROOT / expected).is_dir():
            raise ValueError("manuscript.expected_output must name one file, not a directory")
    return build, expected


def inventory(root, selection=None):
    records = {}
    build, expected = selection if selection else (None, None)
    def fail(error):
        raise error

    for base, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        parent = Path(base)
        retained = []
        for name in sorted(dirs):
            relative = (parent / name).relative_to(root).as_posix()
            if selection and name in EXCLUDED:
                continue
            if selection and within(relative, build):
                if expected is None or not within(expected, relative):
                    continue
            if (parent / name).is_symlink():
                raise ValueError(f"Refusing symlink: {parent / name}")
            retained.append(name)
        dirs[:] = retained
        for name in sorted(files):
            relative = (parent / name).relative_to(root).as_posix()
            if selection:
                if name in EXCLUDED or name.endswith((".pyc", ".pyo")):
                    continue
                if within(relative, build) and relative != expected:
                    continue
            records[relative] = read_record(root, relative)
    return dict(sorted(records.items()))


def snapshot_path(path):
    if path.is_symlink():
        raise ValueError("Snapshot directory must not be a symlink")
    return path.resolve(strict=True)


def verify(snapshot):
    snapshot = snapshot_path(snapshot)
    with source_file(snapshot, "snapshot.json") as (stream, _):
        manifest = json.load(stream)
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported snapshot manifest")
    if not manifest["files"]:
        raise ValueError("Empty snapshot manifest")
    project = snapshot / "project"
    if not project.is_dir() or project.is_symlink():
        raise ValueError("Snapshot project folder is missing or is a symlink")
    if inventory(project) != manifest["files"]:
        raise ValueError("Snapshot file list or SHA-256 verification failed")
    return manifest


def copy_records(source, destination, records):
    destination.mkdir()
    for relative, record in records.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if read_record(source, relative, target) != record:
            raise ValueError(f"File changed during capture: {relative}")


def publish_directory(staged, destination):
    # mkdir is exclusive, including for existing empty directories or symlinks.
    destination.mkdir()
    try:
        for child in staged.iterdir():
            child.rename(destination / child.name)
    except BaseException:
        shutil.rmtree(destination)
        raise


def save(label, note):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", label):
        raise ValueError("Label must use 1–80 letters, digits, underscores or hyphens")
    selection = settings()
    snapshots = ROOT / "snapshots"
    if snapshots.is_symlink():
        raise ValueError("Snapshot folder must not be a symlink")
    snapshots.mkdir(exist_ok=True)
    now = datetime.now().astimezone()
    target = snapshots / f"{now:%Y%m%d-%H%M%S-%f}_{label}"
    before = inventory(ROOT, selection)
    temporary = Path(tempfile.mkdtemp(prefix=".pending-", dir=snapshots))
    try:
        copy_records(ROOT, temporary / "project", before)
        if inventory(temporary / "project") != before or inventory(ROOT, selection) != before:
            raise ValueError("Files changed during capture; retry after all editing has stopped")
        expected = selection[1]
        artifact = before.get(expected)
        manifest = {
            "schema_version": 1,
            "created_at": now.isoformat(),
            "label": label,
            "note": note,
            "original_project_root": str(ROOT),
            "file_count": len(before),
            "total_bytes": sum(record["bytes"] for record in before.values()),
            "expected_output": expected,
            "artifact": {"path": f"project/{expected}", **artifact} if artifact else None,
            "scope": "Local writing materials, plus the configured existing output; excludes build caches, external paths and nested snapshots.",
            "build_status": "No build was run; an existing output is not proof that it matches current sources.",
            "files": before,
        }
        (temporary / "snapshot.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        verify(temporary)
        publish_directory(temporary, target)
    finally:
        shutil.rmtree(temporary)
    print(f"Saved and verified {len(before)} files: {target}")
    print(f"Output: {target / 'project' / expected}" if artifact
          else "No configured output file found; saved source/materials only.")


def restore(snapshot, destination):
    snapshot = snapshot_path(snapshot)
    manifest = verify(snapshot)
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Restore destination must not exist: {destination}")
    if destination.resolve().is_relative_to(snapshot):
        raise ValueError("Restore destination must be outside the snapshot")
    if not destination.parent.is_dir():
        raise ValueError("Restore destination's parent directory must already exist")
    temporary = Path(tempfile.mkdtemp(prefix=".paper-restore-", dir=destination.parent))
    try:
        project = temporary / "project"
        copy_records(snapshot / "project", project, manifest["files"])
        if inventory(project) != manifest["files"] or verify(snapshot) != manifest:
            raise ValueError("Snapshot changed during restore")
        publish_directory(project, destination)
    finally:
        shutil.rmtree(temporary)
    print(f"Restored and verified {len(manifest['files'])} files: {destination}")
    print("Original project unchanged. Review any recorded external paths before continuing.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    saving = commands.add_parser("save", help="Create a new timestamped snapshot")
    saving.add_argument("--label", default="manual")
    saving.add_argument("--note", default="")
    checking = commands.add_parser("verify", help="Verify every archived file")
    checking.add_argument("snapshot", type=Path)
    restoring = commands.add_parser("restore", help="Restore into a NEW directory")
    restoring.add_argument("snapshot", type=Path)
    restoring.add_argument("--to", type=Path, required=True)
    args = parser.parse_args()
    try:
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise ValueError("This script requires macOS/Linux with Python 3.9 or later")
        if args.command == "save":
            save(args.label, args.note)
        elif args.command == "verify":
            manifest = verify(args.snapshot)
            print(f"Verified {len(manifest['files'])} files: {args.snapshot.resolve()}")
        else:
            restore(args.snapshot, args.to)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, f"Snapshot error: {exc}\n")


if __name__ == "__main__":
    main()
