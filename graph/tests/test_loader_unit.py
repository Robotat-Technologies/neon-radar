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
from neonradar_graph import cypher, loader
from neonradar_graph.instances import REAL_DATABASE
from neonradar_graph.loader import (
    LoadError,
    LoadPlan,
    LoadRefused,
    LoadReport,
    PossibleMatchesNotWritten,
    collect_files,
    execute_plan,
    load_files,
    load_records,
    node_query,
    plan_load,
    read_records,
)
from neonradar_graph.mapping import SupportRow

from .conftest import FakeDriver, record

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


def test_relationship_queries_come_from_the_query_files_with_c2_names_only() -> None:
    paid = cypher.query("upsert_relationships.cypher", rel_type="PAID", target_label="Entity")
    assert "OPTIONAL MATCH (s:Entity {id: row.source})" in paid
    assert "OPTIONAL MATCH (t:Entity {id: row.target})" in paid
    assert "MERGE (s)-[r:PAID {id: row.id}]->(t)" in paid and "SET r += row.props)" in paid
    assert "datetime(" not in paid  # PAID.ts arrives as a datetime parameter
    assert "OPTIONAL MATCH (a)-[old:PAID {id: row.id}]->(b)" in paid  # moved or missing end
    assert "  WHERE s IS NULL OR t IS NULL OR a <> s OR b <> t" in paid
    subject = cypher.query(
        "upsert_relationships.cypher", rel_type="SUBJECT_OF", target_label="Sanction"
    )
    assert "OPTIONAL MATCH (t:Sanction {id: row.target})" in subject
    owns = cypher.query("upsert_relationships_resolving.cypher", rel_type="OWNS")
    assert "WHERE $labels.source IN labels(direct)" in owns  # the C2 label, as a parameter
    assert "(:SourceRecord {id: row.target})-[:RESOLVED_TO]->(via:Entity)" in owns
    assert "{{" not in owns and not owns.endswith(";")
    moved = cypher.query("delete_relationships.cypher", rel_type="CONSOLIDATES")
    assert "MATCH ()-[old:CONSOLIDATES {id: id}]->()" in moved
    assert loader.SIBLING_TYPES["OWNS"] == ("HOLDS_ACCOUNT", "CONSOLIDATES")


@pytest.mark.parametrize("name", ["Company`) DETACH DELETE n //", "company", "", "UNKNOWN"])
def test_a_name_that_is_not_a_c2_name_never_reaches_query_text(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setitem(NODE_MAPPINGS, "Company", SimpleNamespace(labels=("Entity", name)))
    with pytest.raises(ValueError, match="not a label name"):
        node_query("Company")
    with pytest.raises(ValueError, match="not a label or relationship type of C2"):
        cypher.query("upsert_relationships.cypher", rel_type=name, target_label="Entity")
    with pytest.raises(ValueError, match="not a label or relationship type of C2"):
        cypher.query("upsert_relationships.cypher", rel_type="PAID", target_label=name)


def test_a_placeholder_without_a_value_stops_the_query() -> None:
    with pytest.raises(ValueError, match="no value for the placeholder"):
        cypher.query("upsert_relationships.cypher", rel_type="PAID")


class Unmigrated(FakeDriver):
    """A FakeDriver whose migration check finds no applied migration."""

    @contextmanager
    def session(self, database: str | None = None, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(run=lambda query, parameters=None: [])


@pytest.mark.parametrize(
    ("records", "database", "code"),
    [
        ([record("syn-co-0001", "Company", name="Example Ltd")], "neo4j", 1),
        ([record("gbch-co-T0000001", "Company", name="Test Holder Ltd")], REAL_DATABASE, 2),
    ],
)
def test_a_pending_migration_stops_the_load(
    records: list[dict[str, Any]], database: str, code: int
) -> None:
    with pytest.raises(loader.SchemaNotMigrated) as stopped:
        load_records(Unmigrated(), records, database=database)
    assert stopped.value.exit_code == code


class WritesNoPossibleMatch(FakeDriver):
    """A FakeDriver on which the possible-match query finds neither end."""

    def execute_query(
        self, query: str, parameters: dict[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        records, summary, keys = super().execute_query(query, parameters, **kwargs)
        return ([{"written": 0}] if "POSSIBLY_SAME_AS" in query else records), summary, keys


def test_possible_matches_the_database_did_not_write_stop_the_load() -> None:
    keys = {"id": "syn-p-0001|psa|syn-p-0002", "a": "syn-p-0001", "b": "syn-p-0002"}
    plan = LoadPlan(0, [], [], possible_matches=[SupportRow(keys, {"synthetic": True})])
    report = LoadReport(strict=True)
    with pytest.raises(PossibleMatchesNotWritten) as stopped:
        execute_plan(WritesNoPossibleMatch(), plan, report, database="neo4j")
    assert stopped.value.exit_code == 1 and report.possible_matches == 0


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
    queries = driver.queries
    assert all(odd not in query for query in queries)
    accounts = [params["rows"] for query, params, _ in driver.calls if "SET n:Account" in query]
    assert [len(rows) for rows in accounts] == [2, 2, 2, 1]
    assert report.nodes_by_label["Account"] == 7
    assert report.written["nodes_created"] == sum(
        report.nodes_by_label[k] for k in ("Entity", "Sanction")
    )
    assert report.relationships_by_type["HOLDS_ACCOUNT"] == 7
    first_relationship = next(i for i, query in enumerate(queries) if "]->" in query)
    nodes_first = queries[1:first_relationship]  # after the migration check
    assert nodes_first and all("MERGE (n:" in query for query in nodes_first)
    assert {database for _, _, database in driver.calls} == {"neo4j"}
    assert loader.BATCH_SIZE == 5_000


def test_an_empty_record_file_is_reported(tmp_path: Path) -> None:
    empty = tmp_path / "empty.ftm.jsonl"
    empty.write_text("", encoding="utf-8")
    report = load_files(FakeDriver(), [empty, FIXTURE])  # type: ignore[arg-type]
    assert report.empty_files == [empty.resolve()]
    assert report.records == len(fixture())
