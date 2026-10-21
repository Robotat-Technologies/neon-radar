"""Shared fixtures for the hygiene script tests: a throwaway git repository.

The repository lives under tmp_path and ignores the user's and the system's git
configuration, so signing, hooks and aliases on a developer machine cannot change the result.
No test runs git in the real repository.
"""

import os
import subprocess
from pathlib import Path

import pytest


class GitRepo:
    def __init__(self, path: Path) -> None:
        self.path = path

    def run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.path, capture_output=True, text=True, check=True
        )
        return result.stdout

    def write(self, relative: str, content: str | bytes) -> Path:
        path = self.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def move(self, source: str, target: str) -> None:
        (self.path / target).parent.mkdir(parents=True, exist_ok=True)
        self.run("mv", source, target)

    def commit(self, message: str) -> None:
        self.run("add", "-A")
        self.run("commit", "-q", "-m", message)


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """A repository on branch main with one commit (README.md)."""
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Hygiene Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "hygiene-test@example.invalid")
    repo = GitRepo(tmp_path / "repo")
    repo.path.mkdir()
    repo.run("init", "-q", "-b", "main")
    repo.write("README.md", "seed\n")
    repo.commit("seed")
    return repo
