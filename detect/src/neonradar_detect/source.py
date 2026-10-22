"""The candidate steps every detector may use (PHASE-3.md 7.1.2).

A detector never talks to Neo4j directly. It calls methods of a `Source`: `Neo4jSource` runs the
query file of the same name in `queries/`, `MemSource` runs the reference code on a `MemGraph`.
Both return the typed rows of `rows.py` in the documented order, so detector logic is plain
Python that unit tests run without a database, and the parity test proves the two sources agree.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from neonradar_detect.expand import FrontierItem
from neonradar_detect.model import EdgeInfo, Finding, NodeInfo
from neonradar_detect.rows import (
    AccountFlows,
    AccountHistory,
    AddressCluster,
    CashProfile,
    Component,
    CounterpartyInfo,
    EntityRow,
    HolderDeposits,
    Hop,
    Hub,
    LinkRow,
    ListedRow,
    OwnershipPath,
    Pay,
)


@dataclass(frozen=True, slots=True)
class Window:
    """The detection period: payments with start <= ts < end."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("window bounds must be timezone-aware (UTC)")
        if not self.start < self.end:
            raise ValueError("window start must be before its end")


@dataclass(slots=True)
class DetectorOutput:
    findings: list[Finding]
    stats: dict[str, int] = field(default_factory=dict)


class Source(Protocol):
    def paid_time_range(self) -> tuple[datetime, datetime] | None: ...

    def node_info(self, ids: Iterable[str]) -> dict[str, NodeInfo]: ...

    def edge_info(self, ids: Iterable[str]) -> dict[str, EdgeInfo]: ...

    def paid_starts(
        self, min_amount: float, start: datetime, end: datetime, limit: int
    ) -> list[Hop]: ...

    def paid_hop(self, frontier: Sequence[FrontierItem]) -> dict[int, list[Hop]]: ...

    def flows_by_inbound(
        self,
        min_inbound_counterparties: int,
        start: datetime,
        end: datetime,
        channel: str | None,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]: ...

    def flows_by_outbound(
        self,
        min_outbound_counterparties: int,
        start: datetime,
        end: datetime,
        bucket_hours: int,
        limit: int,
    ) -> list[AccountFlows]: ...

    def counterparty_info(self, accounts: Iterable[str]) -> dict[str, CounterpartyInfo]: ...

    def paid_times(
        self, pairs: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[datetime, ...]]: ...

    def payments_from(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]: ...

    def payments_into(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, list[Pay]]: ...

    def payments_among(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> list[tuple[str, str, str]]: ...

    def activity_counts(
        self, accounts: Iterable[str], start: datetime, end: datetime
    ) -> dict[str, int]: ...

    def holder_cash_deposits(
        self,
        band_low: float,
        threshold: float,
        min_in_band: int,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[HolderDeposits]: ...

    def quiet_account_histories(
        self,
        min_gap_days: int,
        max_quiet_payments: int,
        max_quiet_amount: float,
        history_start: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[AccountHistory]: ...

    def company_account_histories(
        self, incorporated_since: str, start: datetime, end: datetime, min_payments: int, limit: int
    ) -> list[AccountHistory]: ...

    def recent_account_components(
        self, new_days: int, start: datetime, end: datetime, min_size: int
    ) -> list[Component]: ...

    def entities(self, ids: Iterable[str]) -> dict[str, EntityRow]: ...

    def links_into(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]: ...

    def links_from(self, ids: Iterable[str], types: Sequence[str]) -> dict[str, list[LinkRow]]: ...

    def appointment_counts(self, people: Iterable[str], as_of: str) -> dict[str, int]: ...

    def ownership_paths(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]: ...

    def ownership_cycles(self, max_hops: int, limit: int, as_of: str) -> list[OwnershipPath]: ...

    def registered_clusters(
        self, min_members: int, active_only: bool, limit: int
    ) -> list[AddressCluster]: ...

    def registered_count_quantile(self, q: float, active_only: bool) -> int: ...

    def hubs(self, rel_type: str, min_members: int, limit: int) -> list[Hub]: ...

    def cash_profiles(
        self, prior_start: datetime, start: datetime, end: datetime, currency: str, limit: int
    ) -> list[CashProfile]: ...

    def listed_entities(self) -> list[ListedRow]: ...

    def flagged_ids(self, flag: str) -> list[str]: ...
