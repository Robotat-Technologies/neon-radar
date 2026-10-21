"""api/Dockerfile installs the dependencies from the workspace manifests before it copies the
repository (M1.9e), so it must copy every member's pyproject.toml: `uv sync --locked` fails on
a member it cannot see."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_api_image_copies_every_workspace_manifest() -> None:
    workspace = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    members = set(workspace["tool"]["uv"]["workspace"]["members"])
    dockerfile = (ROOT / "api" / "Dockerfile").read_text(encoding="utf-8")
    copied = set(re.findall(r"^COPY ([a-z][a-z0-9_-]*)/pyproject\.toml \1/$", dockerfile, re.M))
    assert copied == members
