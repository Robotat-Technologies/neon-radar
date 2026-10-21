"""The repository files the typology routes read (PHASE-1.md M1.9c; contracts/C3-api.md).

`detect/typologies/` (`load_catalog()`), `docs/typologies/` (the explainers) and
`docs/sources/bibliography.yaml` (`Citation` titles and links) are found from one setting,
`NR_REPO_ROOT`. Its default is the nearest directory, from the working directory up, whose
`pyproject.toml` has a `[tool.uv.workspace]` table; M1.9e's image sets it to `/app`. The
setting comes from the environment only: it locates the repository, so it cannot come from the
repository's `.env`. Nothing is read until a route needs it, so `create_app()` (and the OpenAPI
export) works anywhere. The contract files `GET /meta` serves (the dataset registry and the
disclaimers) come from the contracts package itself (`load_registry()`, `load_disclaimer()`),
so `/meta` never depends on this setting.
"""

import tomllib
from functools import cached_property
from pathlib import Path
from typing import Any, Final

import yaml
from fastapi import Request
from pydantic_settings import BaseSettings, SettingsConfigDict

from neonradar_contracts.api import Citation
from neonradar_detect.catalog import TypologyFile, load_catalog


class RepoRootNotFound(RuntimeError):
    """No usable repository: `NR_REPO_ROOT` names no NeonRadar checkout, or it is unset and no
    uv workspace lies above the working directory (HTTP 500 on the typology routes)."""


class ApiSettings(BaseSettings):
    """`NR_REPO_ROOT`, from the environment only."""

    model_config = SettingsConfigDict(env_prefix="NR_", extra="ignore")

    repo_root: Path | None = None


def find_workspace_root(start: Path) -> Path | None:
    """The nearest directory, `start` included, whose pyproject.toml has [tool.uv.workspace]."""
    for directory in (start, *start.parents):
        pyproject = directory / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            tool: Any = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {})
        except tomllib.TOMLDecodeError:
            continue
        if isinstance(tool.get("uv", {}).get("workspace"), dict):
            return directory
    return None


# What NR_REPO_ROOT must hold.
EXPECTED: Final = ("detect/typologies", "docs/typologies", "docs/sources/bibliography.yaml")


class RepoFiles:
    """Reads the files on each call, so an edited typology file shows without a restart."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root

    @cached_property
    def root(self) -> Path:
        """The repository; it must hold the typology catalog, the explainers and the
        bibliography, so a wrong or missing directory gives the same hint as no setting."""
        root = self._root or ApiSettings().repo_root or find_workspace_root(Path.cwd())
        if root is None or not all((root / part).exists() for part in EXPECTED):
            raise RepoRootNotFound("set NR_REPO_ROOT to the NeonRadar repository")
        return root

    def catalog(self) -> dict[str, TypologyFile]:
        return load_catalog(self.root / "detect" / "typologies")

    def explainer(self, typology: TypologyFile) -> str | None:
        """The typology's explainer Markdown (`doc`), or None when the file does not exist or
        resolves outside `docs/typologies/` (through a symbolic link, for example)."""
        folder = (self.root / "docs" / "typologies").resolve()
        path = (self.root / typology.doc).resolve()
        if not path.is_relative_to(folder) or not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def citations(self, keys: list[str]) -> list[Citation]:
        """The bibliography entries of `keys`, in that order; unknown keys are left out."""
        path = self.root / "docs" / "sources" / "bibliography.yaml"
        entries = yaml.safe_load(path.read_text(encoding="utf-8")).get("entries") or []
        by_key = {entry["key"]: entry for entry in entries}
        return [
            Citation(
                key=key,
                title=str(entry["title"]),
                publisher=str(entry["publisher"]),
                year=entry.get("year"),
                url=str(entry["url"]),
            )
            for key in keys
            if (entry := by_key.get(key)) is not None
        ]


def get_files(request: Request) -> RepoFiles:
    """FastAPI dependency: the app's repository files (tests pass their own)."""
    files: RepoFiles = request.app.state.files
    return files
