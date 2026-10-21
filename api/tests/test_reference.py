"""Meta, typologies, NR_REPO_ROOT and the offline docs page, without a database (M1.9c)."""

import base64
import hashlib
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from neonradar_api import docs_page
from neonradar_api.files import RepoFiles, find_workspace_root
from neonradar_api.main import create_app
from neonradar_contracts.api import MetaResponse, Problem, TypologyDetail, TypologySummary
from neonradar_contracts.datasets import load_registry
from neonradar_contracts.wording import load_disclaimer
from neonradar_detect.catalog import load_catalog

from .conftest import REPO_ROOT, OfflineGraph

P = "/api/v1"


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(OfflineGraph(), RepoFiles(REPO_ROOT))
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_meta_answers_without_neo4j(client: TestClient) -> None:
    response = client.get(f"{P}/meta")
    assert response.status_code == 200
    meta = MetaResponse.model_validate_json(response.text)
    assert [d.slug for d in meta.datasets] == [d.slug for d in load_registry().datasets]
    assert {d.record_count for d in meta.datasets} == {None}
    assert (meta.counts.nodes_by_label, meta.counts.relationships_by_type) == ({}, {})
    assert meta.disclaimers.standing == load_disclaimer("standing-v1")
    assert meta.disclaimers.synthetic_demo == load_disclaimer("synthetic-demo-v1")
    assert meta.disclaimers.real_data == load_disclaimer("real-data-v1")
    assert (meta.contracts_version, meta.schema_version) == ("1.0.0", "1.0.0")


def test_typologies_come_from_the_catalog_sorted_by_slug(client: TestClient) -> None:
    catalog = load_catalog()
    response = client.get(f"{P}/typologies")
    items = [TypologySummary.model_validate(item) for item in response.json()]
    assert [item.slug for item in items] == sorted(catalog)
    for item in items:
        assert item.detector_available == (catalog[item.slug].detector is not None)
        assert item.status == catalog[item.slug].status


def test_a_typology_has_its_explainer_and_citations_in_file_order(client: TestClient) -> None:
    typology = load_catalog()["circular_flow"]
    detail = TypologyDetail.model_validate_json(client.get(f"{P}/typologies/circular_flow").text)
    explainer = (REPO_ROOT / typology.doc).read_text(encoding="utf-8")
    assert detail.definition_markdown == explainer
    bibliography = yaml.safe_load(
        (REPO_ROOT / "docs" / "sources" / "bibliography.yaml").read_text(encoding="utf-8")
    )
    known = {entry["key"]: entry for entry in bibliography["entries"]}
    assert [c.key for c in detail.citations] == [k for k in typology.citations if k in known]
    assert all(c.url == known[c.key]["url"] for c in detail.citations)
    assert detail.parameters["max_window_days"] == {"default": 14, "min": 1, "max": 90}
    assert detail.false_positives == typology.false_positives


def test_an_unknown_typology_is_a_404_problem(client: TestClient) -> None:
    response = client.get(f"{P}/typologies/no_such_typology")
    assert response.status_code == 404
    assert Problem.model_validate_json(response.text).detail == "No typology has this slug."


def test_the_repository_root_comes_from_nr_repo_root_or_the_uv_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert find_workspace_root(REPO_ROOT / "api" / "src") == REPO_ROOT
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert find_workspace_root(tmp_path) is None
    monkeypatch.setenv("NR_REPO_ROOT", str(REPO_ROOT))
    assert RepoFiles().root == REPO_ROOT
    monkeypatch.delenv("NR_REPO_ROOT")
    monkeypatch.chdir(tmp_path)
    for setting in (None, str(tmp_path / "missing"), str(tmp_path)):  # unset, absent, wrong
        if setting is not None:
            monkeypatch.setenv("NR_REPO_ROOT", setting)
        with TestClient(create_app(OfflineGraph()), raise_server_exceptions=False) as client:
            typologies = client.get(f"{P}/typologies")
            meta = client.get(f"{P}/meta")
        assert typologies.status_code == 500
        detail = Problem.model_validate_json(typologies.text).detail
        assert detail == "The repository files were not found: set NR_REPO_ROOT."
        # /meta reads the contract files from the contracts package, never from NR_REPO_ROOT.
        assert meta.status_code == 200
        assert MetaResponse.model_validate_json(meta.text).disclaimers.standing == (
            load_disclaimer("standing-v1")
        )


def test_an_explainer_outside_docs_typologies_is_not_served(tmp_path: Path) -> None:
    for part in ("detect/typologies", "docs/typologies", "docs/sources"):
        (tmp_path / part).mkdir(parents=True)
    for part in ("detect/typologies/circular_flow.yaml", "docs/sources/bibliography.yaml"):
        (tmp_path / part).write_bytes((REPO_ROOT / part).read_bytes())
    outside = tmp_path / "outside.md"
    outside.write_text("not an explainer", encoding="utf-8")
    (tmp_path / "docs" / "typologies" / "circular-flow.md").symlink_to(outside)
    app = create_app(OfflineGraph(), RepoFiles(tmp_path))
    with TestClient(app) as client:
        detail = TypologyDetail.model_validate_json(
            client.get(f"{P}/typologies/circular_flow").text
        )
    assert detail.definition_markdown is None
    assert detail.citations  # the bibliography still resolves


def _hash(text: str) -> str:
    return base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def test_the_offline_docs_page_loads_nothing_from_elsewhere(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    policy = response.headers["content-security-policy"]
    assert "default-src 'none'" in policy and "connect-src 'self'" in policy
    style = re.search(r"<style>(.*)</style>", response.text, re.DOTALL)
    script = re.search(r"<script>(.*)</script>", response.text, re.DOTALL)
    assert style and script
    assert f"style-src 'sha256-{_hash(style[1])}'" in policy
    assert f"script-src 'sha256-{_hash(script[1])}'" in policy
    assert not re.search(r"https?://|//[a-z]", response.text)  # no absolute or protocol URL
    assert "/docs" not in client.get(f"{P}/openapi.json").json()["paths"]
    assert response.text == docs_page.PAGE
