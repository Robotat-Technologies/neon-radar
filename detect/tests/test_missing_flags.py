"""A node or relationship without a `synthetic` property counts as real (fail closed, G12).

Phase 1 checked this in its alert builder (`test_alerts.py::test_a_missing_synthetic_flag_counts_as
_real`, retired in M3.2, phase-3 reconciliation R2). From Phase 3 on each `Source` reads the flag,
so this checks the Cypher source's reading of a missing value, the oracle's reading of a record
without `nr.synthetic`, and what R-REAL decides about a payment finding that touches such a node.
"""

from typing import Any

from neonradar_detect import policy
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource
from neonradar_detect.model import EdgeInfo, Finding, NodeInfo, Subject
from neonradar_detect.neo4jsource import Neo4jSource


class FakeRecord:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row

    def data(self) -> dict[str, Any]:
        return self.row


class FakeSession:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def run(self, query: Any, parameters: dict[str, Any]) -> list[FakeRecord]:
        return [FakeRecord(row) for row in self.rows]


class FakeDriver:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def session(self, database: str) -> FakeSession:
        return FakeSession(self.rows)


def test_the_cypher_source_reads_a_missing_flag_as_real() -> None:
    holder = {"id": "syn-co-h", "labels": ["Entity", "LegalEntity", "Organization"]}
    rows = [
        {
            "id": "syn-acct-a",
            "labels": ["Entity", "Account"],
            "caption": "syn-acct-a",
            "synthetic": None,  # a node the loader wrote without the property
            "datasets": [],
            "holders": [{**holder, "caption": "syn-co-h", "synthetic": None, "datasets": []}],
        }
    ]
    nodes = Neo4jSource(FakeDriver(rows), "neo4j").node_info(["syn-acct-a"])  # type: ignore[arg-type]
    assert nodes["syn-acct-a"].synthetic is False
    assert nodes["syn-co-h"].synthetic is False


def test_the_oracle_reads_a_record_without_the_flag_as_real() -> None:
    record = {
        "id": "syn-co-x",
        "schema": "Company",
        "datasets": ["nr_synthetic"],
        "properties": {"name": ["Fixture syn-co-x Ltd"]},
    }
    nodes = MemSource(from_records([record])).node_info(["syn-co-x"])
    assert nodes["syn-co-x"].synthetic is False


def test_a_payment_finding_on_a_node_without_the_flag_is_withheld() -> None:
    org = frozenset({"Entity", "LegalEntity", "Organization"})
    nodes = {
        "syn-acct-a": NodeInfo("syn-acct-a", frozenset({"Account"}), "a", True, (), ("x-co",)),
        "syn-acct-b": NodeInfo("syn-acct-b", frozenset({"Account"}), "b", True, ()),
        "x-co": NodeInfo("x-co", org, "x", False, ()),  # read from a node without the flag
    }
    edges = {"p1": EdgeInfo("p1", "PAID", "syn-acct-a", "syn-acct-b", True, 100.0, "GBP")}
    finding = Finding(
        "t",
        "",
        "syn-acct-a",
        ("syn-acct-a", "syn-acct-b"),
        ("p1",),
        (Subject("syn-acct-a", "origin"),),
        {},
        0.5,
        (("p1",),),
    )
    flags = policy.data_flags(finding, nodes, edges)
    assert flags.involves_real_entities and flags.wording_class == "structural_pattern"
    assert policy.decide(finding, flags, nodes, edges) is policy.Decision.ACTIVITY_ON_REAL
