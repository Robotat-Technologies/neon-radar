"""The production `Source`: one query file per method, run on Neo4j (PHASE-3.md 7.1.2).

Every query is read from `queries/<name>.cypher` and sent with `session.run(neo4j.Query(text,
timeout=...), parameters)`: an auto-commit query, so a memory-limit `TransientError` is reported
rather than retried in a loop (`detection-cypher-gds.md` 2.9). Times go in as UTC ISO strings and
are parsed in the query with `datetime($x)`; DATETIME values come back as `neo4j.time.DateTime` and
are turned into aware `datetime` objects here. The four templated queries take a value from a
fixed list for one of three placeholders (`{{max_hops}}`, `{{flag}}`, `{{rel_type}}`), checked
before substitution, so no caller text ever reaches a query. Results are converted into the
rows of `rows.py` in the order the query files document; the parity tests check them against
`MemSource` (PHASE-3.md 7.1.5).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from importlib import resources
from typing import Any

import neo4j
import neo4j.time

from neonradar_detect.expand import FrontierItem
from neonradar_detect.model import EdgeInfo, NodeInfo
from neonradar_detect.rows import (
    AccountFlows,
    AccountHistory,
    AddressCluster,
    CashProfile,
    Component,
    CounterpartyInfo,
    Deposit,
    EntityRow,
    HolderDeposits,
    Hop,
    Hub,
    LinkRow,
    ListedRow,
    OwnershipPath,
    PaidEdge,
    Pay,
    SanctionRow,
)

REGISTRY_TYPES = frozenset(
    {
        "OWNS",
        "CONTROLS",
        "CONSOLIDATES",
        "DIRECTOR_OF",
        "REPRESENTS",
        "FAMILY_OF",
        "ASSOCIATE_OF",
        "HAS_ADDRESS",
        "HOLDS_ACCOUNT",
        "HOLDS_POSITION",
    }
)
TEMPLATE_VALUES = {
    "max_hops": {str(n) for n in range(1, 9)},
    "flag": {"Sanctioned", "PEP", "RCA"},
    "rel_type": {"REPRESENTS", "DIRECTOR_OF"},
}


def iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("times must be timezone-aware")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def native(value: neo4j.time.DateTime) -> datetime:
    moment: datetime = value.to_native()
    return moment.astimezone(UTC)


def query_text(name: str, **template: str) -> str:
    text = (
        resources.files("neonradar_detect.queries")
        .joinpath(f"{name}.cypher")
        .read_text(encoding="utf-8")
    )
    for key, value in template.items():
        if value not in TEMPLATE_VALUES[key]:
            raise ValueError(f"{key} may not be {value!r}")
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        raise ValueError(f"unfilled placeholder in {name}")
    return text


def _pay(row: dict[str, Any]) -> Pay:
    return Pay(
        native(row["ts"]),
        row["edge_id"],
        row["counterparty"],
        float(row["amount"]),
        row["currency"],
        row["channel"],
    )


def _link(row: dict[str, Any]) -> LinkRow:
    return LinkRow(
        row["rel_type"],
        row["rel_id"],
        row["source"],
        row["target"],
        row["share_min"],
        row["share_max"],
        bool(row["share_min_exclusive"]),
        bool(row["share_max_exclusive"]),
        bool(row["is_nominee"]),
        row["role"],
        row["start_date"],
        row["end_date"],
        row["control_type"],
    )


class Neo4jSource:
    def __init__(self, driver: neo4j.Driver, database: str, timeout_s: float = 600.0) -> None:
        self.driver = driver
        self.database = database
        self.timeout_s = timeout_s

    def _run(self, name: str, parameters: dict[str, Any], **template: str) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(
                neo4j.Query(query_text(name, **template), timeout=self.timeout_s), parameters
            )
            return [record.data() for record in result]

    # common ----------------------------------------------------------------------------------

    def paid_time_range(self) -> tuple[datetime, datetime] | None:
        [row] = self._run("paid_time_range", {})
        return (native(row["first"]), native(row["last"])) if row["first"] is not None else None

    def node_info(self, ids: Iterable[str]) -> dict[str, NodeInfo]:
        out: dict[str, NodeInfo] = {}
        for row in self._run("node_info", {"ids": sorted(set(ids))}):
            holders = tuple(h["id"] for h in row["holders"])
            out[row["id"]] = NodeInfo(
                row["id"],
                frozenset(row["labels"]),
                row["caption"],
                bool(row["synthetic"]),
                tuple(row["datasets"]),
                holders,
            )
            for h in row["holders"]:
                out.setdefault(
                    h["id"],
                    NodeInfo(
                        h["id"],
                        frozenset(h["labels"]),
                        h["caption"],
                        bool(h["synthetic"]),
                        tuple(h["datasets"]),
                        (),
                    ),
                )
        return out

    def edge_info(self, ids: Iterable[str]) -> dict[str, EdgeInfo]:
        out = {}
        for r in self._run("edge_info", {"ids": sorted(set(ids))}):
            out[r["id"]] = EdgeInfo(
                r["id"],
                r["type"],
                r["source"],
                r["target"],
                bool(r["synthetic"]),
                float(r["amount"]) if r["amount"] is not None else None,
                r["currency"],
                native(r["ts"]) if r["ts"] is not None else None,
                r["channel"],
                r["share_min"],
                r["share_max"],
                bool(r["share_min_exclusive"]),
                bool(r["share_max_exclusive"]),
                r["role"],
                r["control_type"],
                r["start_date"],
                r["end_date"],
            )
        return out

    # paths -----------------------------------------------------------------------------------

    def paid_starts(
        self, min_amount: float, start: datetime, end: datetime, limit: int
    ) -> list[Hop]:
        rows = self._run(
            "paid_starts",
            {"min_amount": min_amount, "start": iso(start), "end": iso(end), "limit": limit},
        )
        return [
            Hop(
                r["edge_id"],
                r["source"],
                r["target"],
                native(r["ts"]),
                float(r["amount"]),
                r["currency"],
                tuple(r["source_holders"]),
                tuple(r["target_holders"]),
            )
            for r in rows
        ]

    def paid_hop(self, frontier: Sequence[FrontierItem]) -> dict[int, list[Hop]]:
        items = [
            {
                "key": f.key,
                "account": f.account,
                "after": iso(f.after),
                "until": iso(f.until),
                "min_amount": f.min_amount,
                "max_amount": f.max_amount,
                "currency": f.currency,
                "visited": list(f.visited),
            }
            for f in frontier
        ]
        found: dict[int, list[Hop]] = {}
        for i in range(0, len(items), 5000):
            for r in self._run("paid_hop", {"frontier": items[i : i + 5000]}):
                found.setdefault(r["key"], []).append(
                    Hop(
                        r["edge_id"],
                        r["source"],
                        r["target"],
                        native(r["ts"]),
                        float(r["amount"]),
                        r["currency"],
                        (),
                        tuple(r["target_holders"]),
                    )
                )
        return found

    # flows -----------------------------------------------------------------------------------

    def _flows(self, name: str, params: dict[str, Any]) -> list[AccountFlows]:
        return [
            AccountFlows(
                r["account"],
                tuple(r["holders"]),
                tuple(_pay(x) for x in r["inflows"]),
                tuple(_pay(x) for x in r["outflows"]),
            )
            for r in self._run(name, params)
        ]

    def flows_by_inbound(
        self,
        min_inbound_counterparties: int,
        start: datetime,
        end: datetime,
        channel: str | None,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        return self._flows(
            "flows_by_inbound",
            {
                "min_counterparties": min_inbound_counterparties,
                "start": iso(start),
                "end": iso(end),
                "channel": channel,
                "bucket_hours": bucket_hours,
                "limit": limit,
            },
        )

    def flows_by_outbound(
        self,
        min_outbound_counterparties: int,
        start: datetime,
        end: datetime,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        return self._flows(
            "flows_by_outbound",
            {
                "min_counterparties": min_outbound_counterparties,
                "start": iso(start),
                "end": iso(end),
                "bucket_hours": bucket_hours,
                "limit": limit,
            },
        )

    def counterparty_info(self, accounts: Iterable[str]) -> dict[str, CounterpartyInfo]:
        return {
            r["account"]: CounterpartyInfo(
                r["account"], r["opening_date"], tuple(r["holder_labels"]), tuple(r["holders"])
            )
            for r in self._run("counterparty_info", {"ids": sorted(set(accounts))})
        }

    def paid_times(
        self, pairs: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[datetime, ...]]:
        wanted = sorted(set(pairs))
        out: dict[tuple[str, str], tuple[datetime, ...]] = {}
        for i in range(0, len(wanted), 20000):
            for r in self._run("paid_times", {"pairs": [list(p) for p in wanted[i : i + 20000]]}):
                out[(r["payer"], r["payee"])] = tuple(native(t) for t in r["times"])
        return out

    def _payments(
        self, name: str, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        out: dict[str, list[Pay]] = {}
        for r in self._run(
            name, {"ids": sorted(set(accounts)), "start": iso(start), "end": iso(end)}
        ):
            out.setdefault(r["account"], []).append(_pay(r))
        return out

    def payments_from(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        return self._payments("payments_from", accounts, start, end)

    def payments_into(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        return self._payments("payments_into", accounts, start, end)

    def payments_among(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> list[tuple[str, str, str]]:
        rows = self._run(
            "payments_among", {"ids": sorted(set(accounts)), "start": iso(start), "end": iso(end)}
        )
        return [(r["edge_id"], r["payer"], r["payee"]) for r in rows]

    def activity_counts(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, int]:
        rows = self._run(
            "activity_counts", {"ids": sorted(set(accounts)), "start": iso(start), "end": iso(end)}
        )
        return {r["account"]: int(r["payments"]) for r in rows}

    def holder_cash_deposits(
        self,
        band_low: float,
        threshold: float,
        min_in_band: int,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[HolderDeposits]:
        rows = self._run(
            "holder_cash_deposits",
            {
                "band_low": band_low,
                "threshold": threshold,
                "min_in_band": min_in_band,
                "start": iso(start),
                "end": iso(end),
                "limit": limit,
            },
        )
        return [
            HolderDeposits(
                r["holder"],
                tuple(
                    Deposit(
                        native(d["ts"]),
                        d["edge_id"],
                        d["account"],
                        d["branch"],
                        float(d["amount"]),
                        d["currency"],
                    )
                    for d in r["deposits"]
                ),
            )
            for r in rows
        ]

    def _histories(self, name: str, params: dict[str, Any]) -> list[AccountHistory]:
        out = []
        for r in self._run(name, params):
            pays = tuple((_pay(x), x["direction"]) for x in r["pays"])
            out.append(AccountHistory(r["account"], r["opening_date"], tuple(r["holders"]), pays))
        return out

    def quiet_account_histories(
        self,
        min_gap_days: int,
        max_quiet_payments: int,
        max_quiet_amount: float,
        history_start: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[AccountHistory]:
        return self._histories(
            "quiet_account_histories",
            {
                "min_gap_days": min_gap_days,
                "max_quiet_payments": max_quiet_payments,
                "max_quiet_amount": max_quiet_amount,
                "history_start": history_start,
                "start": iso(start),
                "end": iso(end),
                "limit": limit,
            },
        )

    def company_account_histories(
        self, incorporated_since: str, start: datetime, end: datetime, min_payments: int, limit: int
    ) -> list[AccountHistory]:
        return self._histories(
            "company_account_histories",
            {
                "incorporated_since": incorporated_since,
                "start": iso(start),
                "end": iso(end),
                "min_payments": min_payments,
                "limit": limit,
            },
        )

    def recent_account_components(
        self, new_days: int, start: datetime, end: datetime, min_size: int
    ) -> list[Component]:
        params = {"new_days": new_days, "start": iso(start), "end": iso(end)}
        edges = [
            PaidEdge(
                native(r["ts"]),
                r["edge_id"],
                r["source"],
                r["target"],
                float(r["amount"]),
                r["currency"],
                r["channel"],
            )
            for r in self._run("recent_account_edges", params)
        ]
        if not edges:
            return []
        graph = f"nr-ring-{uuid.uuid4().hex}"
        try:
            self._run("recent_account_components_project", {**params, "graph_name": graph})
            rows = self._run("recent_account_components_wcc", {"graph_name": graph})
        finally:
            self._run("recent_account_components_drop", {"graph_name": graph})
        groups: dict[int, list[str]] = {}
        for r in rows:
            groups.setdefault(r["component_id"], []).append(r["account_id"])
        out = []
        for members in groups.values():
            if len(members) < min_size:
                continue
            member_set = set(members)
            out.append(
                Component(
                    tuple(sorted(members)),
                    tuple(sorted(e for e in edges if e.source in member_set)),
                )
            )
        return sorted(out, key=lambda c: c.accounts[0])

    # registry --------------------------------------------------------------------------------

    def entities(self, ids: Iterable[str]) -> dict[str, EntityRow]:
        out = {}
        for r in self._run("entities", {"ids": sorted(set(ids))}):
            out[r["id"]] = EntityRow(
                r["id"],
                tuple(sorted(r["labels"])),
                r["schema"],
                r["jurisdiction"],
                r["incorporation_date"],
                bool(r["synthetic"]),
                r["accounts_category"],
                r["sector"],
                r["status"],
                r["dissolution_date"],
                tuple(r["datasets"]),
                tuple(r["psc_statements"]),
                r["full"],
                r["postal_code"],
                r["city"],
                tuple(r["countries"]),
            )
        return out

    def _links(
        self, name: str, ids: Iterable[str], types: Sequence[str]
    ) -> dict[str, list[LinkRow]]:
        bad = set(types) - REGISTRY_TYPES
        if bad:
            raise ValueError(f"not registry relationship types: {sorted(bad)}")
        out: dict[str, list[LinkRow]] = {}
        for r in self._run(name, {"ids": sorted(set(ids)), "types": sorted(set(types))}):
            out.setdefault(r["key"], []).append(_link(r))
        return out

    def links_into(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        return self._links("links_into", ids, types)

    def links_from(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        return self._links("links_from", ids, types)

    def appointment_counts(self, people: Iterable[str], as_of: str) -> dict[str, int]:
        return {
            r["id"]: int(r["appointments"])
            for r in self._run("appointment_counts", {"ids": sorted(set(people)), "as_of": as_of})
        }

    def _paths(self, name: str, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        rows = self._run(name, {"limit": limit, "as_of": as_of}, max_hops=str(max_hops))
        return [
            OwnershipPath(tuple(r["node_ids"]), tuple(_link(x) for x in r["links"])) for r in rows
        ]

    def ownership_paths(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        return self._paths("ownership_paths", max_hops, limit, as_of)

    def ownership_cycles(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        return self._paths("ownership_cycles", max_hops, limit, as_of)

    def registered_clusters(
        self, min_members: int, active_only: bool, limit: int
    ) -> list[AddressCluster]:
        rows = self._run(
            "registered_clusters",
            {"min_members": min_members, "active_only": active_only, "limit": limit},
        )
        return [
            AddressCluster(
                r["address"], r["full"], r["postal_code"], tuple((m[0], m[1]) for m in r["members"])
            )
            for r in rows
        ]

    def registered_count_quantile(self, q: float, active_only: bool) -> int:
        [row] = self._run("registered_count_quantile", {"q": q, "active_only": active_only})
        return int(row["value"])

    def listed_entities(self) -> list[ListedRow]:
        return [
            ListedRow(
                r["entity"],
                tuple(sorted(r["labels"])),
                tuple(r["datasets"]),
                tuple(
                    SanctionRow(
                        s["id"],
                        tuple(s["datasets"]),
                        s["authority"],
                        s["program"],
                        tuple(s["provisions"]),
                        s["start_date"],
                        s["end_date"],
                    )
                    for s in r["sanctions"]
                ),
            )
            for r in self._run("listed_entities", {})
        ]

    def flagged_ids(self, flag: str) -> list[str]:
        return [r["id"] for r in self._run("flagged_ids", {}, flag=flag)]

    def hubs(self, rel_type: str, min_members: int, limit: int) -> list[Hub]:
        rows = self._run("hubs", {"min_members": min_members, "limit": limit}, rel_type=rel_type)
        return [Hub(r["hub"], tuple(_link(x) for x in r["links"])) for r in rows]

    def cash_profiles(
        self, prior_start: datetime, start: datetime, end: datetime, currency: str, limit: int
    ) -> list[CashProfile]:
        rows = self._run(
            "cash_profiles",
            {
                "prior_start": iso(prior_start),
                "start": iso(start),
                "end": iso(end),
                "currency": currency,
                "limit": limit,
            },
        )
        return [
            CashProfile(
                r["holder"],
                r["sector"],
                r["postal_code"],
                r["city"],
                tuple(r["accounts"]),
                int(r["window_pence"]),
                int(r["window_deposits"]),
                int(r["prior_pence"]),
                int(r["prior_deposits"]),
            )
            for r in rows
        ]
