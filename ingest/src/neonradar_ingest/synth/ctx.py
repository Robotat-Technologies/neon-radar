"""The generation context of generator v1 (PHASE-3.md 7.2.3).

`Ctx` owns everything an overlay writes: records by id (payments, nine in ten of them, kept as
their C1 lines so that a scale world fits in memory), the holder of every new account, the names
already used, the bank branches and the background counterparties. Background code may pay the
accounts of base organisations; scenario code works through `ScenarioCtx`, which refuses any
record that touches a base entity or a base entity's account (G1, D3 in 7.2.4), so a scenario can
only ever involve entities it created itself.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

import numpy as np

from neonradar_ingest.synth import records as rec
from neonradar_ingest.synth.companies import name_key as company_name_key
from neonradar_ingest.synth.dates import Period
from neonradar_ingest.synth.streams import stream
from neonradar_ingest.synth.writer import line

Record = dict[str, Any]


class NameSource(Protocol):
    """Names for new synthetic people and companies (M3.3 adapts the Phase 1 name modules)."""

    def person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        """All spellings of one invented person's name, and a gender ("male" or "female")."""
        ...

    def invented_person(self, rng: np.random.Generator, locale: str) -> tuple[list[str], str]:
        """The same with an invented surname, for every person a scenario creates and for
        people on synthetic lists, PEP personas and their relatives and associates, so that no
        realistic full name is ever flagged or put in a scenario role (PHASE-2.md M2.9)."""
        ...

    def company(self, rng: np.random.Generator, jurisdiction: str) -> str: ...

    def street(self, rng: np.random.Generator) -> str: ...

    def town(self, rng: np.random.Generator) -> str: ...


FLAG_TOPICS = frozenset({"sanction", "role.pep", "role.rca"})
PERSONA_LOCALES = ("en_GB", "ar_SA", "ru_RU")


def letter(rng: np.random.Generator) -> str:
    return chr(65 + int(rng.integers(26)))


def name_key(name: str) -> str:
    """The comparison form for name collisions: NFC, case-folded, punctuation and spaces
    collapsed, and legal forms at either end removed, so "X Ltd" collides with "X LIMITED"
    (Phase 1's `companies.name_key`; M3.3 review)."""
    return company_name_key(name)


@dataclass(slots=True)
class LabelRows:
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    participants: list[dict[str, Any]] = field(default_factory=list)
    params: list[dict[str, Any]] = field(default_factory=list)


class Ctx:
    def __init__(
        self,
        seed: int,
        period: Period,
        names: NameSource,
        *,
        base_ids: Iterable[str] = (),
        base_names: Iterable[str] = (),
        soft_names: Iterable[str] = (),
        currency: str = "GBP",
    ) -> None:
        self.seed = seed
        self.period = period
        self.names = names
        self.currency = currency
        self.records: dict[str, Record] = {}  # every record except payments
        self.payments: dict[str, str] = {}  # payment id -> its C1 line
        self.holder_of: dict[str, str] = {}
        self.base_ids = frozenset(base_ids)
        self.base_accounts: set[str] = set()
        self.base_name_keys = frozenset(name_key(n) for n in base_names)
        self.used_names = set(self.base_name_keys) | {name_key(n) for n in soft_names}
        self.branches: list[str] = []
        self.labels = LabelRows()
        self.split = "dev"
        self._company_numbers: set[str] = set()

    # streams and ids ---------------------------------------------------------------------------

    def rng(self, *keys: str) -> np.random.Generator:
        return stream(self.seed, *keys)

    def rid(self, namespace: str, key: str) -> str:
        rid = rec.hashed_id(namespace, self.seed, key)
        if rid in self.records or rid in self.payments:
            raise ValueError(f"id collision for {namespace}:{key}")
        return rid

    def add(self, record: Record) -> str:
        rid = str(record["id"])
        if rid in self.records or rid in self.payments:
            raise ValueError(f"duplicate record id {rid}")
        if record["schema"] == "Payment":
            self.payments[rid] = line(record)
        else:
            self.records[rid] = record
        return rid

    def record(self, rid: str) -> Record:
        """Any record of this overlay; a payment is parsed back from its line."""
        found = self.records.get(rid)
        if found is not None:
            return found
        parsed: Record = json.loads(self.payments[rid])
        return parsed

    # entities ----------------------------------------------------------------------------------

    def _unique(self, make: Any, attempts: int = 50) -> Any:
        """A name that no base record uses (PHASE-1.md 7.1, synthetic-join mode) and, when one turns
        up within `attempts` draws, that no synthetic record uses yet; after that a synthetic
        repeat is accepted, because a large world can exhaust the word lists (real registers
        repeat names too). Only the name stream moves, so structure never depends on it."""
        for i in range(2 * attempts):
            value = make()
            names = value[0] if isinstance(value, tuple) else [value]
            keys = [name_key(n) for n in names]
            if any(k in self.base_name_keys for k in keys):
                continue
            if i >= attempts or not any(k in self.used_names for k in keys):
                self.used_names.update(keys)
                return value
        raise RuntimeError("could not find a name that no base record uses")

    def company_number(self, rng: np.random.Generator) -> str:
        """`SY9` plus five digits: the overlay range of synthetic company numbers (7.2.2)."""
        for _ in range(1000):
            number = f"SY9{int(rng.integers(0, 100_000)):05d}"
            if number not in self._company_numbers:
                self._company_numbers.add(number)
                return number
        raise RuntimeError("synthetic company numbers exhausted")

    def address(self, key: str, *, country: str = "gb", district: str = "") -> str:
        """A new address; `district` fixes the postcode district (outward code), else one of QQ1 to
        QQ98. QQ is not a UK postcode area, so no synthetic postcode is a real one."""
        rng = self.rng("address", key)
        number = int(rng.integers(1, 200))
        outward = district or f"QQ{int(rng.integers(1, 99))}"
        postcode = f"{outward} {int(rng.integers(1, 9))}{letter(rng)}{letter(rng)}"
        name_rng = self.rng("address-name", key)  # names never move a structural draw
        street = self.names.street(name_rng)
        town = self.names.town(name_rng)
        full = f"{number} {street}, {town}, {postcode}"
        rid = self.rid("addr", key)
        return self.add(rec.address(rid, full, city=town, postal_code=postcode, country=country))

    def company(
        self,
        key: str,
        *,
        jurisdiction: str = "gb",
        incorporated: date,
        sector: str = "",
        address: str = "",
        accounts_category: str = "",
        topics: tuple[str, ...] = (),
    ) -> str:
        rng = self.rng("company", key)
        name_rng = self.rng("company-name", key)
        name = self._unique(lambda: self.names.company(name_rng, jurisdiction))
        rid = self.rid("co", key)
        record = rec.company(
            rid,
            name,
            jurisdiction=jurisdiction,
            registration_number=self.company_number(rng),
            incorporation_date=incorporated.isoformat(),
            addresses={address: "registered"} if address else None,
            sector=sector,
            topics=list(topics),
        )
        if accounts_category:
            record["nr"]["accounts_category"] = accounts_category
        return self.add(record)

    def organization(
        self, key: str, name: str, *, country: str = "gb", topics: tuple[str, ...] = ()
    ) -> str:
        if name_key(name) in self.used_names:
            raise ValueError(f"name already used: {name}")
        self.used_names.add(name_key(name))
        return self.add(
            rec.organization(self.rid("org", key), name, country=country, topics=list(topics))
        )

    def person(
        self,
        key: str,
        *,
        locale: str = "en_GB",
        nationality: str = "gb",
        born: tuple[int, int] = (1950, 2004),
        topics: tuple[str, ...] = (),
        invented: bool = False,
    ) -> str:
        """A synthetic person. A person with a list, PEP or RCA topic, or `invented`, gets an
        invented surname; `locale="any"` lets the name stream choose the script."""
        rng = self.rng("person", key)
        name_rng = self.rng("person-name", key)
        if locale == "any":
            locale = str(name_rng.choice(PERSONA_LOCALES))
        if invented or set(topics) & FLAG_TOPICS:
            names, gender = self._unique(lambda: self.names.invented_person(name_rng, locale))
        else:
            names, gender = self._unique(lambda: self.names.person(name_rng, locale))
        year = int(rng.integers(born[0], born[1] + 1))
        month = int(rng.integers(1, 13))
        rid = self.rid("p", key)
        return self.add(
            rec.person(
                rid,
                names,
                birth_date=f"{year:04d}-{month:02d}",
                nationality=nationality,
                gender=gender,
                topics=list(topics),
            )
        )

    def account(
        self,
        key: str,
        holder: str,
        *,
        opened: date,
        currency: str = "",
        kind: str = "customer",
        bank: str = "",
    ) -> str:
        rid = self.rid("acct", key)
        self.add(
            rec.account(
                rid,
                "NRSYN0000000000",  # replaced by assign_account_numbers() before writing
                bank_name=bank or "Synthetic Bank One",
                currency=currency or self.currency,
                opening_date=opened.isoformat(),
                kind=kind,
            )
        )
        self.add(rec.holding(self.rid("hold", key), holder, rid))
        self.holder_of[rid] = holder
        if holder in self.base_ids:
            self.base_accounts.add(rid)
        return rid

    # relationships -----------------------------------------------------------------------------

    def pay(
        self,
        key: str,
        src: str,
        dst: str,
        amount: float,
        moment: datetime,
        *,
        channel: str = "wire",
        purpose: str = "",
        currency: str = "",
    ) -> str:
        if not self.period.start <= moment < self.period.end:
            raise ValueError(f"payment {key} at {moment} lies outside the period")
        rid = self.rid("pay", key)
        return self.add(
            rec.payment(
                rid,
                payer=self.holder_of[src],
                beneficiary=self.holder_of[dst],
                payer_account=src,
                beneficiary_account=dst,
                amount=amount,
                currency=currency or self._currency_of(src),
                moment=moment,
                channel=channel,
                purpose=purpose,
            )
        )

    def _currency_of(self, account: str) -> str:
        return str(self.records[account]["properties"]["currency"][0])

    def owns(
        self,
        key: str,
        owner: str,
        asset: str,
        *,
        band: str,
        start: date | None = None,
        nominee: bool = False,
    ) -> str:
        return self.add(
            rec.ownership(
                self.rid("own", key),
                owner,
                asset,
                band=band,
                start_date=start.isoformat() if start else "",
                nominee=nominee,
            )
        )

    def director(
        self,
        key: str,
        person: str,
        org: str,
        *,
        start: date,
        end: date | None = None,
        nominee: bool = False,
    ) -> str:
        return self.add(
            rec.directorship(
                self.rid("dir", key),
                person,
                org,
                start_date=start.isoformat(),
                end_date=end.isoformat() if end else "",
                nominee=nominee,
            )
        )

    def represents(self, key: str, agent: str, client: str) -> str:
        return self.add(rec.representation(self.rid("rep", key), agent, client))

    def family(self, key: str, person: str, relative: str, relationship: str) -> str:
        return self.add(
            rec.family(self.rid("fam", key), person, relative, relationship=relationship)
        )

    def control(
        self,
        key: str,
        controller: str,
        controlled: str,
        *,
        control_type: str = "influence",
        band: str = "",
    ) -> str:
        """A PSC control: `control_type` is a C2 measure (voting, appointment, influence); `band` a
        voting band ("25-50", "50-75", "75-100") for `voting`."""
        return self.add(
            rec.control(
                self.rid("ctl", key), controller, controlled, control_type=control_type, band=band
            )
        )

    def associate(self, key: str, person: str, other: str, relationship: str) -> str:
        return self.add(
            rec.associate(self.rid("assoc", key), person, other, relationship=relationship)
        )

    def position(self, key: str, name: str, *, country: str) -> str:
        return self.add(rec.position(self.rid("pos", key), name, country=country))

    def occupancy(
        self, key: str, person: str, position: str, *, start: date, end: date | None = None
    ) -> str:
        return self.add(
            rec.occupancy(
                self.rid("occ", key),
                person,
                position,
                start_date=start.isoformat(),
                end_date=end.isoformat() if end else "",
            )
        )

    def consolidates(self, key: str, parent: str, child: str) -> str:
        return self.add(rec.consolidation(self.rid("cons", key), parent, child))

    def sanction(self, key: str, entity: str, *, start: date) -> str:
        return self.add(
            rec.sanction(
                self.rid("san", key),
                entity,
                authority="Synthetic Authority A",
                program="Synthetic Programme 1",
                start_date=start.isoformat(),
            )
        )

    # finishing ---------------------------------------------------------------------------------

    def assign_account_numbers(self, taken: Iterable[str] = ()) -> None:
        """Give every new account a stable `NRSYN` number: 10 digits from a hash of its id, the next
        free number on a collision, in id order (R8)."""
        used = set(taken)
        for rid in sorted(r for r, x in self.records.items() if x["schema"] == "BankAccount"):
            value = int(hashlib.sha256(f"{self.seed}|{rid}".encode()).hexdigest(), 16) % 10**10
            while f"NRSYN{value:010d}" in used:
                value = (value + 1) % 10**10
            number = f"NRSYN{value:010d}"
            used.add(number)
            self.records[rid]["properties"]["accountNumber"] = [number]


class ScenarioCtx:
    """What a scenario module may do: create its own entities, link them, pay between them.

    Every id a scenario passes must be one it created (or a bank branch ledger); anything else is a
    programming error and raises, so no scenario can reach a base entity (G1)."""

    def __init__(self, ctx: Ctx, scenario_id: str, typology: str, *, lookalike: bool) -> None:
        self.ctx = ctx
        self.scenario_id = scenario_id
        self.typology = typology
        self.lookalike = lookalike
        self.created: set[str] = set()
        # Payments and relationships it made: kept apart from `created`, which a scenario module
        # may read (cash_commingling keys a stream on its size), so owning them moves no draw.
        # Only a label may name one; an endpoint never may (`_check` is the code book's).
        self.links: set[str] = set()
        self.core_payments: list[tuple[str, str, bool]] = []  # (payment id, role, is_core)
        self.roles: dict[str, tuple[str, bool]] = {}  # object id -> (role, is_core)
        self._n = 0

    def rng(self, *keys: str) -> np.random.Generator:
        return self.ctx.rng("scenario", self.scenario_id, *keys)

    def _key(self, kind: str) -> str:
        self._n += 1
        return f"{self.scenario_id}|{kind}|{self._n}"

    def _check(self, *ids: str) -> None:
        for i in ids:
            if i not in self.created and i not in self.ctx.branches:
                raise PermissionError(f"scenario {self.scenario_id} may not use {i}")

    def _check_label(self, object_id: str) -> None:
        """A label may also name a payment or relationship this scenario made (M3.3 review S1)."""
        if object_id not in self.links:
            self._check(object_id)

    def _own(self, rid: str) -> str:
        self.created.add(rid)
        return rid

    def _link(self, rid: str) -> str:
        self.links.add(rid)
        return rid

    @property
    def period(self) -> Period:
        return self.ctx.period

    def address(self, *, country: str = "gb", district: str = "") -> str:
        return self._own(self.ctx.address(self._key("addr"), country=country, district=district))

    def company(self, **kw: Any) -> str:
        if kw.get("address"):
            self._check(kw["address"])
        return self._own(self.ctx.company(self._key("co"), **kw))

    def person(self, **kw: Any) -> str:
        """Scenario people carry invented surnames (M3.3 review: no realistic name in a role)."""
        return self._own(self.ctx.person(self._key("p"), **(kw | {"invented": True})))

    def organization(self, name: str, **kw: Any) -> str:
        return self._own(self.ctx.organization(self._key("org"), name, **kw))

    def account(
        self, holder: str, *, opened: date, currency: str = "", kind: str = "customer"
    ) -> str:
        self._check(holder)
        return self._own(
            self.ctx.account(self._key("acct"), holder, opened=opened, currency=currency, kind=kind)
        )

    def pay(self, src: str, dst: str, amount: float, moment: datetime, **kw: Any) -> str:
        self._check(src, dst)
        return self._link(self.ctx.pay(self._key("pay"), src, dst, amount, moment, **kw))

    def owns(self, owner: str, asset: str, **kw: Any) -> str:
        self._check(owner, asset)
        return self._link(self.ctx.owns(self._key("own"), owner, asset, **kw))

    def director(self, person: str, org: str, **kw: Any) -> str:
        self._check(person, org)
        return self._link(self.ctx.director(self._key("dir"), person, org, **kw))

    def represents(self, agent: str, client: str) -> str:
        self._check(agent, client)
        return self._link(self.ctx.represents(self._key("rep"), agent, client))

    def family(self, person: str, relative: str, relationship: str = "sibling") -> str:
        self._check(person, relative)
        return self._link(self.ctx.family(self._key("fam"), person, relative, relationship))

    def control(self, controller: str, controlled: str, **kw: Any) -> str:
        self._check(controller, controlled)
        return self._link(self.ctx.control(self._key("ctl"), controller, controlled, **kw))

    def associate(self, person: str, other: str, relationship: str = "business partner") -> str:
        self._check(person, other)
        return self._link(self.ctx.associate(self._key("assoc"), person, other, relationship))

    def position(self, name: str, *, country: str) -> str:
        return self._own(self.ctx.position(self._key("pos"), name, country=country))

    def occupancy(self, person: str, position: str, *, start: date, end: date | None = None) -> str:
        self._check(person, position)
        return self._link(
            self.ctx.occupancy(self._key("occ"), person, position, start=start, end=end)
        )

    def consolidates(self, parent: str, child: str) -> str:
        self._check(parent, child)
        return self._link(self.ctx.consolidates(self._key("cons"), parent, child))

    def sanction(self, entity: str, *, start: date) -> str:
        self._check(entity)
        return self._link(self.ctx.sanction(self._key("san"), entity, start=start))

    # labels ------------------------------------------------------------------------------------

    def label_payment(self, payment_id: str, role: str, *, core: bool = True) -> str:
        """Mark a payment as part of the pattern (labels/transactions.csv)."""
        if payment_id not in self.ctx.payments:
            raise ValueError(f"not a payment of this overlay: {payment_id}")
        self._check_label(payment_id)  # only a payment this scenario made (G1)
        self.core_payments.append((payment_id, role, core))
        return payment_id

    def label(self, object_id: str, role: str, *, core: bool = True) -> str:
        """Mark a participant with its role (labels/participants.csv): an entity, account or
        address this scenario created, or a relationship record between two of them."""
        record = self.ctx.records.get(object_id)
        self._check_label(object_id)  # anything this scenario did not create is refused (G1)
        if record is None:
            raise ValueError(f"unknown object {object_id}")
        self.roles[object_id] = (role, core)
        return object_id

    def finish(
        self,
        variant: str,
        difficulty: str,
        params: dict[str, Any],
        expected: dict[str, Any] | None = None,
    ) -> None:
        if not self.roles:
            raise ValueError(f"scenario {self.scenario_id} labelled no participant")
        records = self.ctx.records
        dates = {p: self.ctx.record(p)["properties"]["date"][0] for p, _, _ in self.core_payments}
        pays = sorted(self.core_payments, key=lambda x: (dates[x[0]], x[0]))
        times = [dates[p] for p, _, _ in pays]
        kinds = {oid: object_kind(records[oid]) for oid in self.roles}
        self.ctx.labels.scenarios.append(
            {
                "scenario_id": self.scenario_id,
                "typology": self.typology,
                "variant": variant,
                "is_lookalike": self.lookalike,
                "start_ts": min(times) if times else "",
                "end_ts": max(times) if times else "",
                "participants": "",
                "difficulty": difficulty,
                "split": self.ctx.split,
                "n_transactions": len({p for p, _, _ in pays}),
                "n_accounts": sum(1 for k in kinds.values() if k == "account"),
                "n_entities": sum(1 for k in kinds.values() if k == "entity"),
                "n_relationships": sum(1 for k in kinds.values() if k == "relationship"),
            }
        )
        for step, (payment_id, role, core) in enumerate(pays, 1):
            self.ctx.labels.transactions.append(
                {
                    "tx_id": payment_id,
                    "scenario_id": self.scenario_id,
                    "typology": self.typology,
                    "step": step,
                    "role": role,
                    "is_illicit": not self.lookalike,
                    "variant": variant,
                    "is_lookalike": self.lookalike,
                    "is_core": core,
                }
            )
        for object_id, (role, core) in sorted(self.roles.items()):
            self.ctx.labels.participants.append(
                {
                    "scenario_id": self.scenario_id,
                    "object_kind": kinds[object_id],
                    "object_id": c2_id(records[object_id]),
                    "role": role,
                    "is_core": core,
                }
            )
        self.ctx.labels.params.append(
            {
                "scenario_id": self.scenario_id,
                "params": params,
                "expected_metrics": expected or {},
                "stream_key": ["scenario", self.scenario_id],
                "generator": {
                    "component": f"scenarios.{self.typology}",
                    "version": GENERATOR_VERSION,
                },
            }
        )


RELATIONSHIP_SCHEMAS = frozenset(
    {"Ownership", "Control", "Directorship", "Representation", "Family", "Associate", "Occupancy"}
)
GENERATOR_VERSION = "1.0.0"


def object_kind(record: Record) -> str:
    schema = record["schema"]
    if schema == "BankAccount":
        return "account"
    if schema == "Address":
        return "address"
    if schema in RELATIONSHIP_SCHEMAS:
        return "relationship"
    return "entity"


def c2_id(record: Record) -> str:
    """The C2 id of a labelled object: the record id (FtM interval entity id for relationships)."""
    return str(record["id"])
