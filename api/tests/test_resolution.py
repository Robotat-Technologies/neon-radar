"""Integration: `GET /entities/{entity_id}/resolution` and entity provenance on the resolution
fixture (PHASE-2.md M2.12 deliverable 5).

`fixtures/resolution/` holds seven synthetic records and a hand-written resolution run in the
format of 7.1.8: one entity merged from three records (anchor, D1 member, probabilistic member),
single-record entities, and three possible matches of the merged entity (probabilistic,
deterministic D1 with `identifier_name_mismatch`, and a source hint). The committed
`canonical.csv` starts with the `# synthetic: true` line every committed CSV fixture needs
(scripts/check_fixtures.py); the test loads a copy without it, as `ResolutionMap.load` reads
7.1.8's header first. The texts below are the 7.2 templates rendered for this fixture.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Final

import pytest
from fastapi.testclient import TestClient

from neonradar_api.files import RepoFiles
from neonradar_api.main import create_app
from neonradar_contracts.api import EntityDetail, Problem, ResolutionResponse
from neonradar_graph.loader import load_files, wipe
from neonradar_graph.migrate import migrate

from .conftest import REPO_ROOT, SessionGraph

pytestmark = pytest.mark.integration

P: Final = "/api/v1"
FIXTURE: Final = Path(__file__).resolve().parent / "fixtures" / "resolution"
RUN: Final = "er-20261024T090000-5e1a"
MERGED: Final = "nr-syn-res-co-1"
MEMBERS: Final = [
    (
        "syn-res-co-1",
        "anchor",
        None,
        1.0,
        "Anchor record: the entity takes its id and caption from this NeonRadar synthetic data"
        " record.",
    ),
    ("syn-res-co-2", "deterministic", "D1", 1.0, "Joined by the same UK company number."),
    (
        "syn-res-co-3",
        "probabilistic",
        None,
        0.987,
        "Joined by probabilistic matching (match probability 0.987). Agreeing: same name, same"
        " jurisdiction.",
    ),
]
POSSIBLE_MATCHES: Final = [
    (
        "syn-res-co-5",
        "probabilistic",
        0.912,
        None,
        ["below_merge_threshold"],
        [
            "Agrees: names spelled similarly",
            "Agrees: same jurisdiction",
            "Differs: registration numbers",
        ],
        "Possible match, not confirmed. Probabilistic matching gave 0.912, below the threshold for"
        " merging. Agreeing: names spelled similarly, same jurisdiction. Differing: registration"
        " numbers.",
    ),
    (
        "syn-res-co-6",
        "deterministic",
        None,
        "D1",
        ["identifier_name_mismatch"],
        [],
        "Possible match, not confirmed. Both records give the same UK company number, but the names"
        " differ, so they were not merged.",
    ),
    (
        "syn-res-co-7",
        "source_hint",
        None,
        None,
        ["source_hint:same_name_as"],
        [],
        "Possible match, not confirmed. The ICIJ Offshore Leaks Database marks these records as"
        " having the same name.",
    ),
]


def copy_run(target: Path) -> Path:
    """The fixture run in `target`, its `canonical.csv` without the fixture marker line."""
    run_dir = target / RUN
    shutil.copytree(FIXTURE / RUN, run_dir)
    canonical = run_dir / "canonical.csv"
    lines = canonical.read_text("utf-8").splitlines(keepends=True)
    assert lines[0] == "# synthetic: true\n"
    canonical.write_text("".join(lines[1:]), "utf-8")
    return run_dir


@pytest.fixture(scope="module")
def client(neo4j: Any, tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    wipe(neo4j.driver, neo4j.database)
    migrate(neo4j.driver, neo4j.database)
    run_dir = copy_run(tmp_path_factory.mktemp("resolution"))
    report = load_files(neo4j.driver, [FIXTURE], database=neo4j.database, resolution=run_dir)
    assert not report.failed
    assert (report.merged_entities, report.possible_matches) == (1, 3)
    app = create_app(SessionGraph(neo4j), RepoFiles(REPO_ROOT))
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client


def _resolution(client: TestClient, entity_id: str) -> ResolutionResponse:
    response = client.get(f"{P}/entities/{entity_id}/resolution")
    assert response.status_code == 200, response.text
    return ResolutionResponse.model_validate_json(response.text)


def test_the_merged_entity_lists_its_members_and_possible_matches(client: TestClient) -> None:
    body = _resolution(client, MERGED)
    assert (body.entity_id, body.canonical, body.resolution, body.cluster_size) == (
        MERGED,
        True,
        "mixed",
        3,
    )
    assert (body.run_id, body.resolver_version) == (RUN, "0.1.0")
    members = [
        (m.record_id, m.method, m.rule, m.match_probability, m.explanation) for m in body.members
    ]
    assert members == MEMBERS
    assert {m.decided_at for m in body.members} == {"2026-10-24T09:00:00Z"}
    assert {m.dataset for m in body.members} == {"nr_synthetic"}
    matches = [
        (m.entity.id, m.method, m.match_probability, m.rule, m.reasons, m.evidence, m.explanation)
        for m in body.possible_matches
    ]
    assert matches == POSSIBLE_MATCHES  # the probabilistic one first, then the others by id
    assert all("not confirmed" in m.explanation for m in body.possible_matches)


def test_a_member_record_id_resolves_to_its_entity(client: TestClient) -> None:
    assert _resolution(client, "syn-res-co-2").entity_id == MERGED
    detail = client.get(f"{P}/entities/syn-res-co-3")
    assert detail.status_code == 200, detail.text
    body = EntityDetail.model_validate_json(detail.text)
    assert body.entity.id == MERGED
    assert [(p.record_id, p.dataset) for p in body.provenance] == [
        (record_id, "nr_synthetic") for record_id, *_ in MEMBERS
    ]


def test_a_single_record_entity_has_one_identity_member(client: TestClient) -> None:
    body = _resolution(client, "syn-res-co-4")
    assert (body.canonical, body.resolution, body.cluster_size) == (False, "identity", 1)
    assert [(m.record_id, m.method, m.rule, m.match_probability) for m in body.members] == [
        ("syn-res-co-4", "identity", None, None)
    ]
    assert body.members[0].explanation == "Built from one source record (NeonRadar synthetic data)."
    assert body.possible_matches == []
    detail = EntityDetail.model_validate_json(client.get(f"{P}/entities/syn-res-co-4").text)
    assert [p.record_id for p in detail.provenance] == ["syn-res-co-4"]


def test_a_possible_match_is_seen_from_both_sides(client: TestClient) -> None:
    body = _resolution(client, "syn-res-co-6")
    assert [(m.entity.id, m.method, m.rule) for m in body.possible_matches] == [
        (MERGED, "deterministic", "D1")
    ]
    assert body.run_id == RUN


def test_an_unknown_id_is_a_404_problem(client: TestClient) -> None:
    response = client.get(f"{P}/entities/syn-res-co-99/resolution")
    assert response.status_code == 404, response.text
    assert Problem.model_validate_json(response.text).detail == "No entity has this id."
