"""The loader without a database (neonradar_graph.loader): files, C1 and C2 checks, query text,
batching. The database side is in test_loader.py (integration)."""

import copy
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from neonradar_contracts.graph import FLAG_LABELS, NODE_MAPPINGS
from neonradar_contracts.records import iter_records
from neonradar_graph import loader
from neonradar_graph.loader import (
    LoadError,
    LoadRefused,
    collect_files,
    load_files,
    load_records,
    node_query,
    plan_load,
    read_records,
    relationship_query,
)
from neonradar_graph.mapping import RelationshipRow
from neonradar_graph.migrate import discover

from .conftest import record

FIXTURE = Path(__file__).parent / "fixtures" / "mapping" / "all-schemata.ftm.jsonl"


def fixture() -> dict[str, dict[str, Any]]:
    return {data["id"]: copy.deepcopy(data) for data in iter_records(FIXTURE)}


def test_a_folder_gives_the_record_files_directly_inside_it(tmp_path: Path) -> None:
    for name in (
        "b.ftm.jsonl",
        "a.ftm.jsonl",
        "a.manifest.json",
        "labels/x.csv",
        "sub/c.ftm.jsonl",
    ):
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).write_text("", encoding="utf-8")
    a, b = tmp_path / "a.ftm.jsonl", tmp_path / "b.ftm.jsonl"
    assert collect_files([tmp_path]) == [a.resolve(), b.resolve()]
    assert collect_files([b, tmp_path]) == [b.resolve(), a.resolve()]  # each file once
    (tmp_path / "empty").mkdir()
    with pytest.raises(LoadError, match=r"no \*\.ftm\.jsonl files"):
        collect_files([tmp_path / "empty"])
    with pytest.raises(LoadError, match="no such file"):
        collect_files([tmp_path / "missing.ftm.jsonl"])


def test_an_unreadable_line_stops_the_load(tmp_path: Path) -> None:
    path = tmp_path / "bad.ftm.jsonl"
    path.write_text('{"id": "syn-co-1"}\nnot json\n', encoding="utf-8")
    with pytest.raises(LoadError, match=r"^FORMAT .*bad\.ftm\.jsonl:2"):
        read_records([path])


def test_node_queries_take_labels_from_the_mapping() -> None:
    company = node_query("Company")
    assert company.splitlines()[:4] == [
        "UNWIND $rows AS row",
        "MERGE (n:Entity {id: row.id})",
        "SET n:LegalEntity:Organization:Company",
        "SET n += row.props",
    ]
    for flag in FLAG_LABELS:
        assert f"WHEN row.flags.{flag} THEN [1] ELSE [] END | SET n:{flag})" in company
        assert f"WHEN NOT row.flags.{flag} THEN [1] ELSE [] END | REMOVE n:{flag})" in company
    sanction = node_query("Sanction")
    assert "MERGE (n:Sanction {id: row.id})" in sanction
    assert "SET n:LegalEntity" not in sanction and "SET n += row.props" in sanction


def test_relationship_queries_match_ends_on_the_key_label_and_check_the_c2_label() -> None:
    paid = relationship_query(RelationshipRow("PAID", "x", "a", "b", {}, "2026-03-14T10:22:05Z"))
    seek = "USING INDEX SEEK"
    assert (
        f"OPTIONAL MATCH (s:Entity {{id: row.source}}) {seek} s:Entity(id) WHERE s:Account" in paid
    )
    assert (
        f"OPTIONAL MATCH (t:Entity {{id: row.target}}) {seek} t:Entity(id) WHERE t:Account" in paid
    )
    assert "MERGE (s)-[r:PAID {id: row.id}]->(t)" in paid
    assert "SET r += row.props, r.ts = datetime(row.ts))" in paid
    subject = relationship_query(RelationshipRow("SUBJECT_OF", "x", "a", "b", {}))
    assert f"(s:Entity {{id: row.source}}) {seek} s:Entity(id) WHERE s:Entity" in subject
    assert f"(t:Sanction {{id: row.target}}) {seek} t:Sanction(id) WHERE t:Sanction" in subject
    assert "datetime" not in subject
    assert "DELETE old\n" in paid  # Payment builds only PAID
    owns = relationship_query(RelationshipRow("OWNS", "x", "a", "b", {}))
    assert "OPTIONAL MATCH (a)-[old:OWNS {id: row.id}]->(b)" in owns
    assert "  WHERE s IS NULL OR t IS NULL OR a <> s OR b <> t" in owns  # moved or missing end
    for n, other in enumerate(["HOLDS_ACCOUNT", "CONSOLIDATES"]):  # the other Ownership types
        assert f"OPTIONAL MATCH ()-[o{n}:{other} {{id: row.id}}]->()" in owns
    assert "DELETE old, o0, o1\n" in owns


@pytest.mark.parametrize("name", ["Company`) DETACH DELETE n //", "company", "", "UNKNOWN"])
def test_a_name_that_is_not_an_identifier_never_reaches_query_text(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setitem(NODE_MAPPINGS, "Company", SimpleNamespace(labels=("Entity", name)))
    with pytest.raises(ValueError, match="not a label name"):
        node_query("Company")
    with pytest.raises(ValueError, match="not a relationship type name"):
        relationship_query(RelationshipRow(name or "x", "x", "a", "b", {}))


def test_a_strict_plan_refuses_c1_issues_and_mapping_issues() -> None:
    records = fixture()
    plan = plan_load(list(records.values()), strict=True)
    assert len(plan.nodes) > 0 and len(plan.relationships) > 0
    records["syn-payment-000001"]["properties"]["amount"] = ["-5"]
    with pytest.raises(LoadRefused) as refused:
        plan_load(list(records.values()), strict=True)
    assert [issue.rule for issue in refused.value.issues] == ["R7"]
    records = fixture()
    records["syn-ownership-0001"]["properties"]["owner"].append("syn-p-0002")
    with pytest.raises(LoadRefused) as refused:
        plan_load(list(records.values()), strict=True)
    assert [issue.record_id for issue in refused.value.skipped] == ["syn-ownership-0001"]


def test_a_non_strict_plan_never_maps_records_that_fail_c1() -> None:
    records = fixture()
    first = records["syn-co-0002"]
    first["properties"]["jurisdiction"] = ["not a country"]  # the first record fails C1 ...
    later = copy.deepcopy(first)
    later["properties"]["jurisdiction"] = ["gb"]  # ... and a valid duplicate never replaces it
    unheld = record("syn-acct-0009", "BankAccount", accountNumber="NRSYN0000000009")
    plan = plan_load([*records.values(), later, unheld], strict=False)
    ids = {row.id for row in plan.nodes}
    assert "syn-co-0002" not in ids and "syn-acct-0009" not in ids
    assert {issue.rule for issue in plan.rejected} >= {"R3", "R4", "R8"}
    # Edges that point at the rejected company still map; the loader counts them as dangling
    # unless the graph already holds that company.
    assert any(row.source == "syn-co-0002" for row in plan.relationships)


def test_a_non_strict_plan_drops_an_account_whose_holding_was_skipped() -> None:
    records = fixture()
    holding = records["syn-ownership-0002"]  # syn-co-0001 holds syn-acct-0001
    holding["properties"]["owner"].append("syn-co-0002")  # two owners: C1 passes, C2 skips it
    account = holding["properties"]["asset"][0]
    plan = plan_load(list(records.values()), strict=False)
    assert [str(issue) for issue in plan.skipped] == [
        "C2 syn-ownership-0002: one relationship needs exactly one owner and one asset"
        " (has 2 and 1)"
    ]
    assert account not in {row.id for row in plan.nodes}  # else invariant I4 would break
    assert [(i.rule, i.record_id) for i in plan.rejected] == [("R8", account)]


class FakeDriver:
    """Records each query; answers the migration check and returns no dangling rows."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, Any]]]] = []

    @contextmanager
    def session(self, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(run=lambda query: [{"id": m.id} for m in discover()])

    def execute_query(self, query: str, rows: list[dict[str, Any]], database_: str) -> Any:
        self.calls.append((query, rows))
        counters = SimpleNamespace(
            nodes_created=len(rows) if "MERGE (n:" in query else 0,
            relationships_created=0,
            relationships_deleted=0,
            labels_added=0,
            labels_removed=0,
        )
        return [], SimpleNamespace(counters=counters), []


def test_rows_go_in_batches_as_parameters_and_never_into_query_text() -> None:
    records = fixture()
    odd = "x}) DETACH DELETE n //"
    records["syn-co-0002"]["properties"]["name"] = [odd]
    for n in range(3, 8):  # five more accounts, each with its holder
        rid = f"syn-acct-000{n}"
        records[rid] = record(rid, "BankAccount", accountNumber=f"NRSYN000000000{n}")
        own = f"syn-ownership-01{n}"
        records[own] = record(own, "Ownership", owner="syn-co-0001", asset=rid)
    driver = FakeDriver()
    report = load_records(driver, list(records.values()), batch_size=2)  # type: ignore[arg-type]
    queries = [query for query, _ in driver.calls]
    assert all(odd not in query for query in queries)
    accounts = [rows for query, rows in driver.calls if "SET n:Account" in query]
    assert [len(rows) for rows in accounts] == [2, 2, 2, 1]
    assert report.nodes_by_label["Account"] == 7
    assert report.written["nodes_created"] == sum(
        report.nodes_by_label[k] for k in ("Entity", "Sanction")
    )
    assert report.relationships_by_type["HOLDS_ACCOUNT"] == 7
    first_relationship = next(i for i, query in enumerate(queries) if "-[r:" in query)
    assert all("MERGE (n:" in query for query in queries[:first_relationship])  # nodes first
    assert loader.BATCH_SIZE == 5_000


def test_an_empty_record_file_is_reported(tmp_path: Path) -> None:
    empty = tmp_path / "empty.ftm.jsonl"
    empty.write_text("", encoding="utf-8")
    report = load_files(FakeDriver(), [empty, FIXTURE])  # type: ignore[arg-type]
    assert report.empty_files == [empty.resolve()]
    assert report.records == len(fixture())
