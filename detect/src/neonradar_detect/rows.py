"""Typed rows that candidate steps return (PHASE-3.md 7.1.2).

Each `Source` method (source.py) returns these, sorted as documented, whether it ran a query file
on Neo4j (`neo4jsource.py`) or the reference code on a `MemGraph` (`memsource.py`). The parity
test compares the two implementations row for row, so every field is a plain value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, order=True)
class Pay:
    """One PAID relationship seen from an account: `counterparty` is the other account."""

    ts: datetime
    edge_id: str
    counterparty: str
    amount: float
    currency: str
    channel: str


@dataclass(frozen=True, slots=True)
class Hop:
    edge_id: str
    source: str
    target: str
    ts: datetime
    amount: float
    currency: str
    source_holders: tuple[str, ...]
    target_holders: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AccountFlows:
    """An account with its payments in a period, for the flow typologies."""

    account: str
    holders: tuple[str, ...]
    inflows: tuple[Pay, ...]
    outflows: tuple[Pay, ...]


@dataclass(frozen=True, slots=True)
class CounterpartyInfo:
    account: str
    opening_date: str
    holder_labels: tuple[str, ...]
    holders: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AccountHistory:
    """Every payment of one account up to the end of the period, for dormancy."""

    account: str
    opening_date: str
    holders: tuple[str, ...]
    payments: tuple[tuple[Pay, str], ...]  # (payment, "in" or "out"), in time order


@dataclass(frozen=True, slots=True)
class LinkRow:
    """A registry relationship: type, id, ends and the C2 properties a detector reads."""

    rel_type: str
    rel_id: str
    source: str
    target: str
    share_min: float | None = None
    share_max: float | None = None
    share_min_exclusive: bool = False
    share_max_exclusive: bool = False
    is_nominee: bool = False
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    control_type: str = ""

    def current(self, as_of: str) -> bool:
        """Whether the relationship still holds on `as_of` (an ISO date): no end date, or one
        after it. Partial dates compare as text, so "2026" counts as ended by "2026-07-01"."""
        return not (self.end_date and self.end_date <= as_of)


@dataclass(frozen=True, slots=True)
class EntityRow:
    id: str
    labels: tuple[str, ...]
    schema: str
    jurisdiction: str
    incorporation_date: str
    synthetic: bool
    accounts_category: str = ""
    sector: str = ""
    status: str = ""
    dissolution_date: str = ""
    datasets: tuple[str, ...] = ()
    psc_statements: tuple[str, ...] = ()
    full: str = ""  # addresses only
    postal_code: str = ""  # addresses only
    city: str = ""  # addresses only
    countries: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, order=True)
class Deposit:
    """A cash deposit into one of a holder's accounts; `branch` is the paying cash ledger."""

    ts: datetime
    edge_id: str
    account: str
    branch: str
    amount: float
    currency: str


@dataclass(frozen=True, slots=True)
class HolderDeposits:
    holder: str
    deposits: tuple[Deposit, ...]


@dataclass(frozen=True, slots=True, order=True)
class PaidEdge:
    ts: datetime
    edge_id: str
    source: str
    target: str
    amount: float
    currency: str
    channel: str


@dataclass(frozen=True, slots=True)
class Component:
    """A weakly connected component of a projected payment graph: accounts and their PAID edges."""

    accounts: tuple[str, ...]
    edges: tuple[PaidEdge, ...]


@dataclass(frozen=True, slots=True)
class OwnershipPath:
    """OWNS relationships in order from the first node to the last: nodes[i] owns nodes[i + 1]."""

    nodes: tuple[str, ...]
    links: tuple[LinkRow, ...]


@dataclass(frozen=True, slots=True)
class AddressCluster:
    address: str
    full: str
    postal_code: str
    members: tuple[tuple[str, str], ...]  # (organisation id, HAS_ADDRESS relationship id), by id


@dataclass(frozen=True, slots=True)
class SanctionRow:
    """A :Sanction node an entity is SUBJECT_OF (C2; `provisions` is new in C2 1.2.0)."""

    id: str
    datasets: tuple[str, ...]
    authority: str
    program: str
    provisions: tuple[str, ...]
    start_date: str
    end_date: str


@dataclass(frozen=True, slots=True)
class ListedRow:
    """A :Sanctioned entity with its own datasets and its designations, by sanction id."""

    entity: str
    labels: tuple[str, ...]
    datasets: tuple[str, ...]
    sanctions: tuple[SanctionRow, ...]


@dataclass(frozen=True, slots=True)
class Hub:
    """A node with many relationships of one type (REPRESENTS or DIRECTOR_OF) to organisations."""

    hub: str
    links: tuple[LinkRow, ...]  # by relationship id


@dataclass(frozen=True, slots=True)
class CashProfile:
    """One company's cash deposits in a currency: the window and the period before it, in pence."""

    holder: str
    sector: str
    postal_code: str  # of the registered address ("" when none)
    city: str
    accounts: tuple[str, ...]
    window_pence: int
    window_deposits: int
    prior_pence: int
    prior_deposits: int
