"""The precision report (PHASE-2.md 7.3, M2.10c deliverable 7).

`measure(pairs, labels, barred)` combines the sample with every label file: a pair's label is
its labeller's newest answer; an S4 pair's two answers count when they agree, else the
adjudicated label of a person who labelled neither and did not set the thresholds. For each
stratum it counts `k` (same), `n` (same or different) and `u` (unsure); `stats.py` gives the
point estimate `k / n`, its Wilson 95 percent interval and, for S1, `k / (n + u)` (every unsure
pair wrong); S2 is also split by D rule. The S4 agreement figures use the two answers before
adjudication. `report(...)` writes the text of 7.3: counts and rates only, never a record id,
a handle or a note, with the README sentence and the sources-and-licences footer.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from neonradar_contracts.datasets import load_registry
from neonradar_resolve.labels import Label, adjudicated, answers
from neonradar_resolve.sample import STRATA, Pair
from neonradar_resolve.stats import cohens_kappa, specific_agreement, wilson_interval

RULES = ("D1", "D2", "D3", "D4", "D5")  # the deterministic rules of S2 (D6 is addresses only)
UNSURE_WARNING = 0.15  # 7.3 rule 3
PLANNED_S1_LABELS = 250  # 7.3 rule 5
ICIJ = "icij_offshore_leaks"
ICIJ_NOTICE = (
    "Content in this report was obtained from the ICIJ Offshore Leaks Database, which is"
    " available under the Open Database License 1.0"
    " (https://opendatacommons.org/licenses/odbl/1-0/). Always cite the International"
    " Consortium of Investigative Journalists when using this data."
)
README_SENTENCE = (
    "On {date}, human labellers judged {k} of {n} sampled probabilistic merges on {slice}"
    " correct (precision {p}, Wilson 95% interval {lo} to {hi}; {u} unsure, excluded)."
    " Sanctions, PEP and ICIJ records are never merged by probability, so this does not"
    " measure screening accuracy."
)
REAL_SLICE = "a slice of the UK register"  # 7.3 rule 7, verbatim
NAMES = {"S1": "probabilistic merges", "S2": "deterministic merges", "S3": "possible matches"}


@dataclass(frozen=True)
class Figure:
    k: int  # labels "same"
    n: int  # labels "same" or "different"
    u: int  # labels "unsure"

    @property
    def precision(self) -> float | None:
        return self.k / self.n if self.n else None

    @property
    def interval(self) -> tuple[float, float] | None:
        return wilson_interval(self.k, self.n) if self.n else None

    @property
    def bound(self) -> Figure:
        """The precision if every unsure pair were wrong: `k / (n + u)`."""
        return Figure(self.k, self.n + self.u, 0)

    @property
    def unsure_share(self) -> float | None:
        return self.u / (self.n + self.u) if self.n + self.u else None


def figure(labels: Iterable[str | None]) -> Figure:
    found = [x for x in labels if x is not None]
    same, different = found.count("same"), found.count("different")
    return Figure(same, same + different, found.count("unsure"))


@dataclass(frozen=True)
class Agreement:
    pairs: int
    by_stratum: dict[str, int]
    percent: float | None
    kappa: float | None
    share_same: float | None
    positive: float | None
    negative: float | None
    excluded: int  # pairs either labeller marked unsure (left out of the specific agreements)


def agreement(pairs: Sequence[Pair], labels: Sequence[Label]) -> Agreement:
    """The S4 figures before adjudication, over the pairs both labellers answered."""
    both = [(p, answers(p, labels)) for p in pairs if p.overlap]
    both = [(p, given) for p, given in both if len(given) == 2]
    first = [given[0].label for _, given in both]
    second = [given[1].label for _, given in both]
    by_stratum = {s: sum(1 for p, _ in both if p.stratum == s) for s in ("S1", "S3")}
    if not both:
        return Agreement(0, by_stratum, None, None, None, None, None, 0)
    m = len(both)
    specific = specific_agreement(first, second)
    return Agreement(
        m,
        by_stratum,
        sum(a == b for a, b in zip(first, second, strict=True)) / m,
        cohens_kappa(first, second),
        (first.count("same") + second.count("same")) / (2 * m),
        specific.positive,
        specific.negative,
        specific.excluded,
    )


@dataclass(frozen=True)
class Outcome:
    final: dict[str, str | None]  # pair id -> the label that counts, None when there is none
    strata: dict[str, Figure]
    by_rule: dict[str, Figure]
    agreement: Agreement
    unlabelled: int
    awaiting_adjudication: int
    ignored: int  # labels from people not assigned to the pair, or ineligible adjudications
    labellers: int
    adjudicators: frozenset[str]
    first_at: datetime | None
    last_at: datetime | None
    census: dict[str, bool] = field(default_factory=dict)


def final_label(
    pair: Pair,
    labels: Sequence[Label],
    barred: Iterable[str],
    adjudicators: Iterable[str] | None = None,
) -> tuple[str | None, str, Label | None]:
    """The label that counts, why (`labelled`, `unlabelled`, `awaiting adjudication`) and the
    adjudication it comes from, if any. An S4 pair with one answer counts that answer.
    `adjudicators`, when given (a real profile), are the only people whose adjudication counts.
    """
    given = answers(pair, labels)
    if not given:
        return None, "unlabelled", None
    if not pair.overlap or len(given) == 1 or given[0].label == given[1].label:
        return given[0].label, "labelled", None
    decided = adjudicated(pair, labels, barred, adjudicators)
    if decided is None:
        return None, "awaiting adjudication", None
    return decided.label, "labelled", decided


def measure(
    pairs: Sequence[Pair],
    labels: Sequence[Label],
    barred: Iterable[str],
    census: Mapping[str, bool] | None = None,
    adjudicators: Iterable[str] | None = None,
) -> Outcome:
    barred = frozenset(barred)
    allowed = None if adjudicators is None else frozenset(adjudicators)
    final: dict[str, str | None] = {}
    states: list[str] = []
    used: set[tuple[str, str]] = set()  # (handle, pair id) of the adjudications that count
    for pair in pairs:
        final[pair.pair_id], state, decided = final_label(pair, labels, barred, allowed)
        states.append(state)
        if decided is not None:
            used.add((decided.by, decided.pair_id))
    counted = {(x.by, x.pair_id) for p in pairs for x in answers(p, labels)}
    ignored = sum(
        1 for x in labels if (x.by, x.pair_id) not in (used if x.adjudication else counted)
    )
    stamps = [x.at for x in labels if (x.by, x.pair_id) in (used if x.adjudication else counted)]
    return Outcome(
        final,
        {s: figure(final[p.pair_id] for p in pairs if p.stratum == s) for s in STRATA},
        {
            rule: figure(final[p.pair_id] for p in pairs if p.stratum == "S2" and p.rule == rule)
            for rule in RULES
        },
        agreement(pairs, labels),
        states.count("unlabelled"),
        states.count("awaiting adjudication"),
        ignored,
        len({by for by, _ in counted}),
        frozenset(by for by, _ in used),
        min(stamps, default=None),
        max(stamps, default=None),
        dict(census or {}),
    )


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _value(found: Mapping[str, Any], key: str) -> str:
    value = found.get(key)
    return "n/a" if value is None else str(value)


def _interval(found: Figure) -> tuple[str, str]:
    interval = found.interval
    return ("n/a", "n/a") if interval is None else (_rate(interval[0]), _rate(interval[1]))


def _first_lines(outcome: Outcome) -> list[str]:
    s1 = outcome.strata["S1"]
    lines = []
    share = s1.unsure_share
    if share is not None and share > UNSURE_WARNING:
        lines.append(
            f"More than 15 percent of the labelled S1 pairs were marked unsure ({_percent(share)})."
        )
    if s1.n < PLANNED_S1_LABELS:
        lines.append(
            f"Only {s1.n} S1 labels other than unsure (250 planned), so the interval is wider"
            " than planned."
        )
    return lines


def _census(census: Mapping[str, bool]) -> str | None:
    whole = [f"{s} ({NAMES[s]})" for s in STRATA if census.get(s)]
    if not whole:
        return None
    return (
        f"Labelled whole (a census of this run, not a sample): {', '.join(whole)}; for these"
        " the interval describes the process rather than the sampling."
    )


def _seed_source(seed: object, adr_seed: object) -> str:
    if adr_seed is None:
        return "ADR-0014 sets no evaluation sample seed yet"
    return "ADR-0014" if seed == adr_seed else "not the seed of ADR-0014"


def _adjudication(outcome: Outcome, project_lead: str | None) -> str:
    if not outcome.adjudicators:
        return "no pair needed adjudication"
    if project_lead is not None and outcome.adjudicators == {project_lead}:
        return "adjudicated by the project lead"
    return "adjudicated by people who did not set the thresholds"


def _sources(datasets: Iterable[str]) -> str:
    """One sentence per dataset of the run (7.3 rule 8), then the ICIJ notice when it is in."""
    registry = load_registry()
    parts = []
    slugs = sorted(set(datasets))
    for slug in slugs:
        found = registry.get(slug)
        if found is None:
            parts.append(f"{slug}: not in contracts/datasets.yaml.")
        elif slug == ICIJ:
            continue  # the ODbL notice below carries ICIJ's attribution
        elif found.attribution:
            parts.append(f"{found.title}: {found.attribution.rstrip('.')}.")
        else:
            parts.append(f"{found.title}: no attribution needed.")
    if ICIJ in slugs:
        parts.append(ICIJ_NOTICE)
    return " ".join(parts)


def readme_sentence(outcome: Outcome, on: date, *, real_data: bool, profile: str) -> str:
    """7.3 rule 7, with the values filled in (a synthetic profile names itself, not the UK
    register)."""
    s1 = outcome.strata["S1"]
    lo, hi = _interval(s1)
    where = REAL_SLICE if real_data else f"synthetic records (profile {profile})"
    return README_SENTENCE.format(
        date=on.isoformat(), k=s1.k, n=s1.n, slice=where, p=_rate(s1.precision), lo=lo, hi=hi,
        u=s1.u,
    )  # fmt: skip


def report(
    outcome: Outcome,
    *,
    on: date,
    profile: str,
    real_data: bool,
    run: Mapping[str, Any],
    sample: Mapping[str, Any],
    project_lead: str | None,
) -> str:
    """The report of 7.3 (`docs/data/er/precision-<date>.md` for the published figure)."""
    s1, s2, s3 = (outcome.strata[s] for s in STRATA)
    lo, hi = _interval(s1)
    bound = s1.bound
    blo, bhi = _interval(bound)
    lo2, hi2 = _interval(s2)
    rules = ", ".join(f"{r} {f.k} of {f.n}" for r, f in outcome.by_rule.items())
    a = outcome.agreement
    counts = run.get("counts") or {}
    thresholds = run.get("thresholds") or {}
    merge = thresholds.get("merge_threshold") or {}
    frames = sample.get("frames") or {}
    seed, adr_seed = sample.get("seed"), sample.get("adr_seed")
    used = "decisions applied" if run.get("decisions_used") else "no decisions applied"
    when = (
        f"between {outcome.first_at.date().isoformat()} and {outcome.last_at.date().isoformat()}"
        if outcome.first_at and outcome.last_at
        else "(no labels yet)"
    )
    run_id = sample.get("run_id") or run.get("run_id")
    sizes = ", ".join(str(frames.get(s.lower(), 0)) for s in STRATA)
    slice_words = "one slice of the UK register" if real_data else "synthetic records only"
    lines = [
        f"# Entity resolution precision, {profile}, {on.isoformat()}",
        "",
        *(warnings := _first_lines(outcome)),
        *([""] if warnings else []),
        f"Probabilistic merges (headline): {s1.k} of {s1.n} correct, precision"
        f" {_rate(s1.precision)} (Wilson 95% interval {lo} to {hi});",
        f"{s1.u} pairs ({_percent(s1.unsure_share)}) marked unsure and excluded. If every unsure"
        f" pair were wrong: {bound.k} of {bound.n},",
        f"precision {_rate(bound.precision)} (Wilson 95% interval {blo} to {bhi}).",
        f"Deterministic merges: {s2.k} of {s2.n} correct (Wilson 95% interval {lo2} to {hi2});"
        f" by rule: {rules}.",
        f"Joined through a reviewer's decision: {sample.get('human_joined', 0)} records"
        " (not sampled).",
        f"Possible matches that labellers judged to be the same entity: {s3.k} of {s3.n}.",
        f"Agreement between labellers on {a.pairs} overlapping pairs ({a.by_stratum['S1']} from"
        f" S1, {a.by_stratum['S3']} from S3), before adjudication:",
        f"{_percent(a.percent)}; Cohen's kappa {_rate(a.kappa)}; share of same"
        f" {_percent(a.share_same)}; positive agreement {_rate(a.positive)}; negative agreement"
        f" {_rate(a.negative)}.",
        f"Pairs without a label that counts: {outcome.unlabelled} not labelled,"
        f" {outcome.awaiting_adjudication} awaiting adjudication; labels not counted:"
        f" {outcome.ignored}.",
        *([census] if (census := _census(outcome.census)) else []),
        "",
        f"Evaluation run {run_id} ({used}; {counts.get('decisions_on_file', 0)} decisions on"
        f" file); resolver {run.get('resolver_version')};",
        f"config {run.get('config_sha256')}; thresholds person merge {_value(merge, 'person')},"
        f" org merge {_value(merge, 'org')}, candidate"
        f" {_value(thresholds, 'candidate_threshold')}; frame sizes {sizes}; sample seed"
        f" {seed} ({_seed_source(seed, adr_seed)});",
        f"labelled by {outcome.labellers} people {when}; {_adjudication(outcome, project_lead)}.",
        "",
        readme_sentence(outcome, on, real_data=real_data, profile=profile),
        "",
        f"Limitations: {slice_words}; one evaluation run with one configuration; labels are human"
        " judgements of the records shown and can be wrong; precision of merges says nothing"
        " about recall.",
        f"How to reproduce: uv run neonradar er run --profile {profile} --no-decisions, then"
        f" uv run neonradar er sample --profile {profile} --run <run id> --seed {seed} --labellers"
        " <the labellers>, each labeller labels at a terminal, then uv run neonradar er precision"
        f" --profile {profile} --run <run id> --out <file>.",
        "",
        f"Sources and licences: {_sources(i.get('dataset', '') for i in run.get('inputs') or [])}",
    ]
    return "\n".join(lines) + "\n"


def summary(outcome: Outcome) -> dict[str, Any]:
    """The counts the CLI emits (M2.2): numbers only."""

    def numbers(found: Figure) -> dict[str, Any]:
        interval = found.interval
        bound = found.bound.interval
        return {
            "k": found.k,
            "n": found.n,
            "u": found.u,
            "precision": found.precision,
            "low": interval[0] if interval else None,
            "high": interval[1] if interval else None,
            "bound_precision": found.bound.precision,
            "bound_low": bound[0] if bound else None,
            "bound_high": bound[1] if bound else None,
        }

    a = outcome.agreement
    return {
        **{s.lower(): numbers(f) for s, f in outcome.strata.items()},
        "s2_by_rule": {r.lower(): {"k": f.k, "n": f.n} for r, f in outcome.by_rule.items()},
        "agreement": {
            "pairs": a.pairs,
            "percent": a.percent,
            "kappa": a.kappa,
            "share_same": a.share_same,
            "positive": a.positive,
            "negative": a.negative,
            "excluded": a.excluded,
        },
        "census": {s.lower(): bool(outcome.census.get(s)) for s in STRATA},
        "unlabelled": outcome.unlabelled,
        "awaiting_adjudication": outcome.awaiting_adjudication,
        "labels_not_counted": outcome.ignored,
        "labellers": outcome.labellers,
    }
