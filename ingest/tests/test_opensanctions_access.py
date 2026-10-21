"""The OpenSanctions licence gate (PHASE-1.md 1.2 and M1.8d, guardrails G2 and G7)."""

from pathlib import Path

import pytest

from neonradar_ingest.sources.opensanctions import access
from neonradar_ingest.sources.opensanctions.access import (
    REFUSAL,
    Access,
    LicenceRequired,
    may_write,
    read_access,
    require_access,
)


def _project(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "project.yaml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("value", ["none", "evaluation", "licensed", "exempt"])
def test_reads_each_route(tmp_path: Path, value: str) -> None:
    project = _project(tmp_path, f"access:\n  opensanctions: {value}   # comment\n")
    assert read_access(project) is Access(value)


@pytest.mark.parametrize(
    "text",
    [
        "access:\n  opensanctions: TODO\n",
        "access:\n  opensanctions: no\n",  # YAML false
        "access:\n  opensanctions:\n",
        "access:\n  companies_house_key: pending\n",
        "access: none\n",
        "- a list\n",
        "access: [unclosed\n",
    ],
)
def test_anything_else_counts_as_none(tmp_path: Path, text: str) -> None:
    assert read_access(_project(tmp_path, text)) is Access.NONE


def test_a_missing_file_counts_as_none(tmp_path: Path) -> None:
    assert read_access(tmp_path / "missing.yaml") is Access.NONE


def test_default_is_the_repository_project_file(monkeypatch: pytest.MonkeyPatch) -> None:
    assert access.PROJECT_FILE.parts[-3:] == ("docs", "build", "project.yaml")
    assert access.PROJECT_FILE.is_file()
    monkeypatch.setattr(access, "PROJECT_FILE", Path("/nonexistent/project.yaml"))
    assert read_access() is Access.NONE


def test_none_refuses_with_the_spec_message() -> None:
    with pytest.raises(LicenceRequired) as caught:
        require_access(Access.NONE)
    assert str(caught.value) == REFUSAL
    assert REFUSAL == (
        "OpenSanctions use inside a company needs a data licence; see DATA_SOURCES.md"
    )


def test_evaluation_needs_the_written_confirmation_on_file(tmp_path: Path) -> None:
    confirmation = tmp_path / "opensanctions.md"
    with pytest.raises(LicenceRequired, match="written confirmation is not filed"):
        require_access(Access.EVALUATION, confirmation)
    confirmation.write_text("OpenSanctions' answer", encoding="utf-8")
    require_access(Access.EVALUATION, confirmation)


@pytest.mark.parametrize("route", [Access.LICENSED, Access.EXEMPT])
def test_licensed_and_exempt_may_fetch(tmp_path: Path, route: Access) -> None:
    require_access(route, tmp_path / "missing.md")


def test_only_licensed_access_writes() -> None:
    assert [route for route in Access if may_write(route)] == [Access.LICENSED]
