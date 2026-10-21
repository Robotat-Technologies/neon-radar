"""Helpers shared by the pull request hygiene scripts (docs/build/PHASE-1.md M1.6).

Standard library only: the scripts run on the CI runner's system Python 3.12.
"""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class GitError(RuntimeError):
    """A git command failed."""


def git(root: Path, *args: str) -> str:
    """Run git in `root` and return its standard output; raise GitError on failure."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def git_succeeds(root: Path, *args: str) -> bool:
    """Run git in `root` and say whether it exited 0 (for checks such as rev-parse --verify)."""
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    return result.returncode == 0


def changed_paths(root: Path, base: str) -> list[str]:
    """Paths touched by `base...HEAD`; a rename lists both the old and the new path."""
    output = git(root, "diff", "--name-only", "--no-renames", "-z", f"{base}...HEAD")
    return [path for path in output.split("\0") if path]


def parse_labels(value: str) -> list[str]:
    """Labels from a JSON array (`toJson` in a workflow) or a comma-separated list."""
    value = value.strip()
    if not value:
        return []
    if value.startswith("["):
        data = json.loads(value)
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            raise ValueError(f"labels must be a JSON array of strings, got {value!r}")
        items = data
    else:
        items = value.split(",")
    return [item.strip() for item in items if item.strip()]


def annotate(level: str, message: str) -> None:
    """Print a message; inside GitHub Actions also as an annotation (`error` or `warning`)."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{level}::{message}")
    else:
        print(message)
