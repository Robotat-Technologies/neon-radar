"""Threshold calibration on the synthetic benchmark (PHASE-2.md M2.10b deliverable 6, 7.1.7).

`sweep` clusters one scored run again for each value `t` of `SWEEP`, without scoring again:
once with `merge_threshold = t` for both models (candidates from the lowest sweep value), for
pairwise precision and recall, and once with `candidate_threshold = t` and the merge thresholds
of er.yaml, for the recall of policy-blocked true pairs as possible matches. `propose` applies
the rule of 7.1.7. Nothing here edits er.yaml: the tech lead and the graph mentor set the values
there and in ADR-0014. The thresholds come from the synthetic benchmark only (G10).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from neonradar_resolve import bench, cluster, rules, run
from neonradar_resolve.config import ResolverConfig

SWEEP = (0.50, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999, 0.9999)
PROPOSE_PRECISION = 0.98  # merge threshold: the lowest t with at least this precision
PROPOSE_BLOCKED_RECALL = 0.90  # candidate threshold: the highest t with at least this recall


@dataclass(frozen=True)
class Point:
    t: float
    merge: bench.Score  # merge_threshold = t
    candidate: bench.Score  # candidate_threshold = t


def _score(
    truth: Mapping[str, bench.Truth],
    members: Mapping[str, cluster.Member],
    deterministic: Sequence[cluster.Link],
    probabilistic: Sequence[cluster.Link],
    hints: Sequence[tuple[str, str, str]],
    config: cluster.Config,
) -> bench.Score:
    no_decisions = rules.Decisions([], [], 0)  # the benchmark has no decisions file
    result, _ = run.resolve(
        members, list(deterministic), list(probabilistic), no_decisions, hints, config
    )
    return bench.measure(truth, members, result.canonical, result.candidates)


def sweep(
    truth: Mapping[str, bench.Truth],
    members: Mapping[str, cluster.Member],
    deterministic: Sequence[cluster.Link],
    probabilistic: Sequence[cluster.Link],
    hints: Sequence[tuple[str, str, str]],
    resolver: ResolverConfig,
) -> list[Point]:
    """The benchmark measures at each sweep value (no decisions: the benchmark has none)."""
    base = resolver.cluster_config()
    points = []
    for t in SWEEP:
        merge = cluster.Config(
            dict.fromkeys(base.merge_threshold, t), min(SWEEP), base.cluster_cap,
            base.name_check_jaro_winkler,
        )  # fmt: skip
        candidate = cluster.Config(
            base.merge_threshold, t, base.cluster_cap, base.name_check_jaro_winkler
        )
        points.append(
            Point(
                t,
                _score(truth, members, deterministic, probabilistic, hints, merge),
                _score(truth, members, deterministic, probabilistic, hints, candidate),
            )
        )
    return points


def propose(points: Sequence[Point]) -> dict[str, float | None]:
    """7.1.7: per class the lowest merge threshold with precision at least 0.98; the highest
    candidate threshold with policy-blocked recall at least 0.90; None when no value passes."""
    out: dict[str, float | None] = {}
    for name in bench.CLASSES:
        passing = [
            p.t
            for p in points
            if (v := p.merge.classes[name].precision) is not None and v >= PROPOSE_PRECISION
        ]
        out[f"merge_threshold.{name}"] = min(passing, default=None)
    passing = [
        p.t
        for p in points
        if (v := p.candidate.policy_blocked_recall) is not None and v >= PROPOSE_BLOCKED_RECALL
    ]
    out["candidate_threshold"] = max(passing, default=None)
    return out


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def table(points: Sequence[Point]) -> list[str]:
    """The calibration table as Markdown lines."""
    lines = [
        "| t | person precision | person recall | org precision | org recall"
        " | hard negatives merged | policy-blocked recall (person, org, all) |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in points:
        person, org = p.merge.classes["person"], p.merge.classes["org"]
        blocked = p.candidate
        lines.append(
            f"| {p.t:g} | {_rate(person.precision)} | {_rate(person.recall)}"
            f" | {_rate(org.precision)} | {_rate(org.recall)} | {p.merge.hard_negatives_merged}"
            f" | {_rate(blocked.classes['person'].policy_blocked_recall)},"
            f" {_rate(blocked.classes['org'].policy_blocked_recall)},"
            f" {_rate(blocked.policy_blocked_recall)} |"
        )
    return lines


def document(
    points: Sequence[Point],
    proposal: Mapping[str, float | None],
    resolver: ResolverConfig,
    size: str,
    seed: int,
    splink: Mapping[str, Any],
) -> str:
    """`docs/data/er/benchmark.md`: the calibration table and the proposed values."""
    versions = ", ".join(f"{k} {v}" for k, v in sorted(splink.get("versions", {}).items()))
    scored = splink.get("pairs_scored", {})
    compared = splink.get("comparisons", {})
    configured = {
        **{f"merge_threshold.{k}": v for k, v in sorted(resolver.merge_threshold.items())},
        "candidate_threshold": resolver.candidate_threshold,
    }
    out = [
        "# Entity resolution calibration",
        "",
        f"<!-- Generated by `neonradar er calibrate --size {size} --seed {seed}`"
        " (PHASE-2.md M2.10b). Do not edit by hand: run the command again. -->",
        "",
        f"The {size} synthetic entity resolution benchmark (seed {seed}, M2.9) was scored once by"
        " the two Splink models down to a match probability of 0.50, and the constrained"
        " clustering of PHASE-2.md 7.1.6 then ran again on the stored pairs for each threshold"
        " `t` below, without scoring again. The measures are those of PHASE-2.md 7.1.7:"
        " pairwise precision and recall of each class with `merge_threshold = t` for both"
        " models, the hard negatives merged at that threshold, and the recall of policy-blocked"
        " true pairs (P1, P2) as possible matches with `candidate_threshold = t` and the merge"
        " thresholds of `er.yaml`.",
        "",
        f"Libraries: {versions or 'not recorded'}. Comparisons generated by blocking: person"
        f" {compared.get('person', 0)}, organisation {compared.get('org', 0)}. Pairs scored at"
        f" 0.50 or more: person model {scored.get('person', 0)}, organisation model"
        f" {scored.get('org', 0)}. One DuckDB thread, training seed {resolver.seed}.",
        "",
        "## Calibration table",
        "",
        *table(points),
        "",
        "## Proposed values",
        "",
        "The rule of PHASE-2.md 7.1.7: for each class the lowest merge threshold whose precision"
        f" is at least {PROPOSE_PRECISION}, and the highest candidate threshold whose"
        f" policy-blocked recall is at least {PROPOSE_BLOCKED_RECALL}.",
        "",
        "| Setting | Proposed | In er.yaml now |",
        "|---|---|---|",
        *(
            f"| `{name}` | {'none passes' if value is None else f'{value:g}'}"
            f" | {configured[name]:g} |"
            for name, value in proposal.items()
        ),
        "",
        "`er calibrate` never edits `resolve/config/er.yaml`. The tech lead and the graph mentor"
        " choose the values at the freeze and record them, with this table, in ADR-0014. The"
        " thresholds come from the synthetic benchmark only: no real pair is labelled before"
        " the evaluation sample is drawn (G10, PHASE-2.md 7.3).",
        "",
    ]
    return "\n".join(out)
