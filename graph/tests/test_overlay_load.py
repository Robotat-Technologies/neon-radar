"""Integration: overlay loads, C2 1.2.0 loader rule L18 (PHASE-3.md M3.4 deliverable 5, 5.4).

synth-demo's world with `companies: 40` and its overlay, generated at run time and never
committed (2.9): the overlay loads onto the base with no unresolved reference, again with every
count unchanged, and only HOLDS_ACCOUNT from a base organisation joins a base node and an
overlay node; a holder the graph lacks, and a holder that is not an organisation, stop the load
before anything is written (exit 1). On the resolved Phase 2 demo load, a holding of a merged
record lands on its canonical node. Doctored overlays (exit 2 before connecting) are in
test_overlay_check.py.

A second container started like `neo4j-real` holds test look-alikes (registry companies, a
person and a listed legal entity of unstated kind) as Instance.REAL: it takes an overlay only for
a profile in the list the loader gets, I15 and I16 hold, and a detection run through
Neo4jSource withholds the cycle through a look-alike's account, names no look-alike person and
rests no alert on a look-alike on a payment, so I17 holds (R-REAL on Neo4j, which the detector
tests cannot reach because L17 refuses mixed loads)."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from neonradar_detect.runs import detect_on_graph
from neonradar_graph import loader
from neonradar_graph.client import REPO_ROOT
from neonradar_graph.instances import REAL_DATABASE, Instance
from neonradar_graph.loader import LoadReport, load_files
from neonradar_graph.overlay import OverlayInstanceRefused, OverlayUnresolved, load_overlay
from neonradar_graph.verify import verify
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.synth import overlay, world
from neonradar_ingest.synth.namesource import default_names

from .conftest import DEMO_DIRS, Neo4jTarget, record
from .test_loader_resolution import counts, query

pytestmark = pytest.mark.integration

NONE = {f"I{n}": 0 for n in range(1, 18)}
Records = list[dict[str, Any]]
BASE_NODES = "MATCH (n:Entity) WHERE NOT n.id STARTS WITH 'syn-ov-' RETURN count(n) AS n"
OVERLAY_NODES = (
    "MATCH (n) WHERE (n:Entity OR n:Sanction) AND n.id STARTS WITH 'syn-ov-' RETURN count(n) AS n"
)
# Every relationship between a base node and an overlay node, by type and kind of ends.
BRIDGES = """
MATCH (a:Entity)-[r]->(b:Entity)
WHERE (a.id STARTS WITH 'syn-ov-') <> (b.id STARTS WITH 'syn-ov-')
RETURN DISTINCT type(r) AS type, b.id STARTS WITH 'syn-ov-' AS to_overlay,
       a:Organization AS from_organisation, b:Account AS to_account"""


def write(folder: Path, records: Records, profile: str) -> Path:
    folder.mkdir(parents=True)
    lines = "".join(json.dumps(item) + "\n" for item in records)
    (folder / "records.ftm.jsonl").write_text(lines, encoding="utf-8")
    (folder / "overlay.json").write_text(json.dumps({"profile": profile}), encoding="utf-8")
    return folder


@pytest.fixture(scope="module")
def synth_demo(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """synth-demo's world with 40 companies, and its overlay (the profile's overlay block)."""
    profile = load_profile("synth-demo")
    block, settings = profile.world, profile.overlay
    assert block is not None and settings is not None
    names = default_names()
    base = world.generate(block.seed, replace(block.config(), companies=40), names)
    made = overlay.generate(base, {"nr_synthetic": "synthetic"}, settings.config(block.seed), names)
    root = tmp_path_factory.mktemp("synth-demo")
    return write(root / "world", base, "synth-demo"), write(
        root / "overlay", made.records, "synth-demo"
    )


def holding(owner: str) -> Records:
    """An overlay account that `owner` holds."""
    return [
        record("syn-ov-acct-1", "BankAccount", accountNumber="NRSYN0000000001", currency="GBP"),
        record("syn-ov-own-1", "Ownership", owner=owner, asset="syn-ov-acct-1",
               role="account holder"),
    ]  # fmt: skip


def load(
    db: Neo4jTarget, folder: Path, profile: str = "synth-demo", allowed: tuple[str, ...] = ()
) -> LoadReport:
    instance = Instance.REAL if db.database == REAL_DATABASE else Instance.DEFAULT
    return load_overlay(folder, profile, instance, allowed, driver=db.driver, database=db.database)


def count(db: Neo4jTarget, cypher: str) -> int:
    (row,) = query(db, cypher)
    return int(row["n"])


def test_an_overlay_loads_onto_its_base_and_again_with_the_same_counts(
    graph_db: Neo4jTarget, synth_demo: tuple[Path, Path]
) -> None:
    world_dir, folder = synth_demo
    base = load_files(graph_db.driver, [world_dir], database=graph_db.database)
    assert (base.dangling, base.rejected, base.skipped) == ([], [], [])
    base_nodes = count(graph_db, BASE_NODES)
    first = load(graph_db, folder)
    assert (first.dangling, first.rejected, first.overlay_removed) == ([], [], 0)
    assert first.relationships_by_type["HOLDS_ACCOUNT"] > 0 and first.overlay_records > 0
    loaded, overlay_nodes = counts(graph_db), count(graph_db, OVERLAY_NODES)
    graph_db.driver.execute_query(
        "CREATE (:Alert {alert_id: 'alr-00000000000000000000'})", database_=graph_db.database
    )
    second = load(graph_db, folder)  # L18 step 4 removes the alert and the first overlay
    assert (second.overlay_removed, second.detection_results_removed) == (overlay_nodes, 1)
    assert counts(graph_db) == loaded and count(graph_db, BASE_NODES) == base_nodes
    assert verify(graph_db.driver, graph_db.database) == NONE
    assert query(graph_db, BRIDGES) == [
        {"type": "HOLDS_ACCOUNT", "to_overlay": True, "from_organisation": True, "to_account": True}
    ]


def test_a_holder_the_graph_lacks_or_that_is_no_organisation_stops_before_writing(
    graph_db: Neo4jTarget, synth_demo: tuple[Path, Path], tmp_path: Path
) -> None:
    load_files(graph_db.driver, [synth_demo[0]], database=graph_db.database)
    (person,) = query(graph_db, "MATCH (p:Person) RETURN p.id AS id ORDER BY id LIMIT 1")
    before = counts(graph_db)
    for n, holder in enumerate(["syn-co-0000009999", person["id"]]):
        with pytest.raises(OverlayUnresolved) as stopped:
            load(graph_db, write(tmp_path / str(n), holding(holder), "synth-demo"))
        assert stopped.value.exit_code == 1 and counts(graph_db) == before


def test_a_holding_of_a_merged_record_lands_on_its_canonical_node(
    graph_db: Neo4jTarget, demo_resolution: Path, tmp_path: Path
) -> None:
    load_files(graph_db.driver, DEMO_DIRS, database=graph_db.database, resolution=demo_resolution)
    (merged,) = query(
        graph_db,
        "MATCH (e:Organization) WHERE e.cluster_size >= 2 AND size(e.topics) = 0"
        " RETURN e.id AS id, e.referents[0] AS member ORDER BY id LIMIT 1",
    )
    report = load(graph_db, write(tmp_path / "overlay", holding(merged["member"]), "demo"), "demo")
    assert (report.resolved_through_source_record, report.dangling) == (1, [])
    holders = query(
        graph_db,
        "MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(:Entity {id: 'syn-ov-acct-1'}) RETURN h.id AS id",
    )
    assert holders == [{"id": merged["id"]}] and merged["member"] != merged["id"]
    assert verify(graph_db.driver, graph_db.database) == NONE


# Look-alikes of real records, built here (names already used by the graph and detect tests).
HOLDER = "gbch-co-T0000001"
LOOK_ALIKES = [
    record(HOLDER, "Company", name="Test Holder Ltd", jurisdiction="gb"),
    record("gbch-co-T0000005", "Company", name="Test Trading Ltd", jurisdiction="gb"),
    record("gbch-psc-T00000011", "Person", name="Test Person"),
    record("gbch-ownership-T1", "Ownership", owner="gbch-psc-T00000011", asset=HOLDER),
    {
        **record("ofac-T0000001", "LegalEntity", name="Test Listed Entity", topics="sanction"),
        "datasets": ["us_ofac_sdn"],
    },
    record("gbch-ownership-T5", "Ownership", owner="ofac-T0000001", asset="gbch-co-T0000005"),
]
PEOPLE = {"gbch-psc-T00000011", "ofac-T0000001"}  # a person, a legal entity of unstated kind
CASES = REPO_ROOT / "detect" / "tests" / "fixtures" / "circular_flow" / "cases.ftm.jsonl"


def case_f() -> Records:
    """detect's circular-flow fixture as an overlay (`syn-` ids become `syn-ov-`), with case A's
    origin account held by the look-alike company, as detect's case F."""
    origin = "syn-ov-acct-cfa1"
    text = CASES.read_text(encoding="utf-8").replace('"syn-', '"syn-ov-')
    records: Records = [json.loads(line) for line in text.splitlines() if line.strip()]
    for item in records:
        props = item["properties"]
        if item["schema"] == "Ownership" and props["asset"] == [origin]:
            props["owner"] = [HOLDER]
        for party in ("payer", "beneficiary"):
            if item["schema"] == "Payment" and props[f"{party}Account"] == [origin]:
                props[party] = [HOLDER]
    return records


def test_the_real_data_instance_takes_a_listed_overlay_and_r_real_holds(
    real_neo4j: Neo4jTarget, tmp_path: Path
) -> None:
    base = tmp_path / "base"
    base.mkdir()
    lines = "".join(json.dumps(item) + "\n" for item in LOOK_ALIKES)
    (base / "look-alikes.ftm.jsonl").write_text(lines, encoding="utf-8")
    loaded = loader.load([base], instance=Instance.REAL, driver=real_neo4j.driver)
    assert (loaded.dangling, loaded.rejected) == ([], [])
    records = case_f()
    folder = write(tmp_path / "overlay", records, "uk-tiny")
    before = counts(real_neo4j)
    with pytest.raises(OverlayInstanceRefused):  # uk-tiny is not in the list the loader gets
        load(real_neo4j, folder, "uk-tiny")
    assert counts(real_neo4j) == before
    report = load(real_neo4j, folder, "uk-tiny", ("uk-tiny",))
    assert report.dangling == [] and report.relationships_by_type["PAID"] > 0
    assert verify(real_neo4j.driver, REAL_DATABASE) == NONE  # I15 and I16 among them
    run = detect_on_graph(real_neo4j.driver, REAL_DATABASE, runs_dir=tmp_path / "runs")
    assert sum(run.summary["withheld"].values()) > 0 and run.alerts
    payments = {item["id"] for item in records if item["schema"] == "Payment"}
    look_alikes = {item["id"] for item in LOOK_ALIKES}
    for alert in run.alerts:
        named = {subject.entity_id for subject in alert.subjects} | set(alert.evidence.node_ids)
        assert not named & PEOPLE
        assert not (named & look_alikes and payments & set(alert.evidence.edge_ids))
    assert verify(real_neo4j.driver, REAL_DATABASE)["I17"] == 0
