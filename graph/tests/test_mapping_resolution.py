"""Records plus a resolution run to C2 rows (PHASE-2.md M2.11 deliverable 7, C2 L10 to L15):
RESOLVED_TO from a test-built `canonical.csv`, the HAS_ADDRESS merge after re-pointing, a
dropped self-loop, `PAID.ts` as a datetime, and the checks of `ResolutionMap.load` (L14).
Every record and run is built here; every id is synthetic."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from neonradar_graph.loader import ORPHAN, LoadRefused, load_records, plan_load
from neonradar_graph.mapping import (
    to_node_rows,
    to_possibly_same_as_rows,
    to_relationship_rows,
    to_resolved_to_rows,
    to_source_record_rows,
)
from neonradar_graph.resolution import CANONICAL_HEADER, ResolutionError, ResolutionMap

from .conftest import FakeDriver, record

RUN_ID = "er-20261023T120000-0a0b"
FEATURES = '{"birth":"same date","name":"name key equal"}'
MERGED = "nr-syn-p-0101"


def write_run(folder: Path, rows: list[list[str]], candidates: list[dict[str, Any]]) -> Path:
    """A run folder as `neonradar er run` writes it (7.1.8), with these rows and lines."""
    run_dir = folder / RUN_ID
    run_dir.mkdir()
    summary = {"run_id": RUN_ID, "resolver_version": "0.1.0"}
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    with (run_dir / "canonical.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows([list(CANONICAL_HEADER), *rows])
    lines = "".join(json.dumps(line) + "\n" for line in candidates)
    (run_dir / "candidates.jsonl").write_text(lines, encoding="utf-8")
    return run_dir


def row(
    record_id: str, canonical_id: str, cls: str, size: int, method: str, **cells: str
) -> list[str]:
    values = {"rule": "", "match_probability": "", "via": "", "path_methods": "", "features": ""}
    values |= cells
    head = [record_id, canonical_id, cls, str(size), method]
    return head + [values[name] for name in CANONICAL_HEADER[5:]]


ROWS = [
    row("syn-p-0101", MERGED, "person", 2, "anchor", match_probability="1.0"),
    row(
        "syn-p-0102",
        MERGED,
        "person",
        2,
        "probabilistic",
        match_probability="0.995",
        via="syn-p-0101",
        path_methods="probabilistic",
        features=FEATURES,
    ),
    row("syn-p-0103", "syn-p-0103", "person", 1, "identity"),
    row("syn-addr-0101", "syn-addr-0101", "address", 1, "identity"),
]
CANDIDATE = {
    "a": MERGED,
    "b": "syn-p-0103",
    "record_a": "syn-p-0102",
    "record_b": "syn-p-0103",
    "match_probability": None,
    "match_weight": None,
    "method": "deterministic",
    "rule": "D3",
    "reasons": ["identifier_name_mismatch"],
    "features": {},
}


def records() -> list[dict[str, Any]]:
    """Two records of one person (with one address each way), a third person, accounts and a
    payment, and a Family link between the two merged records."""
    return [
        record(
            "syn-p-0101",
            "Person",
            {"address_roles": {"syn-addr-0101": "residential"}},
            name="Ada Example",
            birthDate="1980",
            topics=["role.pep"],
            addressEntity="syn-addr-0101",
        ),
        record(
            "syn-p-0102",
            "Person",
            {"address_roles": {"syn-addr-0101": "service"}},
            name=["A. Example", "Ada Example"],
            birthDate="1980-02-03",
            nationality="gb",
            topics=["role.pep"],  # P1 (7.1.4): a probabilistic merge joins equal flag topics
            addressEntity="syn-addr-0101",
        ),
        record("syn-p-0103", "Person", name="Ada Exampel"),
        record("syn-addr-0101", "Address", full="7 Example Road, Testtown, QQ1 1QQ"),
        record("syn-family-0101", "Family", person="syn-p-0101", relative="syn-p-0102"),
        record("syn-acct-0101", "BankAccount", accountNumber="NRSYN0000000101"),
        record("syn-acct-0102", "BankAccount", accountNumber="NRSYN0000000102"),
        record("syn-ownership-0101", "Ownership", owner="syn-p-0102", asset="syn-acct-0101"),
        record("syn-ownership-0102", "Ownership", owner="syn-p-0103", asset="syn-acct-0102"),
        record(
            "syn-payment-000101",
            "Payment",
            {"channel": "wire"},
            payer="syn-p-0102",
            beneficiary="syn-p-0103",
            payerAccount="syn-acct-0101",
            beneficiaryAccount="syn-acct-0102",
            amount="120.50",
            currency="EUR",
            date="2026-03-14T10:22:05",
        ),
    ]


@pytest.fixture
def resolution(tmp_path: Path) -> ResolutionMap:
    return ResolutionMap.load(write_run(tmp_path, ROWS, [CANDIDATE]))


def test_the_run_gives_its_identity_and_the_map(resolution: ResolutionMap) -> None:
    assert (resolution.run_id, resolution.resolver_version) == (RUN_ID, "0.1.0")
    assert resolution.decided_at == "2026-10-23T12:00:00Z"  # the run id's start time (4.4)
    assert resolution.canonical("syn-p-0102") == MERGED
    assert resolution.canonical("syn-acct-0101") == "syn-acct-0101"  # not resolved: itself
    assert list(resolution.clusters()) == [MERGED]


def test_resolved_to_copies_rule_probability_and_features_from_canonical_csv(
    resolution: ResolutionMap,
) -> None:
    rows = {row.keys["record_id"]: row for row in to_resolved_to_rows(resolution)}
    assert set(rows) == {"syn-p-0101", "syn-p-0102"}
    assert rows["syn-p-0102"].keys == {"record_id": "syn-p-0102", "canonical_id": MERGED}
    assert rows["syn-p-0102"].props == {
        "method": "probabilistic",
        "rule": None,
        "match_probability": 0.995,
        "features": FEATURES,
        "run_id": RUN_ID,
        "resolver_version": "0.1.0",
        "decided_at": "2026-10-23T12:00:00Z",
    }
    anchor = rows["syn-p-0101"].props
    assert (anchor["method"], anchor["match_probability"], anchor["features"]) == (
        "anchor",
        1.0,
        None,
    )


def test_merged_entity_and_source_records(resolution: ResolutionMap) -> None:
    nodes = {row.id: row for row in to_node_rows(records(), resolution).rows}
    assert "syn-p-0101" not in nodes and "syn-p-0102" not in nodes  # I13
    merged = nodes[MERGED]
    assert merged.labels == ("Entity", "LegalEntity", "Person")
    assert merged.flags == ("Synthetic", "PEP")
    assert merged.props["names"] == ["Ada Example", "A. Example"]  # anchor first, no duplicate
    assert merged.props["topics"] == ["role.pep"]
    assert merged.props["referents"] == ["syn-p-0101", "syn-p-0102"]
    assert merged.props["birth_date"] == "1980-02-03"  # the most precise
    assert merged.props["nationalities"] == ["gb"]
    assert (merged.props["cluster_size"], merged.props["resolution"]) == (2, "probabilistic")
    single = nodes["syn-p-0103"]
    assert (single.props["cluster_size"], single.props["resolution"]) == (1, "identity")
    assert single.props["referents"] == ["syn-p-0103"]
    sources = {r.keys["id"]: r.props for r in to_source_record_rows(records(), resolution).rows}
    assert set(sources) == {"syn-p-0101", "syn-p-0102"}
    assert sources["syn-p-0102"]["topics"] == ["role.pep"]
    assert sources["syn-p-0102"]["canonical_id"] == MERGED
    assert (sources["syn-p-0101"]["retrieved_at"], sources["syn-p-0101"]["run_id"]) == (
        None,
        RUN_ID,
    )


def test_an_unlisted_record_joined_by_a_deterministic_rule_takes_the_union_of_topics(
    tmp_path: Path,
) -> None:
    """P1 (7.1.4): a listed and an unlisted record merge only through D1 to D5 or D7; the
    merged node's topics and flags are the union of its members' own topics (G8)."""
    linked = row(
        "syn-p-0102",
        MERGED,
        "person",
        2,
        "deterministic",
        rule="D1",
        match_probability="1.0",
        via="syn-p-0101",
        path_methods="deterministic",
    )
    run = ResolutionMap.load(write_run(tmp_path, [ROWS[0], linked, *ROWS[2:]], [CANDIDATE]))
    found = records()
    for found_record in found:
        if found_record["id"] == "syn-p-0102":
            del found_record["properties"]["topics"]
    merged = {r.id: r for r in to_node_rows(found, run).rows}[MERGED]
    assert (merged.flags, merged.props["topics"]) == (("Synthetic", "PEP"), ["role.pep"])
    assert merged.props["resolution"] == "deterministic"
    sources = {r.keys["id"]: r.props for r in to_source_record_rows(found, run).rows}
    assert sources["syn-p-0102"]["topics"] == []  # its own topics, never the merged ones


def test_has_address_rows_merge_after_re_pointing_and_a_self_loop_is_dropped(
    resolution: ResolutionMap,
) -> None:
    result = to_relationship_rows(records(), resolution)
    assert result.skipped == []
    addresses = [row for row in result.rows if row.type == "HAS_ADDRESS"]
    assert len(addresses) == 1
    (address,) = addresses
    assert (address.source, address.target) == (MERGED, "syn-addr-0101")
    assert address.id == address.props["id"] == "syn-p-0101|addr|syn-addr-0101"  # C2: record ids
    assert address.props["role"] == "service"  # the first of registered, service, residential
    assert result.counts["duplicate_relationships_merged"] == 1
    assert result.counts["self_loops_dropped"] == 1  # the Family link inside one person
    assert "FAMILY_OF" not in {row.type for row in result.rows}
    holding = next(row for row in result.rows if row.id == "syn-ownership-0101")
    assert (holding.type, holding.source) == ("HOLDS_ACCOUNT", MERGED)


def test_paid_ts_is_a_timezone_aware_datetime() -> None:
    (paid,) = [row for row in to_relationship_rows(records()).rows if row.type == "PAID"]
    ts = paid.props["ts"]
    assert ts == datetime(2026, 3, 14, 10, 22, 5, tzinfo=UTC) and ts.tzinfo is not None
    assert not isinstance(ts, str)


def test_rows_with_an_end_outside_the_load_take_the_resolving_query(
    resolution: ResolutionMap,
) -> None:
    loaded = {row.id for row in to_node_rows(records(), resolution).rows} - {"syn-acct-0102"}
    rows = {row.id: row for row in to_relationship_rows(records(), resolution, loaded).rows}
    assert rows["syn-ownership-0102"].resolving and rows["syn-payment-000101"].resolving
    assert not rows["syn-ownership-0101"].resolving


def test_possible_matches_copy_nothing_but_the_union_of_datasets(
    resolution: ResolutionMap,
) -> None:
    nodes = {row.id: row for row in to_node_rows(records(), resolution).rows}
    (match,) = to_possibly_same_as_rows(resolution, nodes).rows
    assert match.keys == {"id": f"{MERGED}|psa|syn-p-0103", "a": MERGED, "b": "syn-p-0103"}
    assert match.props["match_probability"] is None and match.props["rule"] == "D3"
    assert match.props["reasons"] == ["identifier_name_mismatch"]
    assert (match.props["datasets"], match.props["synthetic"]) == (["nr_synthetic"], True)


def test_a_candidate_between_addresses_stops_the_load(tmp_path: Path) -> None:
    rows = [
        row("syn-addr-0201", "syn-addr-0201", "address", 1, "identity"),
        row("syn-addr-0202", "syn-addr-0202", "address", 1, "identity"),
    ]
    line = CANDIDATE | {
        "a": "syn-addr-0201",
        "b": "syn-addr-0202",
        "record_a": "syn-addr-0201",
        "record_b": "syn-addr-0202",
    }
    with pytest.raises(ResolutionError, match="L14") as stopped:
        ResolutionMap.load(write_run(tmp_path, rows, [line]))
    assert stopped.value.exit_code == 1


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda rows, lines: rows[0].__setitem__(3, "3"), "cluster_size"),
        (lambda rows, lines: rows[0].__setitem__(1, "syn-p-0101x"), "cluster_size"),
        (lambda rows, lines: lines[0].update(a="syn-p-0103", b=MERGED), "a < b"),
        (lambda rows, lines: lines[0].update(record_b="syn-p-0999"), "lacks"),
        (lambda rows, lines: lines[0].update(method="probabilistic", rule=None), "unreadable"),
        (
            lambda rows, lines: lines[0].update(method="probabilistic", match_probability=1.5),
            "unreadable",
        ),
    ],
)
def test_a_run_that_breaks_7_1_8_stops_the_load(tmp_path: Path, change: Any, message: str) -> None:
    rows, lines = [list(r) for r in ROWS], [dict(CANDIDATE)]
    change(rows, lines)
    with pytest.raises(ResolutionError, match=message):
        ResolutionMap.load(write_run(tmp_path, rows, lines))


def test_a_load_that_does_not_fit_the_run_is_refused(resolution: ResolutionMap) -> None:
    schemas = {r["id"]: r["schema"] for r in records()}
    resolution.check_load(schemas, complete=True)
    partial = {rid: s for rid, s in schemas.items() if rid != "syn-p-0102"}
    with pytest.raises(ResolutionError, match="1 merged entit"):
        resolution.check_load(partial, complete=False)
    extra = schemas | {"syn-p-0199": "Person"}
    resolution.check_load(extra, complete=False)  # an additive load may add records
    with pytest.raises(ResolutionError, match="1 resolvable record"):
        resolution.check_load(extra, complete=True)


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("run.json", b"\xff", "run.json is not a JSON object"),
        ("canonical.csv", b"\xff", "canonical.csv is not a UTF-8 CSV file"),
        (
            "canonical.csv",
            (",".join(CANONICAL_HEADER) + "\n" + "x" * 2_000 + "\n").encode(),
            "canonical.csv is not a UTF-8 CSV file",  # a field above the limit set below
        ),
        ("candidates.jsonl", b"\xff\n", "candidates.jsonl is not a UTF-8 file"),
    ],
)
def test_an_unreadable_file_of_the_run_is_named(
    tmp_path: Path, name: str, content: bytes, message: str
) -> None:
    run_dir = write_run(tmp_path, ROWS, [CANDIDATE])
    (run_dir / name).write_bytes(content)
    limit = csv.field_size_limit(1_000)  # other imports may raise the limit
    try:
        with pytest.raises(ResolutionError, match=message):
            ResolutionMap.load(run_dir)
    finally:
        csv.field_size_limit(limit)


def test_members_of_a_merged_entity_that_was_skipped_get_no_source_record(
    tmp_path: Path,
) -> None:
    rows = [
        row("syn-p-0101", MERGED, "person", 2, "anchor", match_probability="1.0"),
        row(
            "syn-co-0102",
            MERGED,
            "org",
            2,
            "deterministic",
            rule="D1",
            match_probability="1.0",
            via="syn-p-0101",
            path_methods="deterministic",
        ),
        row("syn-p-0103", "syn-p-0103", "person", 1, "identity"),
    ]
    run = ResolutionMap.load(write_run(tmp_path, rows, []))
    found = [
        record("syn-p-0101", "Person", name="Ada Example"),
        record("syn-co-0102", "Company", name="Ada Example Ltd"),  # no schema common with Person
        record("syn-p-0103", "Person", name="Ada Exampel"),
    ]
    plan = plan_load(found, strict=False, resolution=run)
    assert (plan.source_records, plan.resolved_to) == ([], [])  # I7 holds
    orphans = {issue.record_id for issue in plan.skipped if issue.message == ORPHAN}
    assert orphans == {"syn-p-0101", "syn-co-0102"}
    with pytest.raises(LoadRefused):
        plan_load(found, strict=True, resolution=run)


def test_a_possible_match_outside_an_additive_load_is_counted(resolution: ResolutionMap) -> None:
    left_out = {"syn-p-0103", "syn-ownership-0102", "syn-acct-0102", "syn-payment-000101"}
    found = [r for r in records() if r["id"] not in left_out]
    report = load_records(FakeDriver(), found, resolution=resolution, replace=False)
    assert (report.possible_matches, report.possible_matches_outside_load) == (0, 1)
    assert report.counts()["possible_matches_outside_load"] == 1
