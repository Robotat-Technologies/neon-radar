"""EXPLAIN every detector query on a test database (PHASE-3.md 7.1.6).

Adapted from the code book's reference (M3.2 deliverable 8): the fixture is
`neo4j_driver_with_world` below, on the shared test database (graph/tests/support/nr_test_neo4j.py),
and the database name comes from it. The offline linters
cannot see the planner; this test asks the server. A query fails when it is not read only (the
three GDS ring files excepted, which project, stream and drop), when the server reports a
deprecation, an unfulfillable hint, a missing parameter (`01N` statuses other than `01N50` to
`01N52`, which mean a label, type or property is absent from the empty test graph), a cartesian
product (`03N90`), an unbounded or exhaustive shortest path (`03N91`, `03N92`) or a shadowed
subquery variable (`03N60`), or when an anchored window query does not seek the `paid_ts` index.
The planner chooses by statistics, so the fixture loads a small generated world first (80
companies, 120 people, one scenario and one look-alike per typology, seed 5: the settings of
`test_world_parity.py`); on an empty database it may not seek.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
import worlds
from nr_test_neo4j import Neo4jTarget

from neonradar_detect.neo4jsource import TEMPLATE_VALUES, query_text
from neonradar_graph.loader import load_records

pytestmark = pytest.mark.integration


@pytest.fixture
def neo4j_driver_with_world(graph_db: Neo4jTarget) -> Iterator[Neo4jTarget]:
    """The shared test database with the small world and overlay of `worlds.py` loaded."""
    report = load_records(graph_db.driver, worlds.small_world(), database=graph_db.database)
    assert (report.dangling, report.rejected, report.skipped) == ([], [], [])
    yield graph_db


START, END, PRIOR = "2026-01-01T00:00:00Z", "2026-07-01T00:00:00Z", "2025-07-01T00:00:00Z"
IDS = {"ids": ["syn-fx-co-a", "syn-fx-acct-b"]}
WINDOW = {"start": START, "end": END}
FRONTIER = [
    {
        "key": 0,
        "account": "syn-fx-acct-b",
        "after": START,
        "until": END,
        "min_amount": 100.0,
        "max_amount": 1000.0,
        "currency": "GBP",
        "visited": ["syn-fx-acct-b"],
    }
]
PARAMS: dict[str, dict[str, Any]] = {
    "activity_counts": {**IDS, **WINDOW},
    "appointment_counts": {**IDS, "as_of": "2026-07-01"},
    "cash_profiles": {"currency": "GBP", "prior_start": PRIOR, **WINDOW, "limit": 10},
    "company_account_histories": {
        **WINDOW,
        "incorporated_since": "2025-01-01",
        "min_payments": 1,
        "limit": 10,
    },
    "counterparty_info": IDS,
    "edge_info": IDS,
    "entities": IDS,
    "evidence": {"node_ids": IDS["ids"], "edge_ids": ["syn-fx-pay-00001"]},
    "flagged_ids": {},
    "flows_by_inbound": {
        "bucket_hours": 72,
        "channel": "wire",
        **WINDOW,
        "min_counterparties": 3,
        "limit": 10,
    },
    "flows_by_outbound": {"bucket_hours": 72, **WINDOW, "min_counterparties": 3, "limit": 10},
    "holder_cash_deposits": {
        "band_low": 9000.0,
        "threshold": 10000.0,
        "min_in_band": 3,
        **WINDOW,
        "limit": 10,
    },
    "hubs": {"min_members": 10, "limit": 10},
    "links_from": {**IDS, "types": ["OWNS", "CONTROLS"]},
    "links_into": {**IDS, "types": ["OWNS", "CONTROLS"]},
    "listed_entities": {},
    "node_info": IDS,
    "ownership_cycles": {"limit": 10, "as_of": "2026-07-01"},
    "ownership_paths": {"limit": 10, "as_of": "2026-07-01"},
    "paid_hop": {"frontier": FRONTIER},
    "paid_starts": {**WINDOW, "min_amount": 1000.0, "limit": 10},
    "paid_time_range": {},
    "paid_times": {"pairs": [["syn-fx-acct-b", "syn-fx-acct-c"]]},
    "payments_among": {**IDS, **WINDOW},
    "payments_from": {**IDS, **WINDOW},
    "payments_into": {**IDS, **WINDOW},
    "quiet_account_histories": {
        "min_gap_days": 180,
        "max_quiet_payments": 2,
        "max_quiet_amount": 500.0,
        "history_start": PRIOR,
        **WINDOW,
        "limit": 10,
    },
    "recent_account_components_project": {"graph_name": "nr-plan-test", **WINDOW, "new_days": 30},
    "recent_account_components_wcc": {"graph_name": "nr-plan-test"},
    "recent_account_components_drop": {"graph_name": "nr-plan-test"},
    "recent_account_edges": {**WINDOW, "new_days": 30},
    "registered_clusters": {"active_only": True, "min_members": 10, "limit": 10},
    "registered_count_quantile": {"active_only": True, "q": 0.99},
}
TEMPLATES = {
    "flagged_ids": {"flag": sorted(TEMPLATE_VALUES["flag"])},
    "hubs": {"rel_type": sorted(TEMPLATE_VALUES["rel_type"])},
    "ownership_cycles": {"max_hops": ["2", "6", "8"]},
    "ownership_paths": {"max_hops": ["2", "6", "8"]},
}
NOT_READ_ONLY = {
    "recent_account_components_project",
    "recent_account_components_wcc",
    "recent_account_components_drop",
}
MUST_SEEK = {"paid_starts", "flows_by_inbound", "flows_by_outbound", "recent_account_edges"}
ALLOWED = ("01N50", "01N51", "01N52")
FORBIDDEN = ("01N", "03N90", "03N91", "03N92", "03N60")


def _renders(name: str) -> list[str]:
    choices = TEMPLATES.get(name)
    if not choices:
        return [query_text(name)]
    [(key, values)] = choices.items()
    return [query_text(name, **{key: v}) for v in values]


def explain_problems(target: Neo4jTarget, name: str, text: str) -> list[str]:
    _, summary, _ = target.driver.execute_query(
        "EXPLAIN " + text, PARAMS[name], database_=target.database
    )
    problems = []
    if name not in NOT_READ_ONLY and summary.query_type != "r":
        problems.append(f"query type {summary.query_type}")
    for status in summary.gql_status_objects:
        code = status.gql_status
        if code.startswith(FORBIDDEN) and code not in ALLOWED:
            problems.append(f"{code}: {status.status_description}")
    if name in MUST_SEEK and "RelationshipIndexSeekByRange" not in json.dumps(summary.plan):
        problems.append("no relationship index seek on PAID.ts")
    return problems


def test_every_query_plans_cleanly(neo4j_driver_with_world: Neo4jTarget) -> None:
    from importlib import resources

    names = sorted(
        p.name.removesuffix(".cypher")
        for p in resources.files("neonradar_detect.queries").iterdir()
        if p.name.endswith(".cypher")
    )
    assert set(names) == set(PARAMS), "every query file needs sample parameters here"
    problems = {
        f"{name}#{i}": found
        for name in names
        for i, text in enumerate(_renders(name))
        if (found := explain_problems(neo4j_driver_with_world, name, text))
    }
    assert problems == {}
