"""Circular flow detector: payments that return to the account they left (PHASE-1.md M1.9b).

Typology `circular_flow` (detect/typologies/circular_flow.yaml, docs/typologies/circular-flow.md).
The query (queries/circular_flow.cypher) finds directed cycles of `PAID` relationships that
start and end at the same `:Account`, with `min_hops` to `max_hops` payments, each payment
strictly later than the one before it (so a cycle is found once, from the account where it
starts), no account visited twice on the way, the first payment to the last within
`max_window_days`, and a return ratio (last amount over first amount, in one currency) of at
least `min_return_ratio`. The variant that returns to another account of the same holder is
Phase 3 work.

Pattern strength orders the review queue; it is a heuristic, not a risk score:

    pattern_strength = 0.5 x return_ratio
                     + 0.3 x (1 - duration_hours / (max_window_days x 24))
                     + 0.2 x min(1, (cycle_length - 1) / 4)

clipped to [0, 1] and rounded to two decimals, computed from the reported metrics. A cycle
that returns more of the sent amount, closes faster and passes through more accounts matches
the graph pattern more closely.
"""

import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from neo4j import Driver, RoutingControl

from neonradar_detect.alerts import EdgeFact, Finding, Step, entity_fact
from neonradar_detect.catalog import TypologyFile
from neonradar_detect.wording import MetricValue, cycle_summary, payment_step

logger = logging.getLogger(__name__)

NAME = __name__
VERSION = "0.1.0"
QUERY_FILE = Path(__file__).resolve().parents[1] / "queries" / "circular_flow.cypher"
QUANTIFIER = "->{MIN_HOPS,MAX_HOPS}("
HOP_LIMIT = 8  # PHASE-1.md 5.2: every traversal at most 8 hops
MAX_RESULTS = 1000
LABEL_MAX = 64  # account labels in explanation texts, so a step stays within 280 characters


@dataclass(frozen=True, slots=True)
class Parameters:
    """The typology parameters of one run, checked against the catalog's ranges."""

    min_hops: int
    max_hops: int
    max_window_days: int | float
    min_return_ratio: int | float


def resolve_parameters(
    typology: TypologyFile, overrides: Mapping[str, int | float] | None = None
) -> Parameters:
    """The catalog defaults, with `overrides` checked against the catalog's `min` and `max`."""
    overrides = dict(overrides or {})
    unknown = sorted(
        set(overrides) - {"min_hops", "max_hops", "max_window_days", "min_return_ratio"}
    )
    if unknown:
        raise ValueError(f"unknown circular_flow parameters: {unknown}")
    values: dict[str, int | float] = {}
    for name, spec in sorted(typology.parameters.items()):
        value = overrides.get(name, spec.default)
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
        ):
            raise ValueError(f"parameter {name} must be a finite number, not {value!r}")
        if (spec.min is not None and value < spec.min) or (
            spec.max is not None and value > spec.max
        ):
            raise ValueError(f"parameter {name}={value} is outside [{spec.min}, {spec.max}]")
        values[name] = value
    hops = (values["min_hops"], values["max_hops"])
    if not all(isinstance(value, int) for value in hops):
        raise ValueError(f"min_hops and max_hops must be integers, not {hops}")
    return Parameters(
        min_hops=int(hops[0]),
        max_hops=int(hops[1]),
        max_window_days=values["max_window_days"],
        min_return_ratio=values["min_return_ratio"],
    )


def query(min_hops: int, max_hops: int) -> str:
    """The detection query for one hop range, from the fixed template. Quantifier bounds
    cannot be query parameters, so they are written in, but only as integers with
    2 <= min_hops <= max_hops <= 8, never as text from outside. (Checked before the cache,
    where 2.0 and True would hit the entries of 2 and 1.)"""
    if not (type(min_hops) is int and type(max_hops) is int):
        raise TypeError("hop bounds must be integers")
    if not 2 <= min_hops <= max_hops <= HOP_LIMIT:
        raise ValueError(f"hop bounds must satisfy 2 <= {min_hops} <= {max_hops} <= {HOP_LIMIT}")
    return _render(min_hops, max_hops)


@cache
def _render(min_hops: int, max_hops: int) -> str:
    template = QUERY_FILE.read_text(encoding="utf-8")
    if template.count(QUANTIFIER) != 1:
        raise RuntimeError(f"{QUERY_FILE.name} must contain {QUANTIFIER} exactly once")
    return template.replace(QUANTIFIER, f"->{{{min_hops},{max_hops}}}(")


def pattern_strength(
    return_ratio: float, duration_hours: float, max_window_days: float, cycle_length: int
) -> float:
    """The queue-ordering heuristic in the module docstring; never a risk score."""
    window_hours = max_window_days * 24
    value = (
        0.5 * return_ratio
        + 0.3 * (1 - duration_hours / window_hours)
        + 0.2 * min(1.0, (cycle_length - 1) / 4)
    )
    return round(min(1.0, max(0.0, value)), 2)


def detect(
    driver: Driver,
    database: str,
    typology: TypologyFile,
    *,
    overrides: Mapping[str, int | float] | None = None,
    limit: int = MAX_RESULTS,
) -> list[Finding]:
    """Every circular flow in the graph, ordered by origin account id and edge ids."""
    params = resolve_parameters(typology, overrides)
    cypher = query(params.min_hops, params.max_hops)
    run_parameters: dict[str, Any] = {
        "origin": None,
        "max_window_days": params.max_window_days,
        "min_return_ratio": params.min_return_ratio,
        "limit": limit,
    }
    records, _, _ = driver.execute_query(
        cypher, run_parameters, database_=database, routing_=RoutingControl.READ
    )
    if len(records) >= limit:
        logger.warning("circular_flow stopped at the result limit of %d cycles", limit)
    return [finding(record.data(), cypher, run_parameters, params) for record in records]


def _label(account: Mapping[str, Any]) -> str:
    """How an explanation names an account: its number, else its caption, else its id."""
    text = str(account.get("account_number") or account.get("caption") or account["id"])
    return text if len(text) <= LABEL_MAX else text[: LABEL_MAX - 1] + "…"


def _moment(value: Any) -> datetime:
    """A `PAID.ts` value (a neo4j DateTime in UTC) as an aware Python datetime."""
    moment = value.to_native() if hasattr(value, "to_native") else value
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        raise ValueError(f"PAID.ts must be a zoned DATETIME (invariant I3), not {value!r}")
    return moment


def finding(
    row: Mapping[str, Any], cypher: str, run_parameters: Mapping[str, Any], params: Parameters
) -> Finding:
    """One result row of the query as a `Finding` with metrics, steps and summary."""
    accounts = [dict(account) for account in row["accounts"]]
    hops = [dict(hop) for hop in row["hops"]]
    origin_id = str(row["origin"])
    labels = {str(account["id"]): _label(account) for account in accounts}
    first, last = hops[0], hops[-1]
    start, end = _moment(first["ts"]), _moment(last["ts"])
    seconds = (end - start).total_seconds()
    sent, returned = float(first["amount"]), float(last["amount"])
    metrics: dict[str, MetricValue] = {
        "cycle_length": len(hops),
        "sent_amount": sent,
        "returned_amount": returned,
        "currency": str(first["currency"]),
        "duration_hours": round(seconds / 3600, 1),
        "duration_days": math.ceil(seconds / 86400),
        "return_ratio": round(returned / sent, 4),
    }
    strength = pattern_strength(
        float(metrics["return_ratio"]),
        float(metrics["duration_hours"]),
        params.max_window_days,
        len(hops),
    )
    steps = tuple(
        Step(
            payment_step(
                labels[str(hop["source"])],
                str(hop["currency"]),
                float(hop["amount"]),
                labels[str(hop["target"])],
                _moment(hop["ts"]),
            ),
            (str(hop["id"]),),
        )
        for hop in hops
    )
    summary = cycle_summary(
        labels[origin_id], str(first["currency"]), sent, returned, len(accounts) - 1, seconds / 3600
    )
    nodes = tuple(entity_fact(account) for account in accounts)
    holders = [dict(holder) for holder in row["holders"]]
    origin = next(node for node in nodes if node.id == origin_id)
    origin_holders = sorted(
        {entity_fact(holder) for holder in holders if holder["account"] == origin_id},
        key=lambda holder: holder.id,
    )
    return Finding(
        nodes=nodes,
        edges=tuple(
            EdgeFact(
                id=str(hop["id"]),
                source=str(hop["source"]),
                target=str(hop["target"]),
                synthetic=hop.get("synthetic") is True,
                datasets=tuple(str(slug) for slug in hop.get("datasets") or ()),
            )
            for hop in hops
        ),
        subjects=(("origin", origin), *(("origin_holder", holder) for holder in origin_holders)),
        holders=tuple(sorted({entity_fact(holder) for holder in holders}, key=lambda h: h.id)),
        metrics=metrics,
        pattern_strength=strength,
        cypher=cypher,
        parameters={**run_parameters, "origin": origin_id},
        window=(start, end),
        summary=summary,
        steps=steps,
        masked=tuple(labels.values()),
    )
