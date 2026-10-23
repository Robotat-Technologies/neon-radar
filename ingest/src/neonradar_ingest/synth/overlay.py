"""The overlay of generator v1: background activity, scenarios and look-alikes on a base
(PHASE-3.md 7.2.7).

`generate` reads nothing and writes nothing: it takes the base's records (any iterable, so the CLI
can stream them from the base's files), returns the overlay's records and labels, and the CLI
writes them (`writer.py`, `labels.py`). The same seed and the same
base give the same records and labels, byte for byte once written. Scenario ids are numbered in
catalog order (`scn-000001` upwards); each scenario draws from its own named stream, so adding a
typology at the end changes no earlier scenario.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from itertools import chain
from pathlib import Path
from types import ModuleType
from typing import Any

from neonradar_ingest.synth import background, writer
from neonradar_ingest.synth.base import BaseView
from neonradar_ingest.synth.ctx import Ctx, LabelRows, NameSource, ScenarioCtx
from neonradar_ingest.synth.dates import Period
from neonradar_ingest.synth.scenarios import (
    cash_commingling,
    circular_flow,
    dormant_reactivation,
    fan_in_collection,
    fan_out_distribution,
    formation_agent_cluster,
    layering_chain,
    mass_registration_address,
    pep_exposure,
    rapid_pass_through,
    recycled_directors,
    sanctions_exposure,
    shell_chain,
    structuring,
)

SCENARIOS: dict[str, ModuleType] = {
    m.TYPOLOGY: m
    for m in (
        structuring,
        rapid_pass_through,
        layering_chain,
        circular_flow,
        fan_in_collection,
        fan_out_distribution,
        dormant_reactivation,
        shell_chain,
        mass_registration_address,
        sanctions_exposure,
        formation_agent_cluster,
        recycled_directors,
        pep_exposure,
        cash_commingling,
    )
}
HISTORY_DAYS = 100  # transaction scenarios start after the detectors' 90-day look-back has data


@dataclass(frozen=True, slots=True)
class OverlayConfig:
    seed: int
    start: date = date(2025, 1, 1)
    end: date = date(2026, 7, 1)
    split: str = "dev"
    illicit: int = 10
    lookalikes: int = 10
    typologies: tuple[str, ...] = tuple(SCENARIOS)
    background: background.BackgroundConfig = field(default_factory=background.BackgroundConfig)


@dataclass(slots=True)
class Overlay:
    """The overlay's records and labels. Payments stay as their C1 lines: `items()` gives every
    record's schema and line in id order (the writer), and `records` parses them into dicts in id
    order (the in-memory graph of small worlds, and the tests)."""

    other_records: dict[str, dict[str, Any]]  # every record except payments
    payments: dict[str, str]  # payment id -> C1 line
    labels: LabelRows
    stats: dict[str, Any]

    def _ids(self) -> list[str]:
        return sorted(self.other_records.keys() | self.payments.keys())

    def items(self) -> Iterator[tuple[str, str]]:
        for rid in self._ids():
            text = self.payments.get(rid)
            if text is not None:
                yield "Payment", text
            else:
                record = self.other_records[rid]
                yield str(record["schema"]), writer.line(record)

    @property
    def records(self) -> list[dict[str, Any]]:
        return [
            self.other_records[rid] if rid in self.other_records else json.loads(self.payments[rid])
            for rid in self._ids()
        ]


def _start(ctx: Ctx, module: ModuleType, scenario_id: str) -> date:
    """A start day that leaves the scenario's lead time and history before it and its span after."""
    rng = ctx.rng("place", scenario_id)
    first = ctx.period.start.date() + timedelta(days=max(module.LEAD_DAYS, HISTORY_DAYS))
    last = ctx.period.end.date() - timedelta(days=module.SPAN_DAYS + 7)
    if last <= first:
        raise ValueError(f"the period is too short for {module.TYPOLOGY}")
    return first + timedelta(days=int(rng.integers(0, (last - first).days + 1)))


def generate(
    base_records: Iterable[Mapping[str, Any]],
    dataset_kinds: Mapping[str, str],
    cfg: OverlayConfig,
    names: NameSource,
    canonical_csv: Path | None = None,
) -> Overlay:
    """`canonical_csv` is the base's latest resolution run (`canonical.csv`), when the profile
    resolves: a merged entity then gets one account, through its anchor record, and none when any
    of its records is flagged or comes from a list or a leak (`BaseView`)."""
    view = BaseView.from_records(base_records, dataset_kinds, canonical_csv)
    period = Period(
        datetime.combine(cfg.start, datetime.min.time(), UTC),
        datetime.combine(cfg.end, datetime.min.time(), UTC),
    )
    ctx = Ctx(
        cfg.seed,
        period,
        names,
        base_ids=view.ids,
        base_names=view.names,
        soft_names=view.synthetic_names,
    )
    ctx.split = cfg.split
    bg = background.generate(ctx, view.eligible, cfg.background)
    counts: dict[str, dict[str, int]] = {}
    n = 0
    for slug, module in SCENARIOS.items():
        if slug not in cfg.typologies:
            continue
        counts[slug] = {"illicit": 0, "lookalike": 0}
        for i in range(cfg.illicit):
            n += 1
            sid = f"scn-{n:06d}"
            variant, difficulty = module.ILLICIT[i % len(module.ILLICIT)]
            module.illicit(
                ScenarioCtx(ctx, sid, slug, lookalike=False),
                variant,
                difficulty,
                _start(ctx, module, sid),
            )
            counts[slug]["illicit"] += 1
        for i in range(cfg.lookalikes):
            n += 1
            sid = f"scn-{n:06d}"
            kind = module.LOOKALIKES[i % len(module.LOOKALIKES)]
            module.lookalike(
                ScenarioCtx(ctx, sid, slug, lookalike=True), kind, _start(ctx, module, sid)
            )
            counts[slug]["lookalike"] += 1
    ctx.assign_account_numbers(view.account_numbers)
    check_bridge(
        chain(ctx.records.values(), (json.loads(text) for text in ctx.payments.values())),
        view.ids,
        ctx.base_accounts,
        {org.id for org in view.eligible},
    )
    stats = {
        "background": bg,
        "scenarios": counts,
        "eligible": len(view.eligible),
        "skipped": dict(view.skipped),
        "records": len(ctx.records) + len(ctx.payments),
    }
    return Overlay(ctx.records, ctx.payments, ctx.labels, stats)


# Every FtM property the generator writes that names another entity (PHASE-3.md 7.2.3).
REFERENCE_PROPERTIES = (
    "owner",
    "asset",
    "director",
    "organization",
    "agent",
    "client",
    "person",
    "relative",
    "associate",
    "controller",
    "controlled",
    "entity",
    "holder",
    "post",
    "addressEntity",
)


def check_bridge(
    records: Iterable[Mapping[str, Any]],
    base_ids: frozenset[str] | set[str],
    base_accounts: set[str],
    eligible: Iterable[str] = (),
) -> None:
    """I15 and I16 on the overlay's own records: the only record that names a base entity is the
    account holding of a base organisation (`base_accounts` are the accounts such holdings
    hold), a payment names a base entity only as the payer or beneficiary of one of those
    accounts, and no payment joins two of them. Every property that can name an entity counts,
    `addressEntity` included. A holding's base owner must be one of the `eligible` organisations,
    and no payment names a base record as an account (M3.3 review)."""
    allowed = frozenset(eligible)
    for r in records:
        p = r["properties"]
        if r["schema"] == "Payment":
            if {p["payerAccount"][0], p["beneficiaryAccount"][0]} & base_ids:
                raise ValueError(f"payment {r['id']} names a base record as an account (I15)")
            if (
                p["payerAccount"][0] in base_accounts
                and p["beneficiaryAccount"][0] in base_accounts
            ):
                raise ValueError(f"payment {r['id']} joins two base holders (I16)")
            for party, account in (
                ("payer", "payerAccount"),
                ("beneficiary", "beneficiaryAccount"),
            ):
                if set(p.get(party, [])) & base_ids and p[account][0] not in base_accounts:
                    raise ValueError(f"payment {r['id']} names a base entity (I15)")
            continue
        named = {v for key in REFERENCE_PROPERTIES for v in p.get(key, [])}
        if not named.isdisjoint(base_ids):
            holding = (
                r["schema"] == "Ownership"
                and p.get("role") == ["account holder"]
                and p["asset"][0] in base_accounts
                and set(p["owner"]) <= allowed
            )
            if not holding:
                raise ValueError(f"record {r['id']} links a base entity (I15)")
