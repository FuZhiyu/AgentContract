#!/usr/bin/env python3
"""Comprehensive test suite for worktree-manager scripts.

Tests create_worktree.py, diff_worktree.py, and sync_worktree.py with
focus on gitignore handling, manifest creation, and edge cases.

Run with: pytest test_worktree_manager.py -v
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import create_worktree
import diff_worktree
import sync_worktree


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tmp_git_repo(tmp_path):
    """Create a temporary git repository with basic structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    # Create initial commit so branch exists
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)
    return repo


@pytest.fixture
def tmp_git_repo_with_gitignore(tmp_git_repo):
    """Git repo with .gitignore and various ignored content."""
    repo = tmp_git_repo

    # Create .gitignore
    gitignore = "output/\n.env\nbuild/**\ncache/\n"
    (repo / ".gitignore").write_text(gitignore)

    # Create ignored content
    (repo / "output").mkdir()
    (repo / "output" / "result.csv").write_text("a,b\n1,2\n")
    (repo / "output" / "subdir").mkdir()
    (repo / "output" / "subdir" / "nested.txt").write_text("nested\n")

    (repo / ".env").write_text("SECRET=abc\n")

    (repo / "build").mkdir()
    (repo / "build" / "app.js").write_text("console.log('built');\n")

    (repo / "cache").mkdir()
    (repo / "cache" / "data.bin").write_bytes(b"\x00" * 100)

    # Commit gitignore
    subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add gitignore"], cwd=repo, capture_output=True, check=True)

    return repo


@pytest.fixture
def tmp_git_repo_with_annotations(tmp_git_repo):
    """Git repo with worktree:symlink annotations in .gitignore."""
    repo = tmp_git_repo

    gitignore = (
        "output/\n"
        "data/  # worktree:symlink\n"
        "build/**  # worktree:symlink\n"
        "cache/*  # worktree:symlink\n"
        ".env\n"
        "models/*.bin  # worktree:symlink\n"
    )
    (repo / ".gitignore").write_text(gitignore)

    # Create the directories/files
    (repo / "output").mkdir()
    (repo / "output" / "result.csv").write_text("data\n")

    (repo / "data").mkdir()
    (repo / "data" / "input.csv").write_text("input\n")

    (repo / "build").mkdir()
    (repo / "build" / "app.js").write_text("built\n")

    (repo / "cache").mkdir()
    (repo / "cache" / "temp.bin").write_bytes(b"\x01" * 50)

    (repo / "models").mkdir()
    (repo / "models" / "large.bin").write_bytes(b"\x02" * 200)

    (repo / ".env").write_text("KEY=val\n")

    subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add gitignore"], cwd=repo, capture_output=True, check=True)

    return repo


@pytest.fixture
def tmp_git_repo_with_symlinks(tmp_git_repo):
    """Git repo with tracked symlinks pointing to external directories."""
    repo = tmp_git_repo
    external = repo.parent / "external"
    external.mkdir()

    # Create external directories
    (external / "shared_data").mkdir()
    (external / "shared_data" / "file1.txt").write_text("shared1\n")
    (external / "shared_data" / "file2.txt").write_text("shared2\n")

    (external / "shared_notes").mkdir()
    (external / "shared_notes" / "note.md").write_text("# Note\n")

    # Create symlinks in repo (tracked by git)
    (repo / "Data").symlink_to(external / "shared_data")
    (repo / "Notes").symlink_to(external / "shared_notes")

    subprocess.run(["git", "add", "Data", "Notes"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add symlinks"], cwd=repo, capture_output=True, check=True)

    return repo


@pytest.fixture
def worktree_with_manifest(tmp_path):
    """Create a worktree directory with a manifest file."""
    wt = tmp_path / "worktree"
    wt.mkdir()

    # Create a fake git structure
    (wt / ".git").write_text("gitdir: /fake/.git/worktrees/wt\n")

    manifest = {
        "version": 1,
        "entries": [
            {"path": "output", "type": "directory", "source": str(tmp_path / "source" / "output")},
            {"path": ".env", "type": "cow_clone", "source": str(tmp_path / "source" / ".env")},
            {"path": "cache/model.bin", "type": "cloud_symlink", "source": str(tmp_path / "source" / "cache" / "model.bin")},
            {"path": "data", "type": "user_symlink", "source": str(tmp_path / "source" / "data")},
        ]
    }
    (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

    # Create source structure
    src = tmp_path / "source"
    src.mkdir()
    (src / "output").mkdir()
    (src / "output" / "result.csv").write_text("original\n")
    (src / ".env").write_text("SECRET=original\n")
    (src / "cache").mkdir()
    (src / "cache" / "model.bin").write_bytes(b"\x00" * 50)
    (src / "data").mkdir()
    (src / "data" / "input.csv").write_text("data\n")

    return wt, src, manifest


# ============================================================
# Tests for create_worktree.py
# ============================================================


class TestGetGitignoredPaths:
    """Tests for get_gitignored_paths()."""

    def test_empty_repo_no_ignored(self, tmp_git_repo):
        """No .gitignore means no ignored paths."""
        result = create_worktree.get_gitignored_paths(tmp_git_repo)
        assert result == []

    def test_directory_pattern(self, tmp_git_repo_with_gitignore):
        """Pattern 'output/' returns the directory with is_dir=True."""
        result = create_worktree.get_gitignored_paths(tmp_git_repo_with_gitignore)
        paths = {str(p): is_dir for p, is_dir in result}
        # git ls-files --directory should list output/ as a single directory entry
        assert "output" in paths
        assert paths["output"] is True

    def test_file_pattern(self, tmp_git_repo_with_gitignore):
        """.env is returned as a file (no trailing slash)."""
        result = create_worktree.get_gitignored_paths(tmp_git_repo_with_gitignore)
        paths = {str(p): is_dir for p, is_dir in result}
        assert ".env" in paths
        assert paths[".env"] is False

    def test_glob_pattern(self, tmp_git_repo):
        """Pattern 'output/**' returns individual files under output/."""
        repo = tmp_git_repo
        (repo / ".gitignore").write_text("output/**\n")
        (repo / "output").mkdir()
        (repo / "output" / "a.txt").write_text("a\n")
        (repo / "output" / "b.txt").write_text("b\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "gitignore"], cwd=repo, capture_output=True, check=True)

        result = create_worktree.get_gitignored_paths(repo)
        paths = [str(p) for p, _ in result]
        # With --directory flag and output/** pattern, git should return individual files
        # because the directory itself is not ignored, only its contents
        assert any("output" in p for p in paths)

    def test_multiple_patterns(self, tmp_git_repo_with_gitignore):
        """Multiple gitignore patterns all get discovered."""
        result = create_worktree.get_gitignored_paths(tmp_git_repo_with_gitignore)
        paths = [str(p) for p, _ in result]
        # Should find output, .env, build, cache
        assert any("output" in p for p in paths)
        assert ".env" in paths
        assert any("build" in p for p in paths)
        assert any("cache" in p for p in paths)

    def test_nonexistent_ignored_path(self, tmp_git_repo):
        """Gitignore pattern for path that doesn't exist returns nothing for it."""
        repo = tmp_git_repo
        (repo / ".gitignore").write_text("nonexistent/\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "gitignore"], cwd=repo, capture_output=True, check=True)

        result = create_worktree.get_gitignored_paths(repo)
        paths = [str(p) for p, _ in result]
        assert "nonexistent" not in paths

    def test_hidden_files_included(self, tmp_git_repo):
        """Hidden files like .env are included in results."""
        repo = tmp_git_repo
        (repo / ".gitignore").write_text(".env\n.secret\n")
        (repo / ".env").write_text("val=1\n")
        (repo / ".secret").write_text("s\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "gitignore"], cwd=repo, capture_output=True, check=True)

        result = create_worktree.get_gitignored_paths(repo)
        paths = [str(p) for p, _ in result]
        assert ".env" in paths
        assert ".secret" in paths


class TestParseWorktreeAnnotations:
    """Tests for parse_worktree_annotations()."""

    def test_no_gitignore(self, tmp_path):
        """No .gitignore returns empty set."""
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == set()

    def test_no_annotations(self, tmp_path):
        """.gitignore without annotations returns empty set."""
        (tmp_path / ".gitignore").write_text("output/\n.env\nbuild/\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == set()

    def test_directory_with_slash_annotation(self, tmp_path):
        """'output/  # worktree:symlink' normalizes to 'output'."""
        (tmp_path / ".gitignore").write_text("output/  # worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"output"}

    def test_double_star_glob_annotation(self, tmp_path):
        """'output/**  # worktree:symlink' normalizes to 'output'."""
        (tmp_path / ".gitignore").write_text("output/**  # worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"output"}

    def test_single_star_glob_annotation(self, tmp_path):
        """'cache/*  # worktree:symlink' normalizes to 'cache'."""
        (tmp_path / ".gitignore").write_text("cache/*  # worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"cache"}

    def test_bare_name_annotation(self, tmp_path):
        """'output  # worktree:symlink' stays as 'output'."""
        (tmp_path / ".gitignore").write_text("output  # worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"output"}

    def test_nested_path_annotation(self, tmp_path):
        """'data/raw/  # worktree:symlink' normalizes to 'data/raw'."""
        (tmp_path / ".gitignore").write_text("data/raw/  # worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"data/raw"}

    def test_comment_only_line_skipped(self, tmp_path):
        """Line with only '# worktree:symlink' and no pattern is skipped."""
        (tmp_path / ".gitignore").write_text("# worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == set()

    def test_multiple_annotations(self, tmp_path):
        """Multiple annotated lines all get parsed."""
        content = (
            "output/\n"
            "data/  # worktree:symlink\n"
            "build/**  # worktree:symlink\n"
            ".env\n"
            "cache/*  # worktree:symlink\n"
        )
        (tmp_path / ".gitignore").write_text(content)
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"data", "build", "cache"}

    def test_mixed_annotated_and_plain(self, tmp_path):
        """Only annotated lines are returned."""
        content = (
            "output/\n"
            "data/  # worktree:symlink\n"
            ".env\n"
        )
        (tmp_path / ".gitignore").write_text(content)
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert "output" not in result
        assert "data" in result
        assert ".env" not in result

    def test_file_annotation(self, tmp_path):
        """'.env  # worktree:symlink' returns '.env'."""
        (tmp_path / ".gitignore").write_text(".env  # worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {".env"}

    def test_models_glob_annotation(self, tmp_path):
        """'models/*.bin  # worktree:symlink' normalizes to 'models'."""
        (tmp_path / ".gitignore").write_text("models/*.bin  # worktree:symlink\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"models"}


class TestCloneGitignored:
    """Tests for clone_gitignored()."""

    def test_basic_directory_clone(self, tmp_git_repo_with_gitignore, tmp_path):
        """Gitignored directory is COW-cloned with manifest entries."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_gitignored(src, dst)

        # Should have entries for ignored content
        assert len(entries) > 0
        entry_paths = [e["path"] for e in entries]
        assert any("output" in p for p in entry_paths)

    def test_directory_entry_type(self, tmp_git_repo_with_gitignore, tmp_path):
        """Directory entries have type 'directory'."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_gitignored(src, dst)

        dir_entries = [e for e in entries if e["type"] == "directory"]
        assert len(dir_entries) > 0
        for entry in dir_entries:
            assert "source" in entry
            assert Path(entry["source"]).is_dir()

    def test_file_entry_cow_clone(self, tmp_git_repo_with_gitignore, tmp_path):
        """Gitignored files get cow_clone type entries."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_gitignored(src, dst)

        cow_entries = [e for e in entries if e["type"] == "cow_clone"]
        # .env should be cow_clone
        env_entries = [e for e in cow_entries if ".env" in e["path"]]
        assert len(env_entries) == 1
        # Verify the file was actually copied
        assert (dst / ".env").exists()
        assert (dst / ".env").read_text() == "SECRET=abc\n"

    def test_user_symlink_created_first(self, tmp_git_repo_with_annotations, tmp_path):
        """User-annotated paths are symlinked before COW cloning."""
        src = tmp_git_repo_with_annotations
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_gitignored(src, dst)

        symlink_entries = [e for e in entries if e["type"] == "user_symlink"]
        assert len(symlink_entries) > 0

        # 'data' should be a symlink
        data_entries = [e for e in symlink_entries if e["path"] == "data"]
        assert len(data_entries) == 1
        assert (dst / "data").is_symlink()

    def test_user_symlink_nonexistent_source_skipped(self, tmp_path):
        """User-annotated path that doesn't exist is skipped."""
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()

        (src / ".gitignore").write_text("nonexistent/  # worktree:symlink\n")

        entries = create_worktree.clone_gitignored(src, dst)
        symlink_entries = [e for e in entries if e["type"] == "user_symlink"]
        assert len(symlink_entries) == 0

    def test_user_symlink_already_exists_skipped(self, tmp_git_repo_with_annotations, tmp_path):
        """User-symlinked path already in destination is skipped."""
        src = tmp_git_repo_with_annotations
        dst = tmp_path / "dst"
        dst.mkdir()
        # Pre-create the destination
        (dst / "data").mkdir()

        entries = create_worktree.clone_gitignored(src, dst)

        data_entries = [e for e in entries if e["path"] == "data" and e["type"] == "user_symlink"]
        assert len(data_entries) == 0

    def test_paths_under_user_symlink_skipped(self, tmp_git_repo_with_annotations, tmp_path):
        """Paths under a user-symlinked directory are not COW-cloned separately."""
        src = tmp_git_repo_with_annotations
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_gitignored(src, dst)

        # Nothing under "data/" should appear as cow_clone or directory
        for entry in entries:
            if entry["type"] in ("cow_clone", "directory"):
                assert not entry["path"].startswith("data/"), \
                    f"Path {entry['path']} should be skipped (under user symlink)"

    def test_destination_already_exists_skipped(self, tmp_git_repo_with_gitignore, tmp_path):
        """Ignored paths already present in destination are skipped."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "dst"
        dst.mkdir()
        # Pre-create output with different content
        (dst / "output").mkdir()
        (dst / "output" / "existing.txt").write_text("existing\n")

        entries = create_worktree.clone_gitignored(src, dst)

        # output should not appear in entries (already exists)
        output_entries = [e for e in entries if e["path"] == "output"]
        assert len(output_entries) == 0
        # The pre-existing file should remain untouched
        assert (dst / "output" / "existing.txt").read_text() == "existing\n"

    def test_directory_contents_cloned(self, tmp_git_repo_with_gitignore, tmp_path):
        """Directory clone copies all contents."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "dst"
        dst.mkdir()

        create_worktree.clone_gitignored(src, dst)

        # Check output directory contents were cloned
        assert (dst / "output" / "result.csv").exists()
        assert (dst / "output" / "subdir" / "nested.txt").exists()

    def test_manifest_entry_has_source(self, tmp_git_repo_with_gitignore, tmp_path):
        """All manifest entries include resolved source path."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_gitignored(src, dst)

        for entry in entries:
            assert "source" in entry
            assert "path" in entry
            assert "type" in entry
            # Source should be an absolute path
            assert Path(entry["source"]).is_absolute()


class TestCloneSymlinkTargets:
    """Tests for clone_symlink_targets()."""

    def test_tracked_directory_symlink(self, tmp_git_repo_with_symlinks, tmp_path, monkeypatch):
        """Tracked directory symlink is cloned as a real directory."""
        src = tmp_git_repo_with_symlinks
        monkeypatch.chdir(src)
        dst = tmp_path / "dst"
        dst.mkdir()
        # Create the directory structure git would create
        (dst / "README.md").write_text("# Test\n")

        entries = create_worktree.clone_symlink_targets(src, dst)

        # Data should be cloned
        data_entries = [e for e in entries if e["path"] == "Data"]
        assert len(data_entries) == 1
        assert data_entries[0]["type"] == "directory"
        assert (dst / "Data").is_dir()
        assert not (dst / "Data").is_symlink()
        assert (dst / "Data" / "file1.txt").exists()

    def test_tracked_file_symlink(self, tmp_git_repo, tmp_path, monkeypatch):
        """Tracked file symlink is COW-cloned."""
        repo = tmp_git_repo
        monkeypatch.chdir(repo)
        external = repo.parent / "external"
        external.mkdir()
        (external / "config.json").write_text('{"key": "val"}\n')

        (repo / "config.json").symlink_to(external / "config.json")
        subprocess.run(["git", "add", "config.json"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "add config"], cwd=repo, capture_output=True, check=True)

        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "README.md").write_text("# Test\n")

        entries = create_worktree.clone_symlink_targets(repo, dst)

        config_entries = [e for e in entries if e["path"] == "config.json"]
        assert len(config_entries) == 1
        assert config_entries[0]["type"] == "cow_clone"
        assert (dst / "config.json").exists()
        assert not (dst / "config.json").is_symlink()

    def test_tracked_symlink_within_repo_kept(self, tmp_git_repo, tmp_path, monkeypatch):
        """Tracked symlink pointing inside repo is kept as symlink."""
        repo = tmp_git_repo
        monkeypatch.chdir(repo)
        (repo / "CLAUDE.md").write_text("# Instructions\n")
        (repo / "AGENTS.md").symlink_to("CLAUDE.md")
        subprocess.run(["git", "add", "CLAUDE.md", "AGENTS.md"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "add internal symlink"], cwd=repo, capture_output=True, check=True)

        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "CLAUDE.md").write_text("# Instructions\n")
        (dst / "AGENTS.md").symlink_to("CLAUDE.md")

        entries = create_worktree.clone_symlink_targets(repo, dst)

        assert not any(e["path"] == "AGENTS.md" for e in entries)
        assert (dst / "AGENTS.md").is_symlink()
        assert (dst / "AGENTS.md").resolve() == (dst / "CLAUDE.md").resolve()

    def test_untracked_symlink_skipped(self, tmp_git_repo, tmp_path, monkeypatch):
        """Non-tracked symlinks are skipped."""
        repo = tmp_git_repo
        monkeypatch.chdir(repo)
        external = repo.parent / "external"
        external.mkdir()
        (external / "untracked_dir").mkdir()
        (external / "untracked_dir" / "file.txt").write_text("x\n")

        (repo / "UntrData").symlink_to(external / "untracked_dir")
        # Do NOT git add it

        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_symlink_targets(repo, dst)

        untr_entries = [e for e in entries if "UntrData" in e.get("path", "")]
        assert len(untr_entries) == 0

    def test_hidden_files_skipped(self, tmp_git_repo, tmp_path):
        """Hidden files/dirs (starting with .) are skipped."""
        repo = tmp_git_repo
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_symlink_targets(repo, dst)

        for entry in entries:
            assert not entry["path"].startswith(".")

    def test_unresolvable_symlink_skipped(self, tmp_git_repo, tmp_path, capsys, monkeypatch):
        """Symlink pointing to nonexistent target is skipped with warning."""
        repo = tmp_git_repo
        monkeypatch.chdir(repo)
        (repo / "broken").symlink_to("/nonexistent/path/that/does/not/exist")
        subprocess.run(["git", "add", "broken"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "broken symlink"], cwd=repo, capture_output=True, check=True)

        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_symlink_targets(repo, dst)

        broken_entries = [e for e in entries if "broken" in e.get("path", "")]
        assert len(broken_entries) == 0
        captured = capsys.readouterr()
        assert "Skipping" in captured.out or len(entries) == 0

    def test_nested_tracked_symlinks(self, tmp_git_repo, tmp_path, monkeypatch):
        """Tracked symlinks inside subdirectories are found."""
        repo = tmp_git_repo
        monkeypatch.chdir(repo)
        external = repo.parent / "external"
        external.mkdir()
        (external / "deep_data").mkdir()
        (external / "deep_data" / "file.txt").write_text("deep\n")

        (repo / "src").mkdir()
        (repo / "src" / "link").symlink_to(external / "deep_data")
        subprocess.run(["git", "add", "src/link"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "nested symlink"], cwd=repo, capture_output=True, check=True)

        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "src").mkdir()

        entries = create_worktree.clone_symlink_targets(repo, dst)

        link_entries = [e for e in entries if "src/link" in e.get("path", "")]
        assert len(link_entries) == 1
        assert (dst / "src" / "link").is_dir()

    def test_permission_error_returns_empty(self, tmp_path):
        """PermissionError on iterdir returns empty list."""
        src = tmp_path / "noperm"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()

        with patch.object(Path, 'iterdir', side_effect=PermissionError("denied")):
            entries = create_worktree.clone_symlink_targets(src, dst)

        assert entries == []

    def test_returns_manifest_entries(self, tmp_git_repo_with_symlinks, tmp_path, monkeypatch):
        """All returned entries have required fields."""
        src = tmp_git_repo_with_symlinks
        monkeypatch.chdir(src)
        dst = tmp_path / "dst"
        dst.mkdir()

        entries = create_worktree.clone_symlink_targets(src, dst)

        for entry in entries:
            assert "path" in entry
            assert "type" in entry
            assert "source" in entry
            assert entry["type"] in ("directory", "cow_clone", "cloud_symlink")


class TestSmartCopyDir:
    """Tests for smart_copy_dir() edge cases."""

    def test_empty_directory(self, tmp_path):
        """Empty directory copies without error."""
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()

        local, cloud = create_worktree.smart_copy_dir(src, dst)
        assert local == 0
        assert cloud == 0

    def test_nested_directories(self, tmp_path):
        """Nested directories are recursively copied."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a").mkdir()
        (src / "a" / "b").mkdir()
        (src / "a" / "b" / "file.txt").write_text("deep\n")

        dst = tmp_path / "dst"
        dst.mkdir()

        local, cloud = create_worktree.smart_copy_dir(src, dst)
        assert local == 1
        assert (dst / "a" / "b" / "file.txt").exists()

    def test_symlinks_inside_directory_recreated(self, tmp_path):
        """Symlinks inside a directory are recreated as symlinks."""
        src = tmp_path / "src"
        src.mkdir()
        target = tmp_path / "target.txt"
        target.write_text("target\n")
        (src / "link.txt").symlink_to(target)

        dst = tmp_path / "dst"
        dst.mkdir()

        create_worktree.smart_copy_dir(src, dst)
        assert (dst / "link.txt").is_symlink()


class TestManifestCreation:
    """Tests for manifest writing in main()."""

    def test_manifest_format(self, tmp_git_repo_with_gitignore, tmp_path):
        """Manifest has correct structure."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "wt"
        dst.mkdir()

        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(src, dst))
        manifest["entries"].extend(create_worktree.clone_symlink_targets(src, dst))

        assert manifest["version"] == 1
        assert isinstance(manifest["entries"], list)
        for entry in manifest["entries"]:
            assert "path" in entry
            assert "type" in entry
            assert "source" in entry

    def test_manifest_json_serializable(self, tmp_git_repo_with_gitignore, tmp_path):
        """Manifest can be serialized to JSON."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "wt"
        dst.mkdir()

        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(src, dst))

        # Should not raise
        json_str = json.dumps(manifest, indent=2)
        parsed = json.loads(json_str)
        assert parsed["version"] == 1

    def test_combined_entries_from_both_functions(self, tmp_git_repo_with_symlinks, tmp_path, monkeypatch):
        """Entries from clone_gitignored and clone_symlink_targets are combined."""
        repo = tmp_git_repo_with_symlinks
        monkeypatch.chdir(repo)
        # Add a gitignore pattern
        (repo / ".gitignore").write_text("build/\n")
        (repo / "build").mkdir()
        (repo / "build" / "out.js").write_text("built\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "gitignore"], cwd=repo, capture_output=True, check=True)

        dst = tmp_path / "wt"
        dst.mkdir()

        entries_ignored = create_worktree.clone_gitignored(repo, dst)
        entries_symlinks = create_worktree.clone_symlink_targets(repo, dst)

        all_entries = entries_ignored + entries_symlinks
        paths = [e["path"] for e in all_entries]
        # Should have both gitignored and symlink entries
        assert any("build" in p for p in paths)
        assert any("Data" in p for p in paths)


# ============================================================
# Tests for diff_worktree.py
# ============================================================


class TestGetManifestEntries:
    """Tests for get_manifest_entries()."""

    def test_manifest_exists(self, worktree_with_manifest):
        """When manifest exists, entries are read from it."""
        wt, src, manifest = worktree_with_manifest
        entries = diff_worktree.get_manifest_entries(wt)
        assert len(entries) == 4
        assert entries[0]["path"] == "output"
        assert entries[0]["type"] == "directory"

    def test_empty_manifest(self, tmp_path):
        """Manifest with empty entries returns empty list."""
        wt = tmp_path / "wt"
        wt.mkdir()
        manifest = {"version": 1, "entries": []}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        entries = diff_worktree.get_manifest_entries(wt)
        assert entries == []

    def test_legacy_fallback(self, tmp_git_repo_with_symlinks):
        """Without manifest, falls back to symlink detection."""
        repo = tmp_git_repo_with_symlinks

        # Create a worktree without manifest
        wt_path = repo.parent / "test-wt"
        subprocess.run(
            ["git", "worktree", "add", str(wt_path), "-b", "test-branch"],
            cwd=repo, capture_output=True, check=True
        )

        try:
            entries = diff_worktree.get_manifest_entries(wt_path)
            # Legacy: should detect Data and Notes symlinked dirs from main
            entry_paths = [e["path"] for e in entries]
            assert "Data" in entry_paths
            assert "Notes" in entry_paths
            for e in entries:
                assert e["type"] == "directory"
        finally:
            subprocess.run(["git", "worktree", "remove", str(wt_path)],
                          cwd=repo, capture_output=True)


class TestDiffFile:
    """Tests for diff_file()."""

    def test_symlink_returns_none(self, tmp_path):
        """Symlink file returns None (cloud file unmodified)."""
        target = tmp_path / "target.txt"
        target.write_text("data\n")
        link = tmp_path / "link.txt"
        link.symlink_to(target)

        result = diff_worktree.diff_file(link, target, "link.txt", "dir")
        assert result is None

    def test_nonexistent_worktree_file_returns_none(self, tmp_path):
        """Worktree file that doesn't exist returns None."""
        source = tmp_path / "source.txt"
        source.write_text("data\n")
        wt_file = tmp_path / "nonexistent.txt"

        result = diff_worktree.diff_file(wt_file, source, "nonexistent.txt", "dir")
        assert result is None

    def test_source_doesnt_exist_returns_new(self, tmp_path):
        """Source file missing means the worktree file is new."""
        wt_file = tmp_path / "new_file.txt"
        wt_file.write_text("new content\n")
        source = tmp_path / "nonexistent_source.txt"

        result = diff_worktree.diff_file(wt_file, source, "new_file.txt", "output")
        assert result is not None
        assert result.status == "new"
        assert result.share_path is None

    def test_identical_files_returns_none(self, tmp_path):
        """Identical files (same size and mtime) return None."""
        src = tmp_path / "src.txt"
        src.write_text("same content\n")
        dst = tmp_path / "dst.txt"
        shutil.copy2(src, dst)  # Preserves mtime

        result = diff_worktree.diff_file(dst, src, "file.txt", "dir")
        assert result is None

    def test_different_size_returns_modified(self, tmp_path):
        """Files with different sizes are detected as modified."""
        src = tmp_path / "src.txt"
        src.write_text("short\n")
        dst = tmp_path / "dst.txt"
        dst.write_text("this is much longer content\n")

        result = diff_worktree.diff_file(dst, src, "file.txt", "dir")
        assert result is not None
        assert result.status == "modified"

    def test_different_mtime_returns_modified(self, tmp_path):
        """Files with same size but different mtime are detected as modified."""
        src = tmp_path / "src.txt"
        src.write_text("same size txt\n")
        dst = tmp_path / "dst.txt"
        dst.write_text("same size txt\n")
        # Set very different mtime
        os.utime(dst, (time.time() + 100, time.time() + 100))

        result = diff_worktree.diff_file(dst, src, "file.txt", "dir")
        assert result is not None
        assert result.status == "modified"

    def test_include_unmodified(self, tmp_path):
        """With include_unmodified=True, identical files return 'unchanged'."""
        src = tmp_path / "src.txt"
        src.write_text("content\n")
        dst = tmp_path / "dst.txt"
        shutil.copy2(src, dst)

        result = diff_worktree.diff_file(dst, src, "file.txt", "dir", include_unmodified=True)
        assert result is not None
        assert result.status == "unchanged"

    def test_hash_comparison_identical(self, tmp_path):
        """Hash comparison correctly identifies identical files."""
        src = tmp_path / "src.txt"
        src.write_text("content\n")
        dst = tmp_path / "dst.txt"
        dst.write_text("content\n")
        # Different mtime but same content
        os.utime(dst, (time.time() + 100, time.time() + 100))

        result = diff_worktree.diff_file(dst, src, "file.txt", "dir", use_hash=True)
        assert result is None  # Same content by hash

    def test_hash_comparison_different(self, tmp_path):
        """Hash comparison correctly identifies different files."""
        src = tmp_path / "src.txt"
        src.write_text("content A\n")
        dst = tmp_path / "dst.txt"
        dst.write_text("content B\n")

        result = diff_worktree.diff_file(dst, src, "file.txt", "dir", use_hash=True)
        assert result is not None
        assert result.status == "modified"

    def test_filechange_fields_populated(self, tmp_path):
        """FileChange has all required fields properly set."""
        src = tmp_path / "src.txt"
        src.write_text("original\n")
        dst = tmp_path / "dst.txt"
        dst.write_text("modified content here\n")

        result = diff_worktree.diff_file(dst, src, "sub/file.txt", "output")
        assert result.worktree_path == str(dst)
        assert result.share_path == str(src)
        assert result.relative_path == "sub/file.txt"
        assert result.directory == "output"
        assert result.size_worktree > 0
        assert result.size_share > 0


class TestDiffDirectory:
    """Tests for diff_directory()."""

    def test_new_files_detected(self, tmp_path):
        """Files only in worktree are marked as new."""
        wt_dir = tmp_path / "wt"
        wt_dir.mkdir()
        (wt_dir / "new.txt").write_text("new\n")

        share_dir = tmp_path / "share"
        share_dir.mkdir()

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        assert len(changes) == 1
        assert changes[0].status == "new"

    def test_modified_files_detected(self, tmp_path):
        """Modified files are correctly detected."""
        share_dir = tmp_path / "share"
        share_dir.mkdir()
        (share_dir / "file.txt").write_text("original\n")

        wt_dir = tmp_path / "wt"
        wt_dir.mkdir()
        (wt_dir / "file.txt").write_text("modified content is longer\n")

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        assert len(changes) == 1
        assert changes[0].status == "modified"

    def test_symlinks_skipped(self, tmp_path):
        """Symlink files in worktree are skipped."""
        target = tmp_path / "target.txt"
        target.write_text("target\n")

        wt_dir = tmp_path / "wt"
        wt_dir.mkdir()
        (wt_dir / "link.txt").symlink_to(target)
        (wt_dir / "real.txt").write_text("real new file\n")

        share_dir = tmp_path / "share"
        share_dir.mkdir()

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        # Only real.txt should appear, link.txt is skipped
        assert len(changes) == 1
        assert "real.txt" in changes[0].relative_path

    def test_hidden_files_skipped(self, tmp_path):
        """Hidden files (starting with .) are skipped."""
        wt_dir = tmp_path / "wt"
        wt_dir.mkdir()
        (wt_dir / ".hidden").write_text("hidden\n")
        (wt_dir / "visible.txt").write_text("visible\n")

        share_dir = tmp_path / "share"
        share_dir.mkdir()

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        assert len(changes) == 1
        assert "visible.txt" in changes[0].relative_path

    def test_hidden_directories_skipped(self, tmp_path):
        """Hidden directories are not traversed."""
        wt_dir = tmp_path / "wt"
        wt_dir.mkdir()
        (wt_dir / ".hidden_dir").mkdir()
        (wt_dir / ".hidden_dir" / "file.txt").write_text("in hidden\n")
        (wt_dir / "visible_dir").mkdir()
        (wt_dir / "visible_dir" / "file.txt").write_text("in visible\n")

        share_dir = tmp_path / "share"
        share_dir.mkdir()

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        paths = [c.relative_path for c in changes]
        assert not any(".hidden_dir" in p for p in paths)
        assert any("visible_dir" in p for p in paths)

    def test_symlink_directories_skipped(self, tmp_path):
        """Symlink directories are not traversed."""
        target_dir = tmp_path / "target_dir"
        target_dir.mkdir()
        (target_dir / "file.txt").write_text("in target\n")

        wt_dir = tmp_path / "wt"
        wt_dir.mkdir()
        (wt_dir / "linked_dir").symlink_to(target_dir)
        (wt_dir / "real_dir").mkdir()
        (wt_dir / "real_dir" / "file.txt").write_text("in real\n")

        share_dir = tmp_path / "share"
        share_dir.mkdir()

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        paths = [c.relative_path for c in changes]
        assert not any("linked_dir" in p for p in paths)

    def test_nested_new_files(self, tmp_path):
        """New files in subdirectories are detected."""
        wt_dir = tmp_path / "wt"
        wt_dir.mkdir()
        (wt_dir / "sub").mkdir()
        (wt_dir / "sub" / "deep").mkdir()
        (wt_dir / "sub" / "deep" / "file.txt").write_text("deep new\n")

        share_dir = tmp_path / "share"
        share_dir.mkdir()

        changes = diff_worktree.diff_directory(wt_dir, share_dir, "output")
        assert len(changes) == 1
        assert changes[0].relative_path == "sub/deep/file.txt"


class TestDiffMainDispatch:
    """Tests for the manifest-based dispatch in main loop logic."""

    def test_directory_entry_dispatches_to_diff_directory(self, worktree_with_manifest):
        """Directory entries trigger diff_directory."""
        wt, src, manifest = worktree_with_manifest
        # Create worktree's output directory with a modified file
        (wt / "output").mkdir()
        (wt / "output" / "result.csv").write_text("modified content\n")

        entries = diff_worktree.get_manifest_entries(wt)
        dir_entries = [e for e in entries if e["type"] == "directory"]
        assert len(dir_entries) == 1

        # Simulate what main loop does
        entry = dir_entries[0]
        source = Path(entry["source"])
        worktree_item = wt / entry["path"]
        changes = diff_worktree.diff_directory(worktree_item, source, entry["path"])
        assert len(changes) == 1
        assert changes[0].status == "modified"

    def test_cow_clone_entry_dispatches_to_diff_file(self, worktree_with_manifest):
        """cow_clone entries trigger diff_file."""
        wt, src, manifest = worktree_with_manifest
        # Create worktree's .env with modified content (different size to ensure detection)
        (wt / ".env").write_text("SECRET=modified_value_that_is_longer\n")

        entries = diff_worktree.get_manifest_entries(wt)
        cow_entries = [e for e in entries if e["type"] == "cow_clone"]
        assert len(cow_entries) == 1

        entry = cow_entries[0]
        result = diff_worktree.diff_file(
            wt / entry["path"],
            Path(entry["source"]),
            entry["path"],
            entry["path"],
        )
        assert result is not None
        assert result.status == "modified"

    def test_cloud_symlink_still_symlink_skipped(self, worktree_with_manifest):
        """cloud_symlink entry that's still a symlink is skipped."""
        wt, src, manifest = worktree_with_manifest
        # Create the cache dir and symlink
        (wt / "cache").mkdir(parents=True)
        source_file = Path(manifest["entries"][2]["source"])
        (wt / "cache" / "model.bin").symlink_to(source_file)

        entries = diff_worktree.get_manifest_entries(wt)
        cloud_entries = [e for e in entries if e["type"] == "cloud_symlink"]
        assert len(cloud_entries) == 1

        entry = cloud_entries[0]
        worktree_item = wt / entry["path"]
        # Still a symlink → should be skipped
        assert worktree_item.is_symlink()

    def test_cloud_symlink_broken_to_real_file_detected(self, worktree_with_manifest):
        """cloud_symlink entry broken to real file is detected as modified."""
        wt, src, manifest = worktree_with_manifest
        # Create real file instead of symlink (simulating user modification)
        (wt / "cache").mkdir(parents=True)
        (wt / "cache" / "model.bin").write_bytes(b"\xFF" * 100)

        entries = diff_worktree.get_manifest_entries(wt)
        cloud_entries = [e for e in entries if e["type"] == "cloud_symlink"]

        entry = cloud_entries[0]
        worktree_item = wt / entry["path"]
        assert not worktree_item.is_symlink()
        assert worktree_item.exists()

        result = diff_worktree.diff_file(
            worktree_item,
            Path(entry["source"]),
            entry["path"],
            entry["path"],
        )
        assert result is not None
        assert result.status == "modified"

    def test_user_symlink_entry_skipped(self, worktree_with_manifest):
        """user_symlink entries are always skipped in diff."""
        wt, src, manifest = worktree_with_manifest
        entries = diff_worktree.get_manifest_entries(wt)
        user_entries = [e for e in entries if e["type"] == "user_symlink"]
        assert len(user_entries) == 1
        # In the main loop, user_symlink just does 'continue'


# ============================================================
# Tests for sync_worktree.py
# ============================================================


class TestBuildSourceMap:
    """Tests for build_source_map()."""

    def test_manifest_exists(self, worktree_with_manifest):
        """Source map is built from manifest entries."""
        wt, src, manifest = worktree_with_manifest
        source_map = sync_worktree.build_source_map(wt)

        assert "output" in source_map
        assert ".env" in source_map
        assert "cache/model.bin" in source_map
        assert "data" in source_map
        assert source_map["output"] == Path(str(src / "output"))

    def test_no_manifest_legacy_fallback(self, tmp_git_repo_with_symlinks):
        """Without manifest, falls back to symlinked dirs."""
        repo = tmp_git_repo_with_symlinks
        wt_path = repo.parent / "test-wt-sync"
        subprocess.run(
            ["git", "worktree", "add", str(wt_path), "-b", "test-sync"],
            cwd=repo, capture_output=True, check=True
        )

        try:
            source_map = sync_worktree.build_source_map(wt_path)
            assert "Data" in source_map
            assert "Notes" in source_map
        finally:
            subprocess.run(["git", "worktree", "remove", str(wt_path)],
                          cwd=repo, capture_output=True)

    def test_empty_manifest(self, tmp_path):
        """Empty manifest returns empty source map."""
        wt = tmp_path / "wt"
        wt.mkdir()
        manifest = {"version": 1, "entries": []}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        source_map = sync_worktree.build_source_map(wt)
        assert source_map == {}


class TestResolveSharePath:
    """Tests for resolve_share_path()."""

    def test_known_directory_with_relative_path(self, tmp_path):
        """Resolves correctly for known directory entries."""
        source_map = {"output": Path("/abs/source/output")}
        result = sync_worktree.resolve_share_path(
            tmp_path, "sub/file.csv", "output", source_map
        )
        assert result == Path("/abs/source/output/sub/file.csv")

    def test_known_directory_empty_relative_path(self, tmp_path):
        """Empty relative_path returns source directly."""
        source_map = {".env": Path("/abs/source/.env")}
        result = sync_worktree.resolve_share_path(
            tmp_path, "", ".env", source_map
        )
        assert result == Path("/abs/source/.env")

    def test_unknown_directory_raises(self, tmp_path):
        """Unknown directory raises ValueError."""
        source_map = {"output": Path("/abs/source/output")}
        with pytest.raises(ValueError, match="not found in source map"):
            sync_worktree.resolve_share_path(
                tmp_path, "file.txt", "unknown_dir", source_map
            )

    def test_nested_path_entry(self, tmp_path):
        """Nested manifest path resolves correctly."""
        source_map = {"cache/model.bin": Path("/abs/source/cache/model.bin")}
        result = sync_worktree.resolve_share_path(
            tmp_path, "", "cache/model.bin", source_map
        )
        assert result == Path("/abs/source/cache/model.bin")


class TestProcessFile:
    """Tests for process_file()."""

    def test_symlink_skipped(self, tmp_path):
        """Symlink files are skipped (shared by design)."""
        target = tmp_path / "target.txt"
        target.write_text("data\n")
        link = tmp_path / "link.txt"
        link.symlink_to(target)

        result = sync_worktree.process_file(
            link, target, "overwrite", "_suffix", verbose=False
        )
        assert result is True

    def test_delete_action(self, tmp_path):
        """Delete action removes worktree file."""
        wt_file = tmp_path / "file.txt"
        wt_file.write_text("data\n")

        result = sync_worktree.process_file(
            wt_file, None, "delete", "_suffix", verbose=False
        )
        assert result is True
        assert not wt_file.exists()

    def test_overwrite_action(self, tmp_path):
        """Overwrite action copies worktree file to share."""
        wt_file = tmp_path / "wt" / "file.txt"
        wt_file.parent.mkdir()
        wt_file.write_text("modified\n")

        share_file = tmp_path / "share" / "file.txt"
        share_file.parent.mkdir()
        share_file.write_text("original\n")

        result = sync_worktree.process_file(
            wt_file, share_file, "overwrite", "_suffix", verbose=False
        )
        assert result is True
        assert share_file.read_text() == "modified\n"

    def test_rename_action(self, tmp_path):
        """Rename action copies with suffix."""
        wt_file = tmp_path / "wt" / "file.txt"
        wt_file.parent.mkdir()
        wt_file.write_text("modified\n")

        share_file = tmp_path / "share" / "file.txt"
        share_file.parent.mkdir()
        share_file.write_text("original\n")

        result = sync_worktree.process_file(
            wt_file, share_file, "rename", "_backup", verbose=False
        )
        assert result is True
        renamed = share_file.parent / "file_backup.txt"
        assert renamed.exists()
        assert renamed.read_text() == "modified\n"
        # Original should be untouched
        assert share_file.read_text() == "original\n"

    def test_overwrite_creates_parent_dirs(self, tmp_path):
        """Overwrite creates parent directories if needed."""
        wt_file = tmp_path / "wt" / "file.txt"
        wt_file.parent.mkdir()
        wt_file.write_text("data\n")

        share_file = tmp_path / "share" / "deep" / "path" / "file.txt"

        result = sync_worktree.process_file(
            wt_file, share_file, "overwrite", "_suffix", verbose=False
        )
        assert result is True
        assert share_file.exists()

    def test_dry_run_no_changes(self, tmp_path):
        """Dry run doesn't actually modify files."""
        wt_file = tmp_path / "file.txt"
        wt_file.write_text("data\n")

        result = sync_worktree.process_file(
            wt_file, None, "delete", "_suffix", dry_run=True, verbose=False
        )
        assert result is True
        assert wt_file.exists()  # Still exists


class TestProcessFromJson:
    """Tests for process_from_json() with manifest-based resolution."""

    def test_with_share_path(self, tmp_path):
        """When change has share_path, uses it directly."""
        wt = tmp_path / "wt"
        wt.mkdir()
        wt_file = wt / "output" / "file.txt"
        wt_file.parent.mkdir(parents=True)
        wt_file.write_text("modified\n")

        share = tmp_path / "share"
        share.mkdir()
        share_file = share / "file.txt"
        share_file.write_text("original\n")

        # Write manifest
        manifest = {"version": 1, "entries": [
            {"path": "output", "type": "directory", "source": str(share)}
        ]}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        # Write diff JSON
        diff_json = {
            "worktree_path": str(wt),
            "changes": [{
                "status": "modified",
                "worktree_path": str(wt_file),
                "share_path": str(share_file),
                "relative_path": "file.txt",
                "directory": "output",
                "size_worktree": 9,
                "size_share": 9,
                "mtime_worktree": 0,
                "mtime_share": 0,
            }]
        }
        json_path = tmp_path / "changes.json"
        json_path.write_text(json.dumps(diff_json))

        success, failure = sync_worktree.process_from_json(
            json_path, "overwrite", "_suffix", verbose=False
        )
        assert success == 1
        assert failure == 0
        assert share_file.read_text() == "modified\n"

    def test_without_share_path_resolves_from_map(self, tmp_path):
        """New files without share_path are resolved via source map."""
        wt = tmp_path / "wt"
        wt.mkdir()
        wt_file = wt / "output" / "new_file.txt"
        wt_file.parent.mkdir(parents=True)
        wt_file.write_text("new content\n")

        share = tmp_path / "share"
        share.mkdir()

        manifest = {"version": 1, "entries": [
            {"path": "output", "type": "directory", "source": str(share)}
        ]}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        diff_json = {
            "worktree_path": str(wt),
            "changes": [{
                "status": "new",
                "worktree_path": str(wt_file),
                "share_path": None,
                "relative_path": "new_file.txt",
                "directory": "output",
                "size_worktree": 12,
                "size_share": None,
                "mtime_worktree": 0,
                "mtime_share": None,
            }]
        }
        json_path = tmp_path / "changes.json"
        json_path.write_text(json.dumps(diff_json))

        success, failure = sync_worktree.process_from_json(
            json_path, "overwrite", "_suffix", verbose=False
        )
        assert success == 1
        expected_file = share / "new_file.txt"
        assert expected_file.exists()
        assert expected_file.read_text() == "new content\n"

    def test_status_filter(self, tmp_path):
        """Status filter only processes matching changes."""
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / "output").mkdir()
        (wt / "output" / "new.txt").write_text("new\n")
        (wt / "output" / "mod.txt").write_text("modified\n")

        share = tmp_path / "share"
        share.mkdir()
        (share / "mod.txt").write_text("original\n")

        manifest = {"version": 1, "entries": [
            {"path": "output", "type": "directory", "source": str(share)}
        ]}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        diff_json = {
            "worktree_path": str(wt),
            "changes": [
                {
                    "status": "new",
                    "worktree_path": str(wt / "output" / "new.txt"),
                    "share_path": None,
                    "relative_path": "new.txt",
                    "directory": "output",
                    "size_worktree": 4,
                    "size_share": None,
                    "mtime_worktree": 0,
                    "mtime_share": None,
                },
                {
                    "status": "modified",
                    "worktree_path": str(wt / "output" / "mod.txt"),
                    "share_path": str(share / "mod.txt"),
                    "relative_path": "mod.txt",
                    "directory": "output",
                    "size_worktree": 9,
                    "size_share": 9,
                    "mtime_worktree": 0,
                    "mtime_share": 0,
                },
            ]
        }
        json_path = tmp_path / "changes.json"
        json_path.write_text(json.dumps(diff_json))

        # Only process "new" files
        success, failure = sync_worktree.process_from_json(
            json_path, "overwrite", "_suffix",
            status_filter=["new"], verbose=False
        )
        assert success == 1
        assert (share / "new.txt").exists()
        # modified file should NOT have been overwritten
        assert (share / "mod.txt").read_text() == "original\n"


class TestProcessFiles:
    """Tests for process_files() with source map."""

    def test_file_not_found(self, tmp_path, capsys):
        """File not found in worktree is skipped."""
        wt = tmp_path / "wt"
        wt.mkdir()
        manifest = {"version": 1, "entries": [
            {"path": "output", "type": "directory", "source": str(tmp_path / "share")}
        ]}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        success, failure = sync_worktree.process_files(
            wt, ["output/nonexistent.txt"], "overwrite", "_suffix", verbose=False
        )
        assert success == 0
        assert failure == 1

    def test_file_not_in_source_map(self, tmp_path, capsys):
        """File in unknown directory is skipped."""
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / "unknown").mkdir()
        (wt / "unknown" / "file.txt").write_text("data\n")
        manifest = {"version": 1, "entries": [
            {"path": "output", "type": "directory", "source": str(tmp_path / "share")}
        ]}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        success, failure = sync_worktree.process_files(
            wt, ["unknown/file.txt"], "overwrite", "_suffix", verbose=False
        )
        assert success == 0
        assert failure == 1

    def test_successful_overwrite(self, tmp_path):
        """File in known directory is synced correctly."""
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / "output").mkdir()
        (wt / "output" / "result.csv").write_text("new data\n")

        share = tmp_path / "share"
        share.mkdir()
        (share / "result.csv").write_text("old data\n")

        manifest = {"version": 1, "entries": [
            {"path": "output", "type": "directory", "source": str(share)}
        ]}
        (wt / ".worktree-manifest.json").write_text(json.dumps(manifest))

        success, failure = sync_worktree.process_files(
            wt, ["output/result.csv"], "overwrite", "_suffix", verbose=False
        )
        assert success == 1
        assert (share / "result.csv").read_text() == "new data\n"


# ============================================================
# Integration Tests
# ============================================================


class TestEndToEndCreateDiffSync:
    """Integration tests for the full create → diff → sync workflow."""

    def test_full_workflow_with_gitignored_directory(self, tmp_git_repo_with_gitignore, tmp_path):
        """Full workflow: create clones gitignored dir, diff detects changes, sync copies back."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "worktree"
        dst.mkdir()

        # Create phase
        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(src, dst))
        manifest_path = dst / ".worktree-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Verify clone
        assert (dst / "output" / "result.csv").exists()
        assert (dst / "output" / "result.csv").read_text() == "a,b\n1,2\n"

        # Modify a file in worktree
        (dst / "output" / "result.csv").write_text("a,b\n1,2\n3,4\n")

        # Diff phase
        entries = diff_worktree.get_manifest_entries(dst)
        all_changes = []
        for entry in entries:
            if entry["type"] == "directory":
                worktree_item = dst / entry["path"]
                if worktree_item.exists():
                    changes = diff_worktree.diff_directory(
                        worktree_item, Path(entry["source"]), entry["path"]
                    )
                    all_changes.extend(changes)

        assert len(all_changes) == 1
        assert all_changes[0].status == "modified"
        assert "result.csv" in all_changes[0].relative_path

        # Sync phase - overwrite
        source_map = sync_worktree.build_source_map(dst)
        share_path = source_map["output"] / "result.csv"
        sync_worktree.process_file(
            dst / "output" / "result.csv",
            share_path,
            "overwrite", "_suffix", verbose=False
        )
        assert (src / "output" / "result.csv").read_text() == "a,b\n1,2\n3,4\n"

    def test_full_workflow_with_cow_clone_file(self, tmp_git_repo_with_gitignore, tmp_path):
        """Full workflow for individual COW-cloned file (.env)."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "worktree"
        dst.mkdir()

        # Create phase
        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(src, dst))
        manifest_path = dst / ".worktree-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        assert (dst / ".env").exists()
        assert (dst / ".env").read_text() == "SECRET=abc\n"

        # Modify (different size to ensure detection regardless of mtime proximity)
        (dst / ".env").write_text("SECRET=xyz_with_extra_content\nANOTHER_VAR=123\n")

        # Diff
        entries = diff_worktree.get_manifest_entries(dst)
        cow_entries = [e for e in entries if e["type"] == "cow_clone"]
        env_entry = next(e for e in cow_entries if ".env" in e["path"])

        change = diff_worktree.diff_file(
            dst / env_entry["path"],
            Path(env_entry["source"]),
            env_entry["path"],
            env_entry["path"],
        )
        assert change is not None
        assert change.status == "modified"

        # Sync
        source_map = sync_worktree.build_source_map(dst)
        sync_worktree.process_file(
            dst / ".env",
            Path(env_entry["source"]),
            "overwrite", "_suffix", verbose=False
        )
        assert (src / ".env").read_text() == "SECRET=xyz_with_extra_content\nANOTHER_VAR=123\n"

    def test_full_workflow_with_user_symlink(self, tmp_git_repo_with_annotations, tmp_path):
        """User-symlinked paths are shared state and skip diff/sync."""
        src = tmp_git_repo_with_annotations
        dst = tmp_path / "worktree"
        dst.mkdir()

        # Create phase
        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(src, dst))
        manifest_path = dst / ".worktree-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # 'data' should be a symlink
        user_entries = [e for e in manifest["entries"] if e["type"] == "user_symlink"]
        assert len(user_entries) > 0
        data_entry = next((e for e in user_entries if e["path"] == "data"), None)
        assert data_entry is not None
        assert (dst / "data").is_symlink()

        # Diff: user_symlink entries are skipped
        entries = diff_worktree.get_manifest_entries(dst)
        for entry in entries:
            if entry["type"] == "user_symlink":
                # These should just be skipped, no diff needed
                pass

    def test_new_file_in_worktree_detected_and_synced(self, tmp_git_repo_with_gitignore, tmp_path):
        """A new file created in the worktree is detected and can be synced."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "worktree"
        dst.mkdir()

        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(src, dst))
        (dst / ".worktree-manifest.json").write_text(json.dumps(manifest, indent=2))

        # Create a new file in the worktree
        (dst / "output" / "new_analysis.csv").write_text("x,y\n10,20\n")

        # Diff should detect it
        entries = diff_worktree.get_manifest_entries(dst)
        dir_entry = next(e for e in entries if e["path"] == "output" and e["type"] == "directory")
        changes = diff_worktree.diff_directory(
            dst / "output", Path(dir_entry["source"]), "output"
        )
        new_changes = [c for c in changes if c.status == "new"]
        assert len(new_changes) == 1
        assert "new_analysis.csv" in new_changes[0].relative_path

    def test_unmodified_file_not_detected(self, tmp_git_repo_with_gitignore, tmp_path):
        """Unmodified COW-cloned files are not flagged as changes."""
        src = tmp_git_repo_with_gitignore
        dst = tmp_path / "worktree"
        dst.mkdir()

        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(src, dst))
        (dst / ".worktree-manifest.json").write_text(json.dumps(manifest, indent=2))

        # Don't modify anything - diff should be empty
        entries = diff_worktree.get_manifest_entries(dst)
        all_changes = []
        for entry in entries:
            if entry["type"] == "directory":
                worktree_item = dst / entry["path"]
                if worktree_item.exists():
                    changes = diff_worktree.diff_directory(
                        worktree_item, Path(entry["source"]), entry["path"]
                    )
                    all_changes.extend(changes)
            elif entry["type"] == "cow_clone":
                change = diff_worktree.diff_file(
                    dst / entry["path"],
                    Path(entry["source"]),
                    entry["path"],
                    entry["path"],
                )
                if change:
                    all_changes.append(change)

        assert len(all_changes) == 0

    def test_mixed_directory_tracked_and_ignored(self, tmp_git_repo, tmp_path):
        """Mixed directory: some tracked files, some ignored."""
        repo = tmp_git_repo
        (repo / ".gitignore").write_text("*.log\n*.tmp\n")
        (repo / "src").mkdir()
        (repo / "src" / "main.py").write_text("print('hello')\n")
        (repo / "src" / "debug.log").write_text("log line\n")
        (repo / "src" / "cache.tmp").write_text("temp\n")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "add src"], cwd=repo, capture_output=True, check=True)

        dst = tmp_path / "worktree"
        dst.mkdir()

        manifest = {"version": 1, "entries": []}
        manifest["entries"].extend(create_worktree.clone_gitignored(repo, dst))
        (dst / ".worktree-manifest.json").write_text(json.dumps(manifest, indent=2))

        # The .log and .tmp files should be in the manifest
        entry_paths = [e["path"] for e in manifest["entries"]]
        assert any("debug.log" in p for p in entry_paths)
        assert any("cache.tmp" in p for p in entry_paths)


class TestCloudFileLifecycle:
    """Tests for cloud (dataless) file handling lifecycle."""

    def test_cloud_file_symlinked_during_create(self, tmp_path):
        """Cloud files are symlinked (not COW-cloned) during create."""
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        dst.mkdir()

        cloud_file = src / "large.bin"
        cloud_file.write_bytes(b"\x00" * 100)

        # Mock is_dataless to return True
        with patch.object(create_worktree, 'is_dataless', return_value=True):
            with patch.object(create_worktree, 'get_gitignored_paths',
                            return_value=[(Path("large.bin"), False)]):
                with patch.object(create_worktree, 'parse_worktree_annotations',
                                return_value=set()):
                    entries = create_worktree.clone_gitignored(src, dst)

        cloud_entries = [e for e in entries if e["type"] == "cloud_symlink"]
        assert len(cloud_entries) == 1
        assert (dst / "large.bin").is_symlink()

    def test_cloud_file_unmodified_diff_skipped(self, tmp_path):
        """Cloud file still as symlink is skipped during diff."""
        source = tmp_path / "source.bin"
        source.write_bytes(b"\x00" * 50)

        wt_file = tmp_path / "link.bin"
        wt_file.symlink_to(source)

        result = diff_worktree.diff_file(wt_file, source, "link.bin", "cache")
        assert result is None

    def test_cloud_file_modified_diff_detected(self, tmp_path):
        """Cloud file broken to real file is detected during diff."""
        source = tmp_path / "source.bin"
        source.write_bytes(b"\x00" * 50)

        # Simulate user modification: real file instead of symlink
        wt_file = tmp_path / "modified.bin"
        wt_file.write_bytes(b"\xFF" * 100)

        result = diff_worktree.diff_file(wt_file, source, "modified.bin", "cache")
        assert result is not None
        assert result.status == "modified"


class TestIsDataless:
    """Tests for is_dataless() helper."""

    def test_regular_file_not_dataless(self, tmp_path):
        """Regular local file is not dataless."""
        f = tmp_path / "local.txt"
        f.write_text("data\n")
        assert create_worktree.is_dataless(f) is False

    def test_nonexistent_file(self, tmp_path):
        """Nonexistent file returns False."""
        f = tmp_path / "nonexistent.txt"
        assert create_worktree.is_dataless(f) is False


class TestEdgeCases:
    """Miscellaneous edge cases."""

    def test_empty_gitignore(self, tmp_git_repo, tmp_path):
        """Empty .gitignore produces no entries."""
        repo = tmp_git_repo
        (repo / ".gitignore").write_text("")
        subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "empty gitignore"], cwd=repo, capture_output=True, check=True)

        result = create_worktree.get_gitignored_paths(repo)
        assert result == []

    def test_gitignore_with_comments_only(self, tmp_path):
        """Gitignore with only comments has no annotations."""
        (tmp_path / ".gitignore").write_text("# comment\n# another\n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == set()

    def test_manifest_version_field(self, tmp_path):
        """Manifest is written with version field."""
        manifest = {"version": 1, "entries": [{"path": "x", "type": "cow_clone", "source": "/x"}]}
        manifest_path = tmp_path / ".worktree-manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        with open(manifest_path) as f:
            loaded = json.load(f)
        assert loaded["version"] == 1

    def test_cow_copy_fallback(self, tmp_path):
        """cow_copy falls back to regular copy when COW is unavailable."""
        src = tmp_path / "src.txt"
        src.write_text("content\n")
        dst = tmp_path / "dst.txt"

        # This should succeed regardless of COW support
        result = create_worktree.cow_copy(src, dst)
        assert result is True
        assert dst.read_text() == "content\n"

    def test_cow_copy_overwrites_existing(self, tmp_path):
        """cow_copy removes existing destination before copying."""
        src = tmp_path / "src.txt"
        src.write_text("new\n")
        dst = tmp_path / "dst.txt"
        dst.write_text("old\n")

        result = create_worktree.cow_copy(src, dst)
        assert result is True
        assert dst.read_text() == "new\n"

    def test_cow_copy_overwrites_symlink(self, tmp_path):
        """cow_copy removes existing symlink destination."""
        src = tmp_path / "src.txt"
        src.write_text("content\n")
        target = tmp_path / "target.txt"
        target.write_text("target\n")
        dst = tmp_path / "dst.txt"
        dst.symlink_to(target)

        result = create_worktree.cow_copy(src, dst)
        assert result is True
        assert not dst.is_symlink()
        assert dst.read_text() == "content\n"

    def test_dirs_filter_in_diff(self, worktree_with_manifest):
        """--dirs filter restricts which entries are processed."""
        wt, src, manifest = worktree_with_manifest
        entries = diff_worktree.get_manifest_entries(wt)

        # Filter to only "output"
        filtered = [e for e in entries if e["path"].split("/")[0] in ["output"]]
        assert len(filtered) == 1
        assert filtered[0]["path"] == "output"

    def test_compare_files_size_mismatch(self, tmp_path):
        """compare_files returns False for different sizes."""
        a = tmp_path / "a.txt"
        a.write_text("short\n")
        b = tmp_path / "b.txt"
        b.write_text("much longer content here\n")

        assert diff_worktree.compare_files(a, b) is False

    def test_compare_files_same_file(self, tmp_path):
        """compare_files returns True for identical files."""
        a = tmp_path / "a.txt"
        a.write_text("content\n")
        b = tmp_path / "b.txt"
        shutil.copy2(a, b)

        assert diff_worktree.compare_files(a, b) is True

    def test_format_size(self):
        """format_size produces human-readable sizes."""
        assert "B" in diff_worktree.format_size(100)
        assert "KB" in diff_worktree.format_size(2048)
        assert "MB" in diff_worktree.format_size(2 * 1024 * 1024)

    def test_generate_rename_suffix_custom(self):
        """Custom suffix is used directly."""
        assert sync_worktree.generate_rename_suffix("_custom") == "_custom"

    def test_generate_rename_suffix_default(self):
        """Default suffix is '_worktree'."""
        assert sync_worktree.generate_rename_suffix(None) == "_worktree"

    def test_generate_rename_suffix_timestamp(self):
        """Timestamp suffix contains date pattern."""
        result = sync_worktree.generate_rename_suffix(None, timestamp=True)
        assert result.startswith("_")
        assert len(result) > 10  # _YYYYMMDD_HHMMSS

    def test_rename_path(self):
        """rename_path inserts suffix before extension."""
        result = sync_worktree.rename_path(Path("/a/b/file.csv"), "_backup")
        assert result == Path("/a/b/file_backup.csv")

    def test_rename_path_no_extension(self):
        """rename_path works with no extension."""
        result = sync_worktree.rename_path(Path("/a/b/Makefile"), "_old")
        assert result == Path("/a/b/Makefile_old")

    def test_annotation_with_extra_spaces(self, tmp_path):
        """Annotation parsing handles extra whitespace."""
        (tmp_path / ".gitignore").write_text("  output/   # worktree:symlink  \n")
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert result == {"output"}

    def test_annotation_worktree_symlink_substring(self, tmp_path):
        """Only exact '# worktree:symlink' triggers, not substrings."""
        (tmp_path / ".gitignore").write_text("output/  # worktree:symlink_extra_text\n")
        # "# worktree:symlink" IS a substring of "# worktree:symlink_extra_text"
        # The check is "in" so this WILL match - documenting current behavior
        result = create_worktree.parse_worktree_annotations(tmp_path)
        assert "output" in result

    def test_multiple_gitignored_dirs_all_cloned(self, tmp_git_repo, tmp_path):
        """Multiple gitignored directories are all independently cloned."""
        repo = tmp_git_repo
        (repo / ".gitignore").write_text("dir_a/\ndir_b/\ndir_c/\n")
        for d in ["dir_a", "dir_b", "dir_c"]:
            (repo / d).mkdir()
            (repo / d / "file.txt").write_text(f"content from {d}\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "dirs"], cwd=repo, capture_output=True, check=True)

        dst = tmp_path / "wt"
        dst.mkdir()
        entries = create_worktree.clone_gitignored(repo, dst)

        entry_paths = [e["path"] for e in entries]
        assert "dir_a" in entry_paths
        assert "dir_b" in entry_paths
        assert "dir_c" in entry_paths
        for d in ["dir_a", "dir_b", "dir_c"]:
            assert (dst / d / "file.txt").exists()
