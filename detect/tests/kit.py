"""Builds small C1 record sets for detector fixtures and unit tests (PHASE-3.md 7.4).

Every id is synthetic (`syn-fx-...`) unless a test asks for a non-synthetic look-alike with
`real=True`, which gives a `gb_companies_house` record built at run time (PHASE-2.md 2.9: such
records are never committed). Times are UTC strings `YYYY-MM-DDTHH:MM`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from neonradar_detect import catalog, runner
from neonradar_detect.graphrows import from_records
from neonradar_detect.memsource import MemSource
from neonradar_detect.source import Source, Window

Record = dict[str, Any]


def _memory(records: list[Record]) -> Source:
    return MemSource(from_records(records))


# How detector tests turn records into a Source. With NR_DETECT_SOURCE=neo4j, the conftest
# replaces it with a factory that loads the records into a test database and returns a
# Neo4jSource, so the same tests check the Cypher candidate steps (M3.2).
SOURCE_FACTORY: Callable[[list[Record]], Source] = _memory


def source_of(records: list[Record]) -> Source:
    return SOURCE_FACTORY(records)


WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def detect(records: list[Record], params: Mapping[str, Any]) -> runner.RunResult:
    """Run the given typologies through the runner with the catalog, as `detect run` does."""
    return runner.run_detection(
        source_of(records),
        params,
        WINDOW,
        catalog.load(),
        run_id="run-20261102T090000-0001",
        created_at=datetime(2026, 11, 2, 9, 0, tzinfo=UTC),
    )


PREFIXES = {
    "nr_synthetic": "syn",
    "gb_companies_house": "gbch",
    "gb_fcdo_sanctions": "uksl",
    "us_ofac_sdn": "ofac",
    "eu_fsf": "eufsf",
    "un_sc_sanctions": "unsc",
    "icij_offshore_leaks": "icij",
}
BANDS = {
    "25-50": (25.0, 50.0, True, False, "ownership-of-shares-25-to-50-percent"),
    "50-75": (50.0, 75.0, True, True, "ownership-of-shares-50-to-75-percent"),
    "75-100": (75.0, 100.0, False, False, "ownership-of-shares-75-to-100-percent"),
}


def _nr(kind: str, **extra: Any) -> dict[str, Any]:
    return {"v": "1.1", "synthetic": True, "synthetic_kind": kind, **extra}


class Kit:
    def __init__(self) -> None:
        self.records: list[Record] = []
        self._holder: dict[str, str] = {}
        self._n = 0

    def _add(
        self,
        rid: str,
        schema: str,
        props: dict[str, list[str]],
        nr: dict[str, Any] | None,
        real: bool,
        dataset: str = "",
    ) -> str:
        real = real or bool(dataset and dataset != "nr_synthetic")
        record: Record = {
            "id": rid,
            "schema": schema,
            "datasets": [dataset or ("gb_companies_house" if real else "nr_synthetic")],
            "properties": {k: v for k, v in props.items() if v},
        }
        nr = nr or _nr("registry")
        if real:
            # a non-synthetic record never sets nr.synthetic (C1 R6); keep its other nr keys
            nr = {k: v for k, v in nr.items() if k not in ("synthetic", "synthetic_kind")}
            if len(nr) > 1:
                record["nr"] = nr
        else:
            record["nr"] = nr
        self.records.append(record)
        return rid

    def _next(self, kind: str) -> str:
        self._n += 1
        return f"syn-fx-{kind}-{self._n:05d}"

    # entities ------------------------------------------------------------------------------

    def company(
        self,
        cid: str,
        name: str = "",
        *,
        jurisdiction: str = "gb",
        incorporated: str = "2015-01-01",
        sector: str = "",
        real: bool = False,
        topics: tuple[str, ...] = (),
        address: str = "",
        accounts_category: str = "",
        dataset: str = "",
        psc_statements: tuple[str, ...] = (),
    ) -> str:
        real = real or bool(dataset and dataset != "nr_synthetic")
        rid = cid if real else f"syn-fx-co-{cid}"
        props = {
            "name": [name or f"Fixture {cid} Ltd"],
            "jurisdiction": [jurisdiction],
            "incorporationDate": [incorporated],
            "sector": [sector] if sector else [],
            "topics": sorted(topics),
            "addressEntity": [address] if address else [],
        }
        extra: dict[str, Any] = {"address_roles": {address: "registered"}} if address else {}
        if accounts_category:
            extra["accounts_category"] = accounts_category
        if psc_statements:
            extra["psc_statements"] = list(psc_statements)
        return self._add(rid, "Company", props, _nr("registry", **extra), real, dataset)

    def person(
        self,
        pid: str,
        name: str = "",
        *,
        real: bool = False,
        topics: tuple[str, ...] = (),
        dataset: str = "",
    ) -> str:
        real = real or bool(dataset and dataset != "nr_synthetic")
        rid = pid if real else f"syn-fx-p-{pid}"
        props = {"name": [name or f"Fixture Person {pid}"], "topics": sorted(topics)}
        return self._add(rid, "Person", props, _nr("registry"), real, dataset)

    def legal_entity(
        self, lid: str, name: str = "", *, real: bool = False, dataset: str = ""
    ) -> str:
        """A legal entity whose kind the source does not state (an ICIJ officer, say)."""
        real = real or bool(dataset and dataset != "nr_synthetic")
        rid = lid if real else f"syn-fx-le-{lid}"
        props = {"name": [name or f"Fixture Entity {lid}"]}
        return self._add(rid, "LegalEntity", props, _nr("registry"), real, dataset)

    def sanction(
        self,
        entity: str,
        dataset: str = "nr_synthetic",
        *,
        provisions: tuple[str, ...] = (),
        authority: str = "Fixture Authority",
        end: str = "",
    ) -> str:
        """A designation of `entity` on the list `dataset` (a non-synthetic dataset gives a
        look-alike record built at run time, never committed)."""
        props = {
            "entity": [entity],
            "authority": [authority],
            "provisions": list(provisions),
            "endDate": [end] if end else [],
        }
        rid = self._next("sanction")
        if dataset != "nr_synthetic":
            rid = f"{PREFIXES[dataset]}-sanction-T{rid.rsplit('-', 1)[1]}"
        return self._add(rid, "Sanction", props, _nr("list"), False, dataset)

    def address(self, aid: str, full: str = "") -> str:
        rid = f"syn-fx-addr-{aid}"
        return self._add(
            rid,
            "Address",
            {"full": [full or f"{aid} Fixture Street, QQ1 1QQ"], "country": ["gb"]},
            None,
            False,
        )

    def account(
        self,
        aid: str,
        holder: str,
        *,
        currency: str = "GBP",
        opened: str = "2024-01-01",
        kind: str = "customer",
    ) -> str:
        rid = f"syn-fx-acct-{aid}"
        self._n += 1
        number = f"NRSYN{self._n:010d}"
        props = {
            "accountNumber": [number],
            "bankName": ["Fixture Bank"],
            "currency": [currency],
            "openingDate": [opened],
        }
        self._add(rid, "BankAccount", props, _nr("activity", account_kind=kind), False)
        self._add(
            f"syn-fx-hold-{aid}",
            "Ownership",
            {"owner": [holder], "asset": [rid], "role": ["account holder"]},
            _nr("activity"),
            False,
        )
        self._holder[rid] = holder
        return rid

    def hold(self, holder: str, account_id: str) -> None:
        """A second holder for an existing account."""
        self._add(
            self._next("hold"),
            "Ownership",
            {"owner": [holder], "asset": [account_id], "role": ["account holder"]},
            _nr("activity"),
            False,
        )

    # links ---------------------------------------------------------------------------------

    def pay(
        self,
        src: str,
        dst: str,
        amount: float,
        when: str,
        *,
        channel: str = "wire",
        currency: str = "GBP",
        pid: str = "",
    ) -> str:
        rid = pid or self._next("pay")
        moment = datetime.strptime(when, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%dT%H:%M:%S")
        props = {
            "payer": [self._holder[src]],
            "beneficiary": [self._holder[dst]],
            "payerAccount": [src],
            "beneficiaryAccount": [dst],
            "amount": [f"{amount:.2f}"],
            "currency": [currency],
            "date": [moment],
        }
        return self._add(rid, "Payment", props, _nr("activity", channel=channel), False)

    def owns(
        self,
        owner: str,
        asset: str,
        band: str = "75-100",
        *,
        nominee: bool = False,
        start: str = "",
        end: str = "",
    ) -> str:
        """`band` is a PSC band ("25-50", "50-75", "75-100") or an exact share ("exact:40");
        `end` is the date the holding ceased."""
        if band.startswith("exact:"):
            value = float(band.split(":", 1)[1])
            low, high, low_x, high_x, nature = value, value, False, False, ""
        else:
            low, high, low_x, high_x, nature = BANDS[band]
        extra: dict[str, Any] = {"share_pct_min": low, "share_pct_max": high}
        if nature:
            extra["natures_of_control"] = [nature]
        if low_x:
            extra["share_pct_min_exclusive"] = True
        if high_x:
            extra["share_pct_max_exclusive"] = True
        if nominee:
            extra["is_nominee"] = True
        props = {
            "owner": [owner],
            "asset": [asset],
            "percentage": [band.removeprefix("exact:")],
            "role": [nature] if nature else [],
            "startDate": [start] if start else [],
            "endDate": [end] if end else [],
        }
        return self._add(self._next("own"), "Ownership", props, _nr("registry", **extra), False)

    def director(
        self,
        person_id: str,
        company_id: str,
        *,
        start: str = "2020-01-01",
        end: str = "",
        nominee: bool = False,
    ) -> str:
        props = {
            "director": [person_id],
            "organization": [company_id],
            "role": ["director"],
            "startDate": [start],
            "endDate": [end] if end else [],
        }
        extra = {"is_nominee": True} if nominee else {}
        return self._add(self._next("dir"), "Directorship", props, _nr("registry", **extra), False)

    def represents(self, agent: str, client: str) -> str:
        props = {"agent": [agent], "client": [client], "role": ["formation agent"]}
        return self._add(self._next("rep"), "Representation", props, None, False)

    def family(self, person_id: str, relative: str, relationship: str = "sibling") -> str:
        props = {"person": [person_id], "relative": [relative], "relationship": [relationship]}
        return self._add(self._next("fam"), "Family", props, None, False)

    def controls(
        self,
        controller: str,
        controlled: str,
        control_type: str = "influence",
        band: str = "",
        *,
        start: str = "",
        end: str = "",
    ) -> str:
        """A PSC control (C2 `control_type`: voting, appointment, influence, trust-or-firm,
        nominee); `band` gives a voting band ("25-50", "50-75", "75-100")."""
        props = {
            "controller": [controller],
            "controlled": [controlled],
            "controlType": [control_type],
            "startDate": [start] if start else [],
            "endDate": [end] if end else [],
        }
        extra: dict[str, Any] = {}
        if band:
            low, high, low_x, high_x, _ = BANDS[band]
            extra = {
                "natures_of_control": [f"voting-rights-{band.replace('-', '-to-')}-percent"],
                "share_pct_min": low,
                "share_pct_max": high,
            }
            if low_x:
                extra["share_pct_min_exclusive"] = True
            if high_x:
                extra["share_pct_max_exclusive"] = True
        return self._add(self._next("ctl"), "Control", props, _nr("registry", **extra), False)

    def consolidates(self, parent: str, child: str) -> str:
        props = {"owner": [parent], "asset": [child], "role": ["consolidation"]}
        return self._add(
            self._next("cons"), "Ownership", props, _nr("registry", consolidation="ultimate"), False
        )

    def associate(self, person_id: str, other: str, relationship: str = "business partner") -> str:
        props = {"person": [person_id], "associate": [other], "relationship": [relationship]}
        return self._add(self._next("assoc"), "Associate", props, None, False)

    def position(self, pid: str, name: str = "", *, country: str = "zz") -> str:
        props = {"name": [name or f"Fixture Office {pid}"], "country": [country]}
        return self._add(f"syn-fx-pos-{pid}", "Position", props, None, False)

    def occupancy(
        self, person_id: str, position_id: str, *, start: str = "2020-01-01", end: str = ""
    ) -> str:
        props = {
            "holder": [person_id],
            "post": [position_id],
            "startDate": [start],
            "endDate": [end] if end else [],
        }
        return self._add(self._next("occ"), "Occupancy", props, None, False)

    def address_at(self, aid: str, full: str, postcode: str, city: str = "Fixture Town") -> str:
        """An address with a postcode and a city (area peer groups, PO boxes, default addresses)."""
        rid = self.address(aid, full)
        record = next(r for r in self.records if r["id"] == rid)
        record["properties"]["postalCode"] = [postcode]
        record["properties"]["city"] = [city]
        return rid

    def history(self, when: str = "2025-10-01T10:00") -> str:
        """One unrelated payment that starts the data's history at `when`: detectors that judge
        earlier relationships skip windows less than their look-back after the first payment."""
        a = self.account("hist-a", self.company("hist-a"))
        b = self.account("hist-b", self.company("hist-b"))
        return self.pay(a, b, 100.0, when)
