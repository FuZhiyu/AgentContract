#!/usr/bin/env python3
"""Stateless tests for worktree-manager scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import create_worktree
import diff_worktree
import sync_worktree
import worktree_discovery


@pytest.fixture
def tmp_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)
    return repo


@pytest.fixture
def repo_with_ignored_and_annotations(tmp_git_repo):
    repo = tmp_git_repo
    (repo / ".gitignore").write_text(
        "output/\n"
        ".env\n"
        "data/\n"
        "data/  # worktree:symlink\n"
    )
    (repo / "output").mkdir()
    (repo / "output" / "result.csv").write_text("a,b\n1,2\n")
    (repo / ".env").write_text("SECRET=abc\n")
    (repo / "data").mkdir()
    (repo / "data" / "shared.csv").write_text("x\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add gitignore"], cwd=repo, capture_output=True, check=True)
    return repo


@pytest.fixture
def repo_with_external_symlink(tmp_git_repo):
    repo = tmp_git_repo
    external = repo.parent / "external"
    external.mkdir()
    (external / "shared_data").mkdir()
    (external / "shared_data" / "file.txt").write_text("shared\n")
    (external / "model.bin").write_bytes(b"\x00" * 16)

    (repo / "Data").symlink_to(external / "shared_data")
    (repo / "model.bin").symlink_to(external / "model.bin")
    subprocess.run(["git", "add", "Data", "model.bin"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add tracked external symlinks"], cwd=repo, capture_output=True, check=True)
    return repo


class TestStatelessDiscovery:
    def test_discovers_gitignored_entries(self, repo_with_ignored_and_annotations):
        entries = worktree_discovery.discover_managed_entries(repo_with_ignored_and_annotations)
        by_path = {e["path"]: e for e in entries}
        assert "output" in by_path
        assert by_path["output"]["entry_kind"] == "directory"
        assert ".env" in by_path
        assert by_path[".env"]["entry_kind"] == "file"

    def test_annotation_paths_are_marked_shared_only(self, repo_with_ignored_and_annotations):
        entries = worktree_discovery.discover_managed_entries(repo_with_ignored_and_annotations)
        by_path = {e["path"]: e for e in entries}
        assert "data" in by_path
        assert by_path["data"]["shared_only"] is True

    def test_discovers_tracked_external_symlinks(self, repo_with_external_symlink):
        entries = worktree_discovery.discover_managed_entries(repo_with_external_symlink)
        by_path = {e["path"]: e for e in entries}
        assert "Data" in by_path
        assert by_path["Data"]["entry_kind"] == "directory"
        assert "model.bin" in by_path
        assert by_path["model.bin"]["entry_kind"] == "file"

    def test_source_map_excludes_shared_only_by_default(self, repo_with_ignored_and_annotations):
        source_map = worktree_discovery.build_source_map(repo_with_ignored_and_annotations)
        assert "data" not in source_map
        assert "output" in source_map

    def test_promotes_nested_symlink_ignored_children_to_directory_root(self, tmp_path, monkeypatch):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "artifacts").mkdir()
        external = tmp_path / "external_notes"
        external.mkdir()
        (external / "day1.md").write_text("notes\n")
        (repo / "artifacts" / "Notes").symlink_to(external)

        monkeypatch.setattr(
            worktree_discovery,
            "get_gitignored_paths",
            lambda _: [(Path("artifacts/Notes/day1.md"), False)],
        )

        entries = worktree_discovery.discover_managed_entries(repo)
        by_path = {e["path"]: e for e in entries}
        assert "artifacts/Notes" in by_path
        assert by_path["artifacts/Notes"]["entry_kind"] == "directory"
        assert "artifacts/Notes/day1.md" not in by_path


class TestDiffBehavior:
    def test_diff_file_symlink_in_worktree_is_unchanged(self, tmp_path):
        source = tmp_path / "source.bin"
        source.write_bytes(b"\x00" * 8)
        wt_link = tmp_path / "wt.bin"
        wt_link.symlink_to(source)
        change = diff_worktree.diff_file(wt_link, source, "", "cache/model.bin")
        assert change is None

    def test_diff_file_source_symlink_real_worktree_is_modified(self, tmp_path):
        source_target = tmp_path / "target.bin"
        source_target.write_bytes(b"\x01" * 8)
        source_link = tmp_path / "source_link.bin"
        source_link.symlink_to(source_target)
        wt_file = tmp_path / "wt.bin"
        wt_file.write_bytes(b"\x02" * 16)

        change = diff_worktree.diff_file(wt_file, source_link, "", "cache/model.bin")
        assert change is not None
        assert change.status == "modified"

    def test_hidden_files_are_detected(self, tmp_path):
        wt_dir = tmp_path / "wt"
        share_dir = tmp_path / "share"
        wt_dir.mkdir()
        share_dir.mkdir()
        (wt_dir / ".env").write_text("A=1\n")
        (wt_dir / "visible.txt").write_text("v\n")

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        rels = {c.relative_path for c in changes}
        assert ".env" in rels
        assert "visible.txt" in rels

    def test_source_symlink_replaced_in_worktree_is_detected(self, tmp_path):
        share_dir = tmp_path / "share"
        wt_dir = tmp_path / "wt"
        share_dir.mkdir()
        wt_dir.mkdir()
        target = tmp_path / "target.txt"
        target.write_text("shared\n")
        (share_dir / "ctrl.txt").symlink_to(target)
        (wt_dir / "ctrl.txt").write_text("local override\n")

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        assert len(changes) == 1
        assert changes[0].status == "modified"
        assert changes[0].relative_path == "ctrl.txt"

    def test_union_discovery_includes_worktree_only_ignored_root(self, tmp_path, monkeypatch):
        main = tmp_path / "main"
        wt = tmp_path / "wt"
        main.mkdir()
        wt.mkdir()

        # Root known in main discovery.
        (main / "output").mkdir()
        # Root only present in target worktree.
        (wt / "newroot").mkdir()
        (wt / "newroot" / "fresh.txt").write_text("fresh\n")

        monkeypatch.setattr(
            diff_worktree,
            "get_gitignored_paths",
            lambda _: [(Path("newroot"), True)],
        )

        entries = diff_worktree.discover_union_entries(main, wt)
        by_path = {e["path"]: e for e in entries}
        assert "newroot" in by_path
        assert by_path["newroot"]["entry_kind"] == "directory"
        assert by_path["newroot"]["source"] == str(main / "newroot")

    def test_new_file_change_contains_target_path(self, tmp_path):
        wt_dir = tmp_path / "wt"
        share_dir = tmp_path / "share"
        wt_dir.mkdir()
        share_dir.mkdir()
        (wt_dir / "new.txt").write_text("hello\n")

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        assert len(changes) == 1
        assert changes[0].status == "new"
        assert changes[0].target_path == str(share_dir / "new.txt")

    def test_union_discovery_promotes_nested_symlink_ignored_children(self, tmp_path, monkeypatch):
        main = tmp_path / "main"
        wt = tmp_path / "wt"
        main.mkdir()
        wt.mkdir()
        (wt / "artifacts").mkdir(parents=True, exist_ok=True)
        external = tmp_path / "ext"
        external.mkdir()
        (external / "x.md").write_text("x\n")
        (wt / "artifacts" / "Notes").symlink_to(external)

        monkeypatch.setattr(
            diff_worktree,
            "get_gitignored_paths",
            lambda _: [(Path("artifacts/Notes/x.md"), False)],
        )

        entries = diff_worktree.discover_union_entries(main, wt)
        by_path = {e["path"]: e for e in entries}
        assert "artifacts/Notes" in by_path
        assert by_path["artifacts/Notes"]["entry_kind"] == "directory"
        assert by_path["artifacts/Notes"]["source"] == str(main / "artifacts" / "Notes")


class TestSyncBehavior:
    def test_process_file_skips_symlink(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("x\n")
        link = tmp_path / "link.txt"
        link.symlink_to(src)
        ok = sync_worktree.process_file(link, tmp_path / "dest.txt", "overwrite", "_suffix", verbose=False)
        assert ok is True

    def test_process_from_json_uses_target_path_for_new_file(self, tmp_path):
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / "output").mkdir()
        new_file = wt / "output" / "new.csv"
        new_file.write_text("x,y\n1,2\n")

        target = tmp_path / "main" / "output" / "new.csv"

        diff_json = {
            "worktree_path": str(wt),
            "changes": [{
                "status": "new",
                "worktree_path": str(new_file),
                "share_path": None,
                "target_path": str(target),
                "relative_path": "new.csv",
                "directory": "output",
                "size_worktree": 8,
                "size_share": None,
                "mtime_worktree": 0,
                "mtime_share": None,
            }],
        }
        json_path = tmp_path / "changes.json"
        json_path.write_text(json.dumps(diff_json))

        success, failure = sync_worktree.process_from_json(
            json_path, "overwrite", "_suffix", verbose=False
        )
        assert success == 1
        assert failure == 0
        assert target.read_text() == "x,y\n1,2\n"

    def test_process_files_supports_exact_key_entries(self, tmp_path, monkeypatch):
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / "cache").mkdir()
        wt_file = wt / "cache" / "model.bin"
        wt_file.write_bytes(b"\x01" * 8)

        share = tmp_path / "share"
        share.mkdir()
        share_file = share / "model.bin"
        share_file.write_bytes(b"\x00" * 8)

        monkeypatch.setattr(sync_worktree, "build_source_map", lambda _: {"cache/model.bin": share_file})
        success, failure = sync_worktree.process_files(
            wt, ["cache/model.bin"], "overwrite", "_suffix", verbose=False
        )
        assert success == 1
        assert failure == 0
        assert share_file.read_bytes() == b"\x01" * 8

    def test_process_from_json_prefers_target_path(self, tmp_path, monkeypatch):
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / "output").mkdir()
        new_file = wt / "output" / "new.csv"
        new_file.write_text("x,y\n1,2\n")

        target = tmp_path / "main" / "output" / "new.csv"

        def _raise_if_called(_):
            raise AssertionError("build_source_map should not be called when target_path is present")

        monkeypatch.setattr(sync_worktree, "build_source_map", _raise_if_called)

        diff_json = {
            "worktree_path": str(wt),
            "changes": [{
                "status": "new",
                "worktree_path": str(new_file),
                "share_path": None,
                "target_path": str(target),
                "relative_path": "new.csv",
                "directory": "output",
                "size_worktree": 8,
                "size_share": None,
                "mtime_worktree": 0,
                "mtime_share": None,
            }],
        }
        json_path = tmp_path / "changes.json"
        json_path.write_text(json.dumps(diff_json))

        success, failure = sync_worktree.process_from_json(
            json_path, "overwrite", "_suffix", verbose=False
        )
        assert success == 1
        assert failure == 0
        assert target.read_text() == "x,y\n1,2\n"

    def test_process_from_json_requires_target_path(self, tmp_path):
        wt = tmp_path / "wt"
        wt.mkdir()
        file_path = wt / "a.txt"
        file_path.write_text("x\n")

        diff_json = {
            "worktree_path": str(wt),
            "changes": [{
                "status": "new",
                "worktree_path": str(file_path),
                "share_path": None,
                "relative_path": "a.txt",
                "directory": "output",
                "size_worktree": 2,
                "size_share": None,
                "mtime_worktree": 0,
                "mtime_share": None,
            }],
        }
        json_path = tmp_path / "changes.json"
        json_path.write_text(json.dumps(diff_json))

        with pytest.raises(ValueError, match="target_path"):
            sync_worktree.process_from_json(json_path, "overwrite", "_suffix", verbose=False)


class TestEndToEndNoManifest:
    def test_create_diff_sync_without_manifest_file(self, repo_with_ignored_and_annotations, tmp_path):
        repo = repo_with_ignored_and_annotations
        wt = tmp_path / "worktree"
        subprocess.run(
            ["git", "worktree", "add", str(wt), "-b", "stateless-e2e"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        try:
            # Create step: clone ignored content; manifest should not exist.
            create_worktree.clone_gitignored(repo, wt)
            create_worktree.clone_symlink_targets(repo, wt)
            assert not (wt / ".worktree-manifest.json").exists()

            # Modify a cloned file in worktree.
            (wt / "output" / "result.csv").write_text("a,b\n1,2\n3,4\n")

            main = worktree_discovery.get_main_worktree(wt)
            entries = worktree_discovery.discover_managed_entries(main)
            output_entry = next(e for e in entries if e["path"] == "output")
            changes = diff_worktree.diff_directory(
                wt / "output",
                Path(output_entry["source"]),
                "output",
            )
            modified = [c for c in changes if c.status == "modified"]
            assert len(modified) == 1

            diff_json = {
                "worktree_path": str(wt),
                "changes": [diff_worktree.asdict(modified[0])],
            }
            json_path = wt / "changes.json"
            json_path.write_text(json.dumps(diff_json))

            success, failure = sync_worktree.process_from_json(
                json_path, "overwrite", "_suffix", verbose=False
            )
            assert success == 1
            assert failure == 0
            assert (repo / "output" / "result.csv").read_text() == "a,b\n1,2\n3,4\n"
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, capture_output=True)

    def test_cli_diff_sync_round_trip_for_worktree_only_ignored_root(self, tmp_git_repo, tmp_path):
        repo = tmp_git_repo
        (repo / ".gitignore").write_text("output/\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "add ignore"], cwd=repo, capture_output=True, check=True)

        wt = tmp_path / "worktree-cli-e2e"
        subprocess.run(
            ["git", "worktree", "add", str(wt), "-b", "stateless-cli-e2e"],
            cwd=repo,
            capture_output=True,
            check=True,
        )

        try:
            # Ignore this root only in the target worktree via local (uncommitted)
            # .gitignore changes in this worktree checkout.
            with open(wt / ".gitignore", "a", encoding="utf-8") as f:
                f.write("notes_local/\n")

            worktree_only_file = wt / "notes_local" / "draft.md"
            worktree_only_file.parent.mkdir(parents=True, exist_ok=True)
            worktree_only_file.write_text("worktree note\n")

            diff_cmd = [
                "python3",
                str(SCRIPTS_DIR / "diff_worktree.py"),
                str(wt),
                "--json",
            ]
            diff_proc = subprocess.run(diff_cmd, cwd=repo, capture_output=True, text=True, check=True)
            diff_data = json.loads(diff_proc.stdout)

            matching = [
                c for c in diff_data["changes"]
                if c["directory"] == "notes_local" and c["relative_path"] == "draft.md"
            ]
            assert len(matching) == 1
            change = matching[0]
            assert change["status"] == "new"
            assert change["target_path"] == str(repo / "notes_local" / "draft.md")

            json_path = wt / "changes_cli_e2e.json"
            json_path.write_text(json.dumps(diff_data))

            sync_cmd = [
                "python3",
                str(SCRIPTS_DIR / "sync_worktree.py"),
                "--from-json",
                str(json_path),
                "--action",
                "overwrite",
            ]
            subprocess.run(sync_cmd, cwd=repo, capture_output=True, text=True, check=True)

            assert (repo / "notes_local" / "draft.md").read_text() == "worktree note\n"
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, capture_output=True)
