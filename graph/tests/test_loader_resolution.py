"""Integration: the resolution-aware loader on Neo4j 5.26 (PHASE-2.md M2.11 deliverable 7, C2
L8 to L17). The demo profile's records are resolved once per session (`demo_resolution`,
deterministic rules only) and loaded: every invariant holds, a second load changes no count,
one merged entity follows 7.1.6 property by property, every line of `candidates.jsonl` gives
one POSSIBLY_SAME_AS, a changed run leaves no superseded node, and a load without a run gives
Phase 1's counts. A second container started like `neo4j-real` (database `realdata`) takes
look-alike records built here and replaces them on the next resolved load (L9)."""

import csv
import json
import shutil
from collections import Counter
from functools import reduce
from pathlib import Path
from typing import Any

import pytest
from followthemoney import ValueEntity, model

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.graph import NODE_MAPPINGS, PROPERTY_KINDS
from neonradar_contracts.records import iter_records
from neonradar_graph.instances import REAL_DATABASE, Instance
from neonradar_graph.loader import LoadReport, collect_files, load, load_files
from neonradar_graph.mapping import to_node_rows, to_relationship_rows
from neonradar_graph.verify import verify
from neonradar_keys.names import latin_forms

from .conftest import DEMO_DIRS, Neo4jTarget, record, resolve

pytestmark = pytest.mark.integration

NAME_PROPS = ("name", "alias", "previousName", "abbreviation")
NONE = {f"I{n}": 0 for n in range(1, 18)}
FIXTURE = Path(__file__).parent / "fixtures" / "mapping" / "all-schemata.ftm.jsonl"


def query(db: Neo4jTarget, cypher: str, **params: Any) -> list[dict[str, Any]]:
    records, _, _ = db.driver.execute_query(cypher, params, database_=db.database)
    return [found.data() for found in records]


def counts(db: Neo4jTarget) -> dict[str, dict[str, int]]:
    labels = query(
        db,
        "MATCH (n) WHERE NOT n:SchemaMigration UNWIND labels(n) AS label"
        " RETURN label, count(*) AS n ORDER BY label",
    )
    types = query(db, "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY type")
    return {
        "labels": {row["label"]: row["n"] for row in labels},
        "types": {row["type"]: row["n"] for row in types},
    }


def load_demo(db: Neo4jTarget, run_dir: Path | None, **kwargs: Any) -> LoadReport:
    report = load_files(db.driver, DEMO_DIRS, database=db.database, resolution=run_dir, **kwargs)
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    return report


def canonical_rows(run_dir: Path) -> list[dict[str, str]]:
    with (run_dir / "canonical.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def candidate_lines(run_dir: Path) -> list[dict[str, Any]]:
    text = (run_dir / "candidates.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def demo_records() -> dict[str, dict[str, Any]]:
    return {r["id"]: r for path in collect_files(DEMO_DIRS) for r in iter_records(path)}


def test_a_resolved_demo_load_holds_every_invariant_and_loads_twice_the_same(
    graph_db: Neo4jTarget, demo_resolution: Path
) -> None:
    first = load_demo(graph_db, demo_resolution)
    assert verify(graph_db.driver, graph_db.database) == NONE
    before = counts(graph_db)
    lines = candidate_lines(demo_resolution)
    assert before["types"]["POSSIBLY_SAME_AS"] == len(lines) == first.possible_matches > 0
    assert before["labels"]["SourceRecord"] == before["types"]["RESOLVED_TO"]
    assert before["labels"]["SourceRecord"] == first.source_records > 0
    assert first.resolution_run == demo_resolution.name and first.merged_entities > 0
    paid = (
        "MATCH ()-[r:PAID]->() RETURN count(r) AS n,"
        " sum(CASE WHEN r.ts IS :: ZONED DATETIME THEN 1 ELSE 0 END) AS dt"
    )
    (found,) = query(graph_db, paid)
    assert found["n"] == found["dt"] > 0  # PAID.ts is a DATETIME after a resolved load (I3)
    second = load_demo(graph_db, demo_resolution)
    assert counts(graph_db) == before  # L16
    assert second.superseded_removed > 0  # the first load's nodes, replaced (L9)
    for name in (
        "nodes_by_label",
        "relationships_by_type",
        "canonical_entities",
        "merged_entities",
        "source_records",
        "possible_matches",
        "self_loops_dropped",
        "duplicate_relationships_merged",
    ):
        assert getattr(second, name) == getattr(first, name), name


def test_one_merged_entity_follows_the_merge_rules(
    graph_db: Neo4jTarget, demo_resolution: Path
) -> None:
    load_demo(graph_db, demo_resolution)
    rows = canonical_rows(demo_resolution)
    clusters: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if int(row["cluster_size"]) >= 2:
            clusters.setdefault(row["canonical_id"], []).append(row)
    canonical_id = max(sorted(clusters), key=lambda cid: len(clusters[cid]))
    members = clusters[canonical_id]
    records = demo_records()
    anchor_id = canonical_id.removeprefix("nr-")
    registry = load_registry()

    def order(data: dict[str, Any]) -> tuple[bool, int, str]:
        priority = registry.get(data["datasets"][0]).anchor_priority  # type: ignore[union-attr]
        return data["id"] != anchor_id, priority or 0, data["id"]

    ordered = sorted((records[m["record_id"]] for m in members), key=order)
    anchor = ordered[0]
    names = list(
        dict.fromkeys(v for r in ordered for p in NAME_PROPS for v in r["properties"].get(p, []))
    )[:50]
    topics = sorted({t for r in ordered for t in r["properties"].get("topics", [])})
    methods = {m["method"] for m in members if m["method"] != "anchor"}
    (stored,) = query(
        graph_db,
        "MATCH (e:Entity {id: $id}) RETURN properties(e) AS props, labels(e) AS labels",
        id=canonical_id,
    )
    props = stored["props"]
    assert props["schema"] == reduce(model.common_schema, (r["schema"] for r in ordered)).name
    caption = anchor.get("caption") or ValueEntity.from_dict(dict(anchor)).caption  # it pops keys
    assert props["caption"] == caption
    assert props["names"] == names and props["names_latin"] == latin_forms(names)
    assert props["topics"] == topics
    assert props["datasets"] == sorted({d for r in ordered for d in r["datasets"]})
    assert props["referents"] == sorted(r["id"] for r in ordered)
    assert (props["cluster_size"], props["synthetic"]) == (len(members), True)
    assert props["resolution"] == (methods.pop() if len(methods) == 1 else "mixed")
    assert ("Sanctioned" in stored["labels"]) == ("sanction" in topics)
    for flag, topic in (("PEP", "role.pep"), ("RCA", "role.rca")):
        assert (flag in stored["labels"]) == any(
            t.split(".")[:2] == topic.split(".") for t in topics
        )
    # Each member as its own entity (Phase 1's mapping), then the 7.1.6 rules over them.
    singles = {row.id: row.props for row in to_node_rows(ordered).rows}
    member_props = [singles[r["id"]] for r in ordered]
    assert props["countries"] == sorted({c for p in member_props for c in p["countries"]})
    scalars = ("source_url", "first_seen", "last_seen")
    for name in (*scalars, *NODE_MAPPINGS[props["schema"]].properties.values()):
        values = [p[name] for p in member_props if p.get(name) is not None]
        if not values:
            assert name not in props, name
        elif PROPERTY_KINDS.get(name) == "list":  # sorted unions
            assert props[name] == sorted({v for found in values for v in found}), name
        elif name in ("birth_date", "first_seen", "last_seen"):  # most precise, min, max
            wanted = {"birth_date": max(values, key=len), "first_seen": min(values)}
            assert props[name] == wanted.get(name, max(values)), name
        else:  # the anchor's value, else the first in member order
            assert props[name] == values[0], name
    assert not query(
        graph_db, "MATCH (e:Entity) WHERE e.id IN $ids RETURN e.id", ids=props["referents"]
    )
    sources = query(
        graph_db,
        "MATCH (s:SourceRecord)-[r:RESOLVED_TO]->(:Entity {id: $id})"
        " RETURN s.id AS id, s.topics AS topics, s.canonical_id AS canonical,"
        " r.method AS method, r.rule AS rule, r.match_probability AS p ORDER BY id",
        id=canonical_id,
    )
    assert [(s["id"], s["method"], s["rule"], s["p"]) for s in sources] == [
        (m["record_id"], m["method"], m["rule"] or None, 1.0) for m in members
    ]
    for source in sources:
        assert source["topics"] == records[source["id"]]["properties"].get("topics", [])
        assert source["canonical"] == canonical_id


def changed_run(run_dir: Path, folder: Path) -> tuple[Path, list[str]]:
    """A copy of `run_dir` under a new run id in which two more person records are merged
    (by a deterministic rule, as canonical.csv would record it)."""
    changed = folder / "er-20261023T130000-0e0f"
    shutil.copytree(run_dir, changed)
    summary = json.loads((changed / "run.json").read_text(encoding="utf-8"))
    summary["run_id"] = changed.name
    (changed / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    rows = canonical_rows(run_dir)
    named = {x for line in candidate_lines(run_dir) for x in (line["record_a"], line["record_b"])}
    records = demo_records()
    pair = [
        rid
        for row in rows
        if row["method"] == "identity" and row["class"] == "person"
        and (rid := row["record_id"]) not in named
        and not records[rid]["properties"].get("topics")
    ][:2]  # fmt: skip
    anchor = min(pair)
    for row in rows:
        if row["record_id"] in pair:
            linked = row["record_id"] != anchor
            row.update(
                canonical_id=f"nr-{anchor}",
                cluster_size="2",
                method="deterministic" if linked else "anchor",
                rule="D1" if linked else "",
                match_probability="1.0",
                via=anchor if linked else "",
                path_methods="deterministic" if linked else "",
            )
    with (changed / "canonical.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return changed, pair


def test_a_changed_run_leaves_no_superseded_node(
    graph_db: Neo4jTarget, demo_resolution: Path, tmp_path: Path
) -> None:
    load_demo(graph_db, demo_resolution)
    (first,) = query(graph_db, "MATCH (n) WHERE n:Entity OR n:SourceRecord RETURN count(n) AS n")
    changed, pair = changed_run(demo_resolution, tmp_path)
    report = load_demo(graph_db, changed)
    assert verify(graph_db.driver, graph_db.database) == NONE  # I13 among them
    assert query(graph_db, "MATCH (e:Entity) WHERE e.id IN $ids RETURN e.id", ids=pair) == []
    merged = "MATCH (e:Entity {id: $id}) RETURN e.cluster_size AS size, e.resolution AS how"
    assert query(graph_db, merged, id=f"nr-{min(pair)}") == [{"size": 2, "how": "deterministic"}]
    # the L9 purge removes every entity and source record of the first load
    assert report.superseded_removed == first["n"] and report.resolution_run == changed.name


def test_a_load_without_a_resolution_run_gives_the_phase_1_counts(graph_db: Neo4jTarget) -> None:
    report = load_demo(graph_db, None)
    records = list(demo_records().values())
    nodes, relationships = to_node_rows(records).rows, to_relationship_rows(records).rows
    labels = Counter(label for row in nodes for label in (*row.labels, *row.flags))
    assert report.nodes_by_label == labels
    assert report.relationships_by_type == Counter(row.type for row in relationships)
    stored = counts(graph_db)
    assert "SourceRecord" not in stored["labels"]
    assert not {"RESOLVED_TO", "POSSIBLY_SAME_AS"} & set(stored["types"])
    single = (
        "MATCH (e:Entity) WHERE e.cluster_size <> 1 OR e.resolution <> 'identity'"
        " RETURN count(e) AS n"
    )
    assert query(graph_db, single) == [{"n": 0}]
    assert (report.resolution_run, report.superseded_removed) == (None, 0)


# The real-data instance: a second container started like neo4j-real (database realdata,
# conftest.py's `real_neo4j`), loaded with look-alike records built here (never committed,
# PHASE-2.md 2.9).


def look_alike_set(folder: Path, tag: str) -> tuple[Path, Path]:
    """A company, its owner recorded twice with one native id (merged by D5) and a holding;
    written to `folder` and resolved. `tag` keeps the ids of two sets apart."""
    company, owner = f"gbch-co-T000000{tag}", f"gbch-psc-T000000{tag}1"
    native = {"v": "1.1", "source_ref": f"T-{tag}"}
    rows = [
        record(company, "Company", name=f"Test Holder T000000{tag} Ltd", jurisdiction="gb"),
        record(owner, "Person", native, name="Test Person"),
        record(f"gbch-psc-T000000{tag}2", "Person", native, name="Test Person"),
        record(f"gbch-ownership-T{tag}", "Ownership", owner=owner, asset=company),
    ]
    records = folder / f"records-{tag}"
    records.mkdir()
    (records / "look-alikes.ftm.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    return records, resolve([records], folder / f"er-20261023T12000{tag}-0a0{tag}")


def node_ids(db: Neo4jTarget) -> set[str]:
    found = query(db, "MATCH (n) WHERE n:Entity OR n:Sanction OR n:SourceRecord RETURN n.id AS id")
    return {row["id"] for row in found}


def test_a_resolved_real_load_replaces_the_previous_one(
    real_neo4j: Neo4jTarget, graph_db: Neo4jTarget, tmp_path: Path
) -> None:
    first_records, first_run = look_alike_set(tmp_path, "1")
    first = load([first_records], first_run, instance=Instance.REAL, driver=real_neo4j.driver)
    assert (first.merged_entities, first.source_records, first.dangling) == (1, 2, [])
    assert verify(real_neo4j.driver, REAL_DATABASE) == NONE
    first_ids = node_ids(real_neo4j)
    assert "nr-gbch-psc-T00000011" in first_ids
    second_records, second_run = look_alike_set(tmp_path, "2")
    second = load([second_records], second_run, instance=Instance.REAL, driver=real_neo4j.driver)
    assert second.superseded_removed == len(first_ids)  # every entity, sanction and source record
    assert node_ids(real_neo4j).isdisjoint(first_ids)  # the first set is gone
    assert verify(real_neo4j.driver, REAL_DATABASE) == NONE
    # A synthetic load into the first container leaves the real-data one unchanged.
    before = counts(real_neo4j)
    load_files(graph_db.driver, [FIXTURE], database=graph_db.database)
    assert counts(real_neo4j) == before
