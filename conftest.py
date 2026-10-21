"""Repository-wide pytest setup. The shared Neo4j of the integration tests is a plugin
registered here once, so every suite (graph, detect, api) uses one database per session:
graph/tests/support/nr_test_neo4j.py (on the test path through pyproject.toml).

`data_env` (ingest and cli tests of the data manager, PHASE-2.md M2.2) points every data
manager folder, the profiles, the project file and `.env` at a temporary tree."""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

pytest_plugins = ["nr_test_neo4j"]

SYNTHETIC_ONLY = {"real_data_profiles": [], "data_protection_filed": False}


@dataclass(frozen=True)
class DataEnv:
    root: Path
    cache: Path
    profiles: Path
    project: Path
    env_file: Path

    def write_project(self, **access: Any) -> Path:
        """A project file with `access` (Phase 2 defaults otherwise, as in OD-22)."""
        values = {"sanctions_lists": ["gb_fcdo_sanctions", "us_ofac_sdn", "eu_fsf"]}
        data = {"people": {"er_labellers": ["@TODO"]}, "access": {**values, **access}}
        self.project.write_text(yaml.safe_dump(data), encoding="utf-8")
        return self.project

    def write_profile(self, name: str, *, real_data: bool, sources: dict[str, Any]) -> None:
        data = {
            "profile": name,
            "description": "A test profile.",
            "real_data": real_data,
            "sources": sources,
            "resolution": {"enabled": False, "config": "resolve/config/er.yaml"},
        }
        (self.profiles / f"{name}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")

    def approve_machine(self, approved: bool = True) -> None:
        value = "approved" if approved else ""
        self.env_file.write_text(f"NR_REAL_DATA_MACHINE={value}\n", encoding="utf-8")

    def allow_real(self, profile: str, **access: Any) -> None:
        """Every gate condition passes for `profile` (synthetic test inputs only)."""
        self.write_project(real_data_profiles=[profile], data_protection_filed=True, **access)
        self.approve_machine()


def _no_network(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("tests never use the network: give the client an httpx.MockTransport")


@pytest.fixture
def data_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DataEnv:
    import httpx

    from neonradar_ingest.data import gate, layout, profiles

    env = DataEnv(
        tmp_path,
        tmp_path / "data" / "cache",
        tmp_path / "profiles",
        tmp_path / "project.yaml",
        tmp_path / ".env",
    )
    shutil.copytree(profiles.PROFILES_DIR, env.profiles)  # the committed profiles
    monkeypatch.setattr(profiles, "PROFILES_DIR", env.profiles)
    monkeypatch.setattr(layout, "CACHE_ROOT", env.cache)
    monkeypatch.setattr(gate, "ENV_FILE", env.env_file)
    monkeypatch.setenv("NR_PROJECT_FILE", str(env.project))
    for name in ("CI", "CODESPACES", "NR_REAL_DATA_MACHINE"):
        monkeypatch.delenv(name, raising=False)
    # Only httpx.MockTransport may answer: the real transports refuse every request.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _no_network)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _no_network)
    env.write_project(**SYNTHETIC_ONLY)
    return env
