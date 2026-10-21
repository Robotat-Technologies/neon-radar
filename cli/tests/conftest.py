from pathlib import Path

import pytest

from neonradar_graph import client


@pytest.fixture(autouse=True)
def no_compose_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Inside the devcontainer /run/secrets/neo4j_password exists; the tests never read it."""
    monkeypatch.setattr(client, "SECRETS_DIR", tmp_path / "no-secrets")
