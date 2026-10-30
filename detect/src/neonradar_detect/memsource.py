"""Reference candidate steps on a MemGraph (PHASE-3.md 7.1.2).

`MemSource` implements every method of `Source` in plain Python. It is the oracle: each method
returns what its query file in `queries/` must return on the same graph, in the same order. The
detector tests run on both sources and the world parity test compares them on a generated world
(PHASE-3.md 7.1.5).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta

from neonradar_detect.expand import FrontierItem
from neonradar_detect.memgraph import MemGraph, Rel
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

INACTIVE = frozenset({"dissolved", "converted-closed", "removed", "closed"})
REGISTRY_TYPES = ("OWNS", "CONTROLS", "DIRECTOR_OF", "REPRESENTS", "FAMILY_OF", "ASSOCIATE_OF")


def _pay(rel: Rel, counterparty: str) -> Pay:
    return Pay(
        rel.props["ts"],
        rel.id,
        counterparty,
        float(rel.props["amount"]),
        rel.props["currency"],
        rel.props.get("channel") or "",
    )


def _current(rel: Rel, as_of: str) -> bool:
    end = rel.props.get("end_date") or ""
    return not (end and end <= as_of)


def _link(rel: Rel) -> LinkRow:
    p = rel.props
    return LinkRow(
        rel.type,
        rel.id,
        rel.source,
        rel.target,
        p.get("share_pct_min"),
        p.get("share_pct_max"),
        bool(p.get("share_min_exclusive", False)),
        bool(p.get("share_max_exclusive", False)),
        bool(p.get("is_nominee", False)),
        p.get("role") or p.get("relationship") or "",
        p.get("start_date") or "",
        p.get("end_date") or "",
        p.get("control_type") or "",
    )


class MemSource:
    def __init__(self, graph: MemGraph) -> None:
        self.graph = graph

    # helpers ---------------------------------------------------------------------------------

    def _ledger(self, account: str) -> bool:
        """A bank's cash ledger (C1 `account_kind` cash_ledger): the counterparty of cash deposits
        and withdrawals, never a candidate account and never a hop of a path."""
        return bool(self.graph.node(account).get("account_kind") == "cash_ledger")

    def _holders(self, account: str) -> tuple[str, ...]:
        return tuple(n.id for n in self.graph.holders(account))

    def _entity_row(self, node_id: str) -> EntityRow:
        n = self.graph.node(node_id)
        return EntityRow(
            n.id,
            tuple(sorted(n.labels)),
            n.get("schema", ""),
            n.get("jurisdiction") or "",
            n.get("incorporation_date") or "",
            n.synthetic,
            n.get("accounts_category") or "",
            n.get("sector") or "",
            n.get("status") or "",
            n.get("dissolution_date") or "",
            tuple(n.get("datasets", ())),
            tuple(n.get("psc_statements", ())),
            n.get("full") or "",
            n.get("postal_code") or "",
            n.get("city") or "",
            tuple(n.get("countries", ())),
        )

    # common ----------------------------------------------------------------------------------

    def paid_time_range(self) -> tuple[datetime, datetime] | None:
        times = [r.props["ts"] for r in self.graph.rels("PAID")]
        return (min(times), max(times)) if times else None

    def node_info(self, ids: Iterable[str]) -> dict[str, NodeInfo]:
        """Evidence nodes and the holders of evidence accounts, with what the policy needs."""
        out: dict[str, NodeInfo] = {}
        wanted = sorted(set(ids))
        for node_id in wanted:
            n = self.graph.node(node_id)
            holders = self._holders(node_id) if "Account" in n.labels else ()
            out[node_id] = NodeInfo(
                n.id,
                n.labels,
                n.get("caption", n.id),
                n.synthetic,
                tuple(n.get("datasets", ())),
                holders,
            )
            for h in holders:
                if h not in out:
                    hn = self.graph.node(h)
                    out[h] = NodeInfo(
                        hn.id,
                        hn.labels,
                        hn.get("caption", hn.id),
                        hn.synthetic,
                        tuple(hn.get("datasets", ())),
                        (),
                    )
        return out

    def edge_info(self, ids: Iterable[str]) -> dict[str, EdgeInfo]:
        """The evidence relationships with their ends and the properties the wording uses."""
        out = {}
        for rel_id in sorted(set(ids)):
            r = self.graph.rel(rel_id)
            q = r.props
            out[rel_id] = EdgeInfo(
                r.id,
                r.type,
                r.source,
                r.target,
                r.synthetic,
                float(q["amount"]) if q.get("amount") is not None else None,
                q.get("currency") or "",
                q.get("ts"),
                q.get("channel") or "",
                q.get("share_pct_min"),
                q.get("share_pct_max"),
                bool(q.get("share_min_exclusive", False)),
                bool(q.get("share_max_exclusive", False)),
                q.get("role") or q.get("relationship") or "",
                q.get("control_type") or "",
                q.get("start_date") or "",
                q.get("end_date") or "",
            )
        return out

    def paid_starts(
        self, min_amount: float, start: datetime, end: datetime, limit: int
    ) -> list[Hop]:
        hops = []
        for rel in self.graph.rels("PAID"):
            ts = rel.props["ts"]
            if self._ledger(rel.source) or self._ledger(rel.target):
                continue
            if float(rel.props["amount"]) >= min_amount and start <= ts < end:
                hops.append(
                    Hop(
                        rel.id,
                        rel.source,
                        rel.target,
                        ts,
                        float(rel.props["amount"]),
                        rel.props["currency"],
                        self._holders(rel.source),
                        self._holders(rel.target),
                    )
                )
        hops.sort(key=lambda h: (h.ts, h.edge_id))
        return hops[:limit]

    def paid_hop(self, frontier: Sequence[FrontierItem]) -> dict[int, list[Hop]]:
        found: dict[int, list[Hop]] = {}
        for item in frontier:
            hops = []
            for rel in self.graph.out_rels(item.account, "PAID"):
                ts = rel.props["ts"]
                amount = float(rel.props["amount"])
                if not (item.after < ts <= item.until):
                    continue
                if not (item.min_amount <= amount <= item.max_amount):
                    continue
                if (
                    rel.props["currency"] != item.currency
                    or rel.target in item.visited
                    or self._ledger(rel.target)
                ):
                    continue
                hops.append(
                    Hop(
                        rel.id,
                        rel.source,
                        rel.target,
                        ts,
                        amount,
                        rel.props["currency"],
                        (),
                        self._holders(rel.target),
                    )
                )
            hops.sort(key=lambda h: (h.ts, h.edge_id))
            if hops:
                found[item.key] = hops
        return found

    # flow typologies -------------------------------------------------------------------------

    def _flows(self, account: str, start: datetime, end: datetime) -> AccountFlows:
        ins = sorted(
            _pay(r, r.source)
            for r in self.graph.in_rels(account, "PAID")
            if start <= r.props["ts"] < end
        )
        outs = sorted(
            _pay(r, r.target)
            for r in self.graph.out_rels(account, "PAID")
            if start <= r.props["ts"] < end
        )
        return AccountFlows(account, self._holders(account), tuple(ins), tuple(outs))

    def flows_by_inbound(
        self,
        min_inbound_counterparties: int,
        start: datetime,
        end: datetime,
        channel: str | None,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        """Accounts other than cash ledgers with at least `min_inbound_counterparties` distinct
        paying accounts in one bucket of `bucket_hours` (buckets counted from `start`; payments of
        `channel` only, when given), with every payment in and out in [start, end), by account id.
        A window of `bucket_hours` with 2k payers puts k of them in one bucket, so a detector asks
        for half its threshold and loses nothing."""
        out = []
        width = bucket_hours * 3600
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            buckets: dict[int, set[str]] = defaultdict(set)
            for r in self.graph.in_rels(acct.id, "PAID"):
                ts = r.props["ts"]
                if start <= ts < end and (channel is None or r.props.get("channel") == channel):
                    buckets[int((ts - start).total_seconds() // width)].add(r.source)
            if any(len(v) >= min_inbound_counterparties for v in buckets.values()):
                out.append(self._flows(acct.id, start, end))
        return out[:limit]

    def flows_by_outbound(
        self,
        min_outbound_counterparties: int,
        start: datetime,
        end: datetime,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]:
        """As `flows_by_inbound`, counting distinct payees."""
        out = []
        width = bucket_hours * 3600
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            buckets: dict[int, set[str]] = defaultdict(set)
            for r in self.graph.out_rels(acct.id, "PAID"):
                ts = r.props["ts"]
                if start <= ts < end:
                    buckets[int((ts - start).total_seconds() // width)].add(r.target)
            if any(len(v) >= min_outbound_counterparties for v in buckets.values()):
                out.append(self._flows(acct.id, start, end))
        return out[:limit]

    def counterparty_info(self, accounts: Iterable[str]) -> dict[str, CounterpartyInfo]:
        out = {}
        for a in sorted(set(accounts)):
            n = self.graph.node(a)
            holders = self.graph.holders(a)
            labels = sorted({lab for h in holders for lab in h.labels})
            out[a] = CounterpartyInfo(
                a, n.get("opening_date") or "", tuple(labels), tuple(h.id for h in holders)
            )
        return out

    def paid_times(
        self, pairs: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[datetime, ...]]:
        """For each (payer account, payee account), the times of every PAID between them, sorted;
        pairs with no payment are left out."""
        out = {}
        for a, b in sorted(set(pairs)):
            times = sorted(r.props["ts"] for r in self.graph.out_rels(a, "PAID") if r.target == b)
            if times:
                out[(a, b)] = tuple(times)
        return out

    def payments_from(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        out = {}
        for a in sorted(set(accounts)):
            pays = sorted(
                _pay(r, r.target)
                for r in self.graph.out_rels(a, "PAID")
                if start <= r.props["ts"] < end
            )
            if pays:
                out[a] = pays
        return out

    def payments_into(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]:
        """Each account's incoming payments in [start, end), in order of (ts, id)."""
        out: dict[str, list[Pay]] = {}
        for a in sorted(set(accounts)):
            pays = [
                _pay(r, r.source)
                for r in self.graph.in_rels(a, "PAID")
                if start <= r.props["ts"] < end
            ]
            if pays:
                out[a] = sorted(pays)
        return out

    def payments_among(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> list[tuple[str, str, str]]:
        """(edge id, payer account, payee account) for PAID between two of `accounts` in the
        period, by edge id."""
        wanted = set(accounts)
        rows = []
        for a in sorted(wanted):
            for r in self.graph.out_rels(a, "PAID"):
                if r.target in wanted and start <= r.props["ts"] < end:
                    rows.append((r.id, r.source, r.target))
        return sorted(rows)

    def activity_counts(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, int]:
        """Number of PAID relationships into or out of each account in the period."""
        out = {}
        for a in sorted(set(accounts)):
            n = sum(1 for r in self.graph.in_rels(a, "PAID") if start <= r.props["ts"] < end)
            n += sum(1 for r in self.graph.out_rels(a, "PAID") if start <= r.props["ts"] < end)
            out[a] = n
        return out

    def holder_cash_deposits(
        self,
        band_low: float,
        threshold: float,
        min_in_band: int,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[HolderDeposits]:
        """Holders whose accounts received at least `min_in_band` cash deposits of band_low to
        threshold (both included: the detector applies each currency's edge) in the period, with
        every cash deposit of the period into any of their accounts, in time order. By holder id."""
        out = []
        for holder in self.graph.nodes("LegalEntity"):
            deposits = []
            for acct in self.graph.accounts(holder.id):
                for r in self.graph.in_rels(acct.id, "PAID"):
                    if r.props.get("channel") == "cash_deposit" and start <= r.props["ts"] < end:
                        deposits.append(
                            Deposit(
                                r.props["ts"],
                                r.id,
                                acct.id,
                                r.source,
                                float(r.props["amount"]),
                                r.props["currency"],
                            )
                        )
            if sum(1 for d in deposits if band_low <= d.amount <= threshold) >= min_in_band:
                out.append(HolderDeposits(holder.id, tuple(sorted(deposits))))
        return out[:limit]

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
        """Accounts with a quiet period that ends with a payment in [start, end): at least
        `min_gap_days` from a payment, or from the opening date when that is on or after
        `history_start` (the date of the first payment in the data, so the account's whole life is
        loaded), to that payment, with at most `max_quiet_payments` payments between them totalling
        at most `max_quiet_amount`. Each with every payment of the account before `end`, in order
        of (ts, id); accounts by id."""
        out = []
        gap = timedelta(days=min_gap_days)
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            pays: list[tuple[Pay, str]] = []
            for r in self.graph.in_rels(acct.id, "PAID"):
                if r.props["ts"] < end:
                    pays.append((_pay(r, r.source), "in"))
            for r in self.graph.out_rels(acct.id, "PAID"):
                if r.props["ts"] < end:
                    pays.append((_pay(r, r.target), "out"))
            if not pays:
                continue
            pays.sort(key=lambda x: (x[0].ts, x[0].edge_id))
            ts = [x.ts for x, _ in pays]
            amt = [x.amount for x, _ in pays]
            opening = acct.get("opening_date") or ""
            opened = None
            if len(opening) == 10 and opening >= history_start:
                opened = datetime.fromisoformat(opening).replace(tzinfo=ts[0].tzinfo)
            found = False
            for j in range(len(pays)):
                if not start <= ts[j] < end:
                    continue
                for m in range(max_quiet_payments + 1):
                    k = j - m - 1
                    if k < 0:
                        break
                    if ts[j] - ts[k] >= gap and sum(amt[k + 1 : j]) <= max_quiet_amount:
                        found = True
                        break
                if (
                    not found
                    and opened is not None
                    and j <= max_quiet_payments
                    and sum(amt[:j]) <= max_quiet_amount
                    and ts[j] - opened >= gap
                ):
                    found = True
                if found:
                    break
            if found:
                out.append(AccountHistory(acct.id, opening, self._holders(acct.id), tuple(pays)))
        return out[:limit]

    def company_account_histories(
        self, incorporated_since: str, start: datetime, end: datetime, min_payments: int, limit: int
    ) -> list[AccountHistory]:
        """Accounts held by a company whose accounts category is DORMANT, or that was incorporated
        on or after `incorporated_since`, with at least `min_payments` payments in the period
        (those payments only, in time order)."""
        out = []
        for acct in self.graph.nodes("Account"):
            if self._ledger(acct.id):
                continue
            holders = self.graph.holders(acct.id)
            if not any(
                "Company" in h.labels
                and (
                    (h.get("accounts_category") or "").upper() == "DORMANT"
                    or (
                        len(h.get("incorporation_date") or "") == 10
                        and h.get("incorporation_date") >= incorporated_since
                    )
                )
                for h in holders
            ):
                continue
            pays: list[tuple[Pay, str]] = []
            for r in self.graph.in_rels(acct.id, "PAID"):
                if start <= r.props["ts"] < end:
                    pays.append((_pay(r, r.source), "in"))
            for r in self.graph.out_rels(acct.id, "PAID"):
                if start <= r.props["ts"] < end:
                    pays.append((_pay(r, r.target), "out"))
            if len(pays) >= min_payments:
                pays.sort(key=lambda x: (x[0].ts, x[0].edge_id))
                out.append(
                    AccountHistory(
                        acct.id,
                        acct.get("opening_date") or "",
                        tuple(h.id for h in holders),
                        tuple(pays),
                    )
                )
        return out[:limit]

    def recent_account_components(
        self, new_days: int, start: datetime, end: datetime, min_size: int
    ) -> list[Component]:
        """Weakly connected components of the PAID relationships in [start, end) whose two accounts
        were both opened at most `new_days` before the payment (accounts with a full ISO opening
        date, cash ledgers excluded); components of at least `min_size` accounts, each with its
        accounts sorted, ordered by their smallest account id. The reference for GDS WCC on the
        same projection (queries/recent_account_components.cypher)."""
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def new_at(account_id: str, ts: datetime) -> bool:
            opened = self.graph.node(account_id).get("opening_date") or ""
            if len(opened) != 10 or self._ledger(account_id):
                return False
            return 0 <= (ts.date() - datetime.fromisoformat(opened).date()).days <= new_days

        edges = []
        for r in self.graph.rels("PAID"):
            ts = r.props["ts"]
            if start <= ts < end and new_at(r.source, ts) and new_at(r.target, ts):
                edges.append(r)
                for x in (r.source, r.target):
                    parent.setdefault(x, x)
                a, b = find(r.source), find(r.target)
                if a != b:
                    parent[max(a, b)] = min(a, b)
        groups: dict[str, list[str]] = defaultdict(list)
        for x in parent:
            groups[find(x)].append(x)
        out = []
        for members in groups.values():
            if len(members) < min_size:
                continue
            member_set = set(members)
            comp_edges = sorted(
                PaidEdge(
                    r.props["ts"],
                    r.id,
                    r.source,
                    r.target,
                    float(r.props["amount"]),
                    r.props["currency"],
                    r.props.get("channel") or "",
                )
                for r in edges
                if r.source in member_set
            )
            out.append(Component(tuple(sorted(members)), tuple(comp_edges)))
        return sorted(out, key=lambda c: c.accounts[0])

    # registry --------------------------------------------------------------------------------

    def entities(self, ids: Iterable[str]) -> dict[str, EntityRow]:
        return {i: self._entity_row(i) for i in sorted(set(ids))}

    def links_into(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        """Registry relationships of `types` that end at each id, by relationship id."""
        out: dict[str, list[LinkRow]] = defaultdict(list)
        for i in sorted(set(ids)):
            for r in self.graph.in_rels(i, *types):
                out[i].append(_link(r))
            out[i].sort(key=lambda link: link.rel_id)
        return dict(out)

    def links_from(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]:
        out: dict[str, list[LinkRow]] = defaultdict(list)
        for i in sorted(set(ids)):
            for r in self.graph.out_rels(i, *types):
                out[i].append(_link(r))
            out[i].sort(key=lambda link: link.rel_id)
        return dict(out)

    def appointment_counts(self, people: Iterable[str], as_of: str) -> dict[str, int]:
        """Number of DIRECTOR_OF relationships each id starts that still hold on `as_of`."""
        return {
            p: sum(1 for r in self.graph.out_rels(p, "DIRECTOR_OF") if _current(r, as_of))
            for p in sorted(set(people))
        }

    def _owns(self, node_id: str, as_of: str, into: bool = False) -> list[Rel]:
        rels = self.graph.in_rels(node_id, "OWNS") if into else self.graph.out_rels(node_id, "OWNS")
        return [r for r in rels if _current(r, as_of)]

    def ownership_paths(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        """Maximal paths of 1 to `max_hops` OWNS relationships that still hold on `as_of`, from a
        top (a node no such OWNS points to) to a leaf Company (one that owns no Organization
        through one), never repeating a node. Ordered by the node ids along the path."""
        out: list[OwnershipPath] = []
        g = self.graph

        def owns_org(n: str) -> list[Rel]:
            return [r for r in self._owns(n, as_of) if "Organization" in g.node(r.target).labels]

        tops = [
            n.id
            for n in g.nodes("LegalEntity")
            if not self._owns(n.id, as_of, into=True) and owns_org(n.id)
        ]

        def walk(path: list[str], links: list[Rel]) -> None:
            last = path[-1]
            nexts = [r for r in owns_org(last) if r.target not in path]
            if links and "Company" in g.node(last).labels and not owns_org(last):
                out.append(OwnershipPath(tuple(path), tuple(_link(r) for r in links)))
            if len(links) >= max_hops:
                return
            for r in nexts:
                walk([*path, r.target], [*links, r])

        for top in tops:
            walk([top], [])
        out.sort(key=lambda x: x.nodes)
        return out[:limit]

    def ownership_cycles(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]:
        """Simple cycles of 2 to `max_hops` OWNS relationships that still hold on `as_of`, each
        once, starting at its smallest node id; nodes[0] == nodes[-1]."""
        out: list[OwnershipPath] = []
        g = self.graph

        def walk(origin: str, path: list[str], links: list[Rel]) -> None:
            for r in self._owns(path[-1], as_of):
                if r.target == origin and len(links) + 1 >= 2:
                    out.append(OwnershipPath((*path, origin), tuple(_link(x) for x in [*links, r])))
                elif r.target > origin and r.target not in path and len(links) + 1 < max_hops:
                    walk(origin, [*path, r.target], [*links, r])

        for start in g.nodes("LegalEntity"):
            walk(start.id, [start.id], [])
        out.sort(key=lambda x: x.nodes)
        return out[:limit]

    def _active(self, node_id: str) -> bool:
        n = self.graph.node(node_id)
        return not n.get("dissolution_date") and (n.get("status") or "").casefold() not in INACTIVE

    def _registered(self, address: str, active_only: bool) -> list[tuple[str, str]]:
        return sorted(
            (r.source, r.id)
            for r in self.graph.in_rels(address, "HAS_ADDRESS")
            if r.props.get("role") == "registered"
            and "Organization" in self.graph.node(r.source).labels
            and (not active_only or self._active(r.source))
        )

    def registered_clusters(
        self, min_members: int, active_only: bool, limit: int
    ) -> list[AddressCluster]:
        """Addresses with at least `min_members` organisations whose HAS_ADDRESS role is
        registered (with `active_only`, organisations without a dissolution date whose status is
        not an inactive one), ordered by address id."""
        out = []
        for addr in self.graph.nodes("Address"):
            members = self._registered(addr.id, active_only)
            if len(members) >= min_members:
                out.append(
                    AddressCluster(
                        addr.id,
                        addr.get("full") or "",
                        addr.get("postal_code") or "",
                        tuple(members),
                    )
                )
        return out[:limit]

    def registered_count_quantile(self, q: float, active_only: bool) -> int:
        """The nearest-rank `q` quantile of the number of registered organisations per address,
        over addresses with at least one: the value at position max(1, ceil(q * n)) in ascending
        order; 0 when no address has one."""
        counts = sorted(
            c
            for c in (len(self._registered(a.id, active_only)) for a in self.graph.nodes("Address"))
            if c > 0
        )
        if not counts:
            return 0
        return counts[max(1, math.ceil(q * len(counts))) - 1]

    def hubs(self, rel_type: str, min_members: int, limit: int) -> list[Hub]:
        """Nodes with relationships of `rel_type` (REPRESENTS or DIRECTOR_OF) to at least
        `min_members` distinct organisations, by node id, each with those relationships by id."""
        if rel_type not in ("REPRESENTS", "DIRECTOR_OF"):
            raise ValueError(f"not a hub relationship: {rel_type}")
        by_source: dict[str, list[Rel]] = defaultdict(list)
        for r in self.graph.rels(rel_type):
            if "Organization" in self.graph.node(r.target).labels:
                by_source[r.source].append(r)
        out = []
        for source in sorted(by_source):
            rels = by_source[source]
            if len({r.target for r in rels}) >= min_members:
                out.append(
                    Hub(source, tuple(sorted((_link(r) for r in rels), key=lambda x: x.rel_id)))
                )
        return out[:limit]

    def cash_profiles(
        self, prior_start: datetime, start: datetime, end: datetime, currency: str, limit: int
    ) -> list[CashProfile]:
        """Companies whose accounts received cash deposits in `currency` in [prior_start, end):
        sums in pence (each amount rounded to pence first) and counts for [start, end) and for
        [prior_start, start), the sector, and the postcode and city of the registered address (the
        smallest postcode when there are several). By holder id."""
        out = []
        for c in self.graph.nodes("Company"):
            accounts = set()
            win = win_n = prior = prior_n = 0
            for h in self.graph.out_rels(c.id, "HOLDS_ACCOUNT"):
                for r in self.graph.in_rels(h.target, "PAID"):
                    ts = r.props["ts"]
                    if r.props.get("channel") != "cash_deposit" or r.props["currency"] != currency:
                        continue
                    if not prior_start <= ts < end:
                        continue
                    accounts.add(h.target)
                    pence = round(float(r.props["amount"]) * 100)
                    if ts >= start:
                        win += pence
                        win_n += 1
                    else:
                        prior += pence
                        prior_n += 1
            if not accounts:
                continue
            addresses = sorted(
                (
                    self.graph.node(r.target).get("postal_code") or "",
                    self.graph.node(r.target).get("city") or "",
                )
                for r in self.graph.out_rels(c.id, "HAS_ADDRESS")
                if r.props.get("role") == "registered"
            )
            postal, city = addresses[0] if addresses else ("", "")
            out.append(
                CashProfile(
                    c.id,
                    c.get("sector") or "",
                    postal,
                    city,
                    tuple(sorted(accounts)),
                    win,
                    win_n,
                    prior,
                    prior_n,
                )
            )
        return out[:limit]

    def listed_entities(self) -> list[ListedRow]:
        """Every :Sanctioned entity with its labels, datasets and the :Sanction nodes it is
        SUBJECT_OF (by sanction id), ordered by entity id."""
        out = []
        for e in self.graph.nodes("Sanctioned"):
            sanctions = []
            for r in self.graph.out_rels(e.id, "SUBJECT_OF"):
                s = self.graph.node(r.target)
                sanctions.append(
                    SanctionRow(
                        s.id,
                        tuple(s.get("datasets", ())),
                        s.get("authority") or "",
                        s.get("program") or "",
                        tuple(s.get("provisions", ())),
                        s.get("start_date") or "",
                        s.get("end_date") or "",
                    )
                )
            sanctions.sort(key=lambda x: x.id)
            out.append(
                ListedRow(
                    e.id, tuple(sorted(e.labels)), tuple(e.get("datasets", ())), tuple(sanctions)
                )
            )
        return out

    def flagged_ids(self, flag: str) -> list[str]:
        """Ids of the :Entity nodes with one flag label (Sanctioned, PEP or RCA), sorted."""
        if flag not in ("Sanctioned", "PEP", "RCA"):
            raise ValueError(f"not a flag label: {flag}")
        return [n.id for n in self.graph.nodes(flag)]
