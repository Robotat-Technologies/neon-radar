"""Entity-facing text for alerts: headlines, summaries and steps (PHASE-3.md 7.5.2).

Headlines come from the typology file's templates (PHASE-1.md 5.4): `wording.headline_structural`
or `wording.headline_synthetic`, or the pair under `wording.variants.<variant>` when the finding's
variant has one. A placeholder is `{metric}` or `{metric|filter}`: `money` (the finding's
`currency` and the amount), `pct` (a ratio as a whole percent) and `n:<singular>[:<plural>]` (a
count with its noun). Headlines describe the shape and its numbers, never the conduct a typology is
named after (`typology-detection-definitions.md` 16.1), and the summary names the typology's
neutral `shape_name`, after the optional `wording.detail` template (the sentences a detector's
metrics need, such as the result of each sanctions test). Steps are rendered from the evidence
relationships. `render` lints every text it renders (`wording_lint.violations`, with the captions
of every node it names masked out) and raises `WordingError` on a match, so no run can emit text
that names conduct (G5); the error names the typology, the part and the patterns, never the text.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from neonradar_detect.catalog import Typology
from neonradar_detect.model import EdgeInfo, Finding, NodeInfo
from neonradar_detect.wording_lint import violations

MAX_HEADLINE = 140
MAX_STEP = 280
PLACEHOLDER = re.compile(r"\{(\w+)(?:\|([a-z]+)(?::([^:}]+))?(?::([^:}]+))?)?\}")


class WordingError(ValueError):
    """Rendered alert text matched the wording lint."""


@dataclass(frozen=True, slots=True)
class Rendered:
    headline: str
    summary: str
    steps: tuple[tuple[str, tuple[str, ...]], ...]  # (text, edge ids)


def money(currency: str, amount: float) -> str:
    text = f"{amount:,.2f}"
    return f"{currency} {text[:-3] if text.endswith('.00') else text}"


def day(moment: datetime | str) -> str:
    d = datetime.fromisoformat(moment) if isinstance(moment, str) else moment
    return f"{d.day} {d.strftime('%B')} {d.year}"


def counted(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def render_template(template: str, metrics: Mapping[str, Any]) -> str:
    def one(m: re.Match[str]) -> str:
        name, kind, a, b = m.groups()
        value = metrics[name]
        if kind is None:
            return _value(value)
        if kind == "money":
            return money(str(metrics["currency"]), float(value))
        if kind == "pct":
            return f"{round(100 * float(value))} percent"
        if kind == "n":
            return counted(int(value), a, b)
        raise ValueError(f"unknown filter {kind}")

    return PLACEHOLDER.sub(one, template)


def placeholders(template: str) -> set[str]:
    return {m.group(1) for m in PLACEHOLDER.finditer(template)}


def templates(typology: Typology, variant: str) -> Mapping[str, str]:
    return typology.wording.get("variants", {}).get(variant) or typology.wording


def _cap(text: str, limit: int) -> str:
    """`text`, or its words up to `limit - 1` characters and an ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut and not text[limit - 1].isspace():
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" ,;:") + "…"


def band(e: EdgeInfo) -> str:
    low, high = e.share_min, e.share_max
    if low is None and high is None:
        return "an unrecorded share"
    if low is not None and high is not None and low == high:
        return f"{low:g} percent"
    if high is None or (high >= 100 and not e.share_max_exclusive):
        return (
            f"{low:g} percent or more"
            if not e.share_min_exclusive
            else f"more than {low:g} percent"
        )
    lower = f"more than {low:g}" if e.share_min_exclusive else f"at least {low:g}"
    upper = f"less than {high:g}" if e.share_max_exclusive else f"at most {high:g}"
    return f"{lower} and {upper} percent"


def dates(e: EdgeInfo) -> str:
    """The " from <start>" and " to <end>" parts for the full dates a relationship records."""
    since = f" from {day(e.start_date)}" if len(e.start_date) == 10 else ""
    until = f" to {day(e.end_date)}" if len(e.end_date) == 10 else ""
    return since + until


def edge_sentence(e: EdgeInfo, name: Callable[[str], str]) -> str:
    s, t = name(e.source), name(e.target)
    if e.type == "PAID" and e.ts is not None:
        if e.channel == "cash_deposit":
            return f"{money(e.currency, e.amount or 0)} in cash was paid into {t} on {day(e.ts)}."
        return f"{s} paid {money(e.currency, e.amount or 0)} to {t} on {day(e.ts)}."
    if e.type == "OWNS":
        return f"{s} is recorded as holding {band(e)} of {t}{dates(e)}."
    if e.type == "CONTROLS":
        what = {
            "appointment": "the right to appoint or remove a majority of the board of",
            "voting": f"{band(e)} of the voting rights in",
        }.get(e.control_type, "significant influence or control over")
        return f"{s} is recorded with {what} {t}{dates(e)}."
    if e.type == "CONSOLIDATES":
        return f"{s} is recorded as consolidating {t} in its accounts."
    if e.type == "DIRECTOR_OF":
        return f"{s} is recorded as a director of {t}{dates(e)}."
    if e.type == "REPRESENTS":
        return f"{s} is recorded as an agent of {t}."
    if e.type == "HAS_ADDRESS":
        return f"{s} is registered at {t}."
    if e.type == "FAMILY_OF":
        return f"{s} and {t} are recorded as family ({e.role or 'relationship not given'})."
    if e.type == "ASSOCIATE_OF":
        return f"{s} and {t} are recorded as associates ({e.role or 'relationship not given'})."
    if e.type == "HOLDS_ACCOUNT":
        return f"{s} holds account {t}."
    return f"{s} is linked to {t}."


def group_sentence(group: Sequence[EdgeInfo], name: Callable[[str], str]) -> str:
    """One step: a single relationship in full, or a group summarised."""
    if len(group) == 1:
        return _cap(edge_sentence(group[0], name), MAX_STEP)
    if all(e.type == "PAID" for e in group):
        currencies = sorted({e.currency for e in group})
        total = sum(e.amount or 0 for e in group)
        first = min(e.ts for e in group if e.ts)
        last = max(e.ts for e in group if e.ts)
        sources = sorted({e.source for e in group})
        targets = sorted({e.target for e in group})
        amount = (
            money(currencies[0], total) if len(currencies) == 1 else "amounts in several currencies"
        )
        when = (
            f"on {day(first)}"
            if first.date() == last.date()
            else f"between {day(first)} and {day(last)}"
        )
        if all(e.channel == "cash_deposit" for e in group):
            into = name(targets[0]) if len(targets) == 1 else counted(len(targets), "account")
            text = f"{counted(len(group), 'cash deposit')} of {amount} in total into {into} {when}."
        elif len(targets) == 1:
            payers, n = counted(len(sources), "account"), counted(len(group), "payment")
            text = f"{payers} paid {amount} in {n} to {name(targets[0])} {when}."
        elif len(sources) == 1:
            n, payees = counted(len(group), "payment"), counted(len(targets), "account")
            text = f"{name(sources[0])} paid {amount} in {n} to {payees} {when}."
        else:
            accounts = counted(len(set(sources) | set(targets)), "account")
            text = f"{counted(len(group), 'payment')} of {amount} in total among {accounts} {when}."
        return _cap(text, MAX_STEP)
    joined = " ".join(edge_sentence(e, name) for e in group)
    if len(joined) <= MAX_STEP:
        return joined
    head = edge_sentence(group[0], name)
    return _cap(
        f"{head} And {counted(len(group) - 1, 'more recorded relationship')} of the same kind.",
        MAX_STEP,
    )


def render(
    finding: Finding,
    typology: Typology,
    wording_class: str,
    nodes: Mapping[str, NodeInfo],
    edges: Mapping[str, EdgeInfo],
) -> Rendered:
    def name(node_id: str) -> str:
        info = nodes.get(node_id)
        return info.caption if info is not None else node_id

    pair = templates(typology, finding.variant)
    key = "headline_synthetic" if wording_class == "synthetic_scenario" else "headline_structural"
    headline = _cap(render_template(pair[key], finding.metrics), MAX_HEADLINE)
    plain = _cap(render_template(pair["headline_structural"], finding.metrics), MAX_HEADLINE)
    detail_template = pair.get("detail") or typology.wording.get("detail") or ""
    detail = f"{render_template(detail_template, finding.metrics)} " if detail_template else ""
    summary = (
        f"{plain}. {detail}This matches the graph pattern of {typology.shape_name}. The records "
        "show the shape only; the notes below list ordinary activity that looks the same."
    )
    steps = tuple(
        (group_sentence([edges[e] for e in group], name), tuple(group)) for group in finding.steps
    )
    captions = tuple(
        sorted({info.caption for info in nodes.values()} | set(nodes), key=len, reverse=True)
    )
    parts = [("headline", headline), ("summary", summary)]
    parts += [(f"step {i}", text) for i, (text, _) in enumerate(steps, 1)]
    for part, text in parts:
        found = violations(text, captions)
        if found:
            raise WordingError(f"{typology.slug}: the {part} matches {found}")
    return Rendered(headline, summary, steps)
