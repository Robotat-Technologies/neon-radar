"""Benchmark measures (PHASE-2.md 7.1.7, M2.10a deliverable 9).

A true pair is two records of the same class with the same `entity_id` in
`labels/er_truth.csv`. It is policy-blocked when its records have different flag topics or
exactly one of them is leak-style (P1, P2), and mergeable otherwise. Pairwise precision of a
class is the share of its record pairs in one cluster that are true pairs; recall is the share
of its mergeable true pairs in one cluster. A policy-blocked true pair is recalled as a possible
match when its records ended up in one cluster (only a deterministic rule with the name check or
a decision can put them there) or a line of `candidates.jsonl` joins their clusters. A hard
negative merged is an entity with a record in one cluster with a record of its `twin_of` entity.
Address records are not counted.
"""

from __future__ import annotations

import csv
import itertools
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from neonradar_resolve.cluster import Member

CLASSES = ("person", "org")


@dataclass(frozen=True)
class Truth:
    entity: str
    entity_class: str
    style: str
    twin_of: str | None


@dataclass(frozen=True)
class ClassScore:
    merged_pairs: int
    true_merged_pairs: int
    mergeable_true_pairs: int
    mergeable_recalled: int

    @property
    def precision(self) -> float | None:
        return self.true_merged_pairs / self.merged_pairs if self.merged_pairs else None

    @property
    def recall(self) -> float | None:
        if not self.mergeable_true_pairs:
            return None
        return self.mergeable_recalled / self.mergeable_true_pairs

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        return None if p is None or r is None or p + r == 0 else 2 * p * r / (p + r)


@dataclass(frozen=True)
class Score:
    classes: dict[str, ClassScore]
    cross_class_pairs_merged: int
    policy_blocked_pairs: int
    policy_blocked_recalled: int
    hard_negatives_merged: int
    unlabelled_records: int

    @property
    def policy_blocked_recall(self) -> float | None:
        if not self.policy_blocked_pairs:
            return None
        return self.policy_blocked_recalled / self.policy_blocked_pairs


def read_truth(path: Path) -> dict[str, Truth]:
    """`labels/er_truth.csv`: comment lines start with `#`, then a header row."""
    with path.open(encoding="utf-8", newline="") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    out = {}
    for row in csv.DictReader(lines):
        out[row["record_id"]] = Truth(
            row["entity_id"], row["class"], row["style"], row["twin_of"] or None
        )
    return out


def _blocked(a: Member, b: Member) -> bool:
    return a.flag_topics != b.flag_topics or (a.kind == "leak") != (b.kind == "leak")


def measure(
    truth: Mapping[str, Truth],
    members: Mapping[str, Member],
    canonical: Iterable[Mapping[str, object]],
    candidates: Iterable[Mapping[str, object]],
) -> Score:
    cluster_of = {str(r["record_id"]): str(r["canonical_id"]) for r in canonical}
    joined = {frozenset((str(c["a"]), str(c["b"]))) for c in candidates}
    labelled = [rid for rid in sorted(cluster_of) if rid in truth]
    unlabelled = sum(
        1 for rid, m in members.items() if m.entity_class != "address" and rid not in truth
    )

    merged: dict[str, int] = dict.fromkeys(CLASSES, 0)
    true_merged: dict[str, int] = dict.fromkeys(CLASSES, 0)
    cross = 0
    by_cluster: dict[str, list[str]] = defaultdict(list)
    for rid in labelled:
        by_cluster[cluster_of[rid]].append(rid)
    for ids in by_cluster.values():
        for a, b in itertools.combinations(ids, 2):
            ta, tb = truth[a], truth[b]
            if ta.entity_class != tb.entity_class:
                cross += 1
                continue
            merged[ta.entity_class] += 1
            true_merged[ta.entity_class] += ta.entity == tb.entity

    mergeable: dict[str, int] = dict.fromkeys(CLASSES, 0)
    recalled: dict[str, int] = dict.fromkeys(CLASSES, 0)
    blocked = blocked_recalled = 0
    by_entity: dict[str, list[str]] = defaultdict(list)
    for rid in labelled:
        by_entity[truth[rid].entity].append(rid)
    for ids in by_entity.values():
        for a, b in itertools.combinations(ids, 2):
            together = cluster_of[a] == cluster_of[b]
            if _blocked(members[a], members[b]):
                blocked += 1
                blocked_recalled += together or frozenset((cluster_of[a], cluster_of[b])) in joined
            else:
                mergeable[truth[a].entity_class] += 1
                recalled[truth[a].entity_class] += together

    clusters_of_entity: dict[str, set[str]] = defaultdict(set)
    for rid in labelled:
        clusters_of_entity[truth[rid].entity].add(cluster_of[rid])
    twins = {frozenset((t.entity, t.twin_of)) for t in truth.values() if t.twin_of is not None}
    hard = sum(
        1
        for pair in twins
        if len(pair) == 2 and set.intersection(*(clusters_of_entity.get(e, set()) for e in pair))
    )
    scores = {c: ClassScore(merged[c], true_merged[c], mergeable[c], recalled[c]) for c in CLASSES}
    return Score(scores, cross, blocked, blocked_recalled, hard, unlabelled)


def as_counts(score: Score) -> dict[str, object]:
    """The measures as a counts-only summary (rates rounded to 4 decimals)."""

    def rate(value: float | None) -> float | None:
        return None if value is None else round(value, 4)

    out: dict[str, object] = {}
    for name, s in score.classes.items():
        out[name] = {
            "precision": rate(s.precision),
            "recall": rate(s.recall),
            "f1": rate(s.f1),
            "merged_pairs": s.merged_pairs,
            "true_merged_pairs": s.true_merged_pairs,
            "mergeable_true_pairs": s.mergeable_true_pairs,
            "mergeable_recalled": s.mergeable_recalled,
        }
    out.update(
        cross_class_pairs_merged=score.cross_class_pairs_merged,
        policy_blocked_pairs=score.policy_blocked_pairs,
        policy_blocked_recalled=score.policy_blocked_recalled,
        policy_blocked_recall=rate(score.policy_blocked_recall),
        hard_negatives_merged=score.hard_negatives_merged,
        unlabelled_records=score.unlabelled_records,
    )
    return out


def lines(score: Score) -> list[str]:
    """The measures as text for `er bench`."""

    def rate(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.4f}"

    out = [
        f"{name:7} precision {rate(s.precision)}  recall {rate(s.recall)}  f1 {rate(s.f1)}"
        f"  (merged pairs {s.merged_pairs}, mergeable true pairs {s.mergeable_true_pairs})"
        for name, s in score.classes.items()
    ]
    out.append(
        f"policy-blocked true pairs recalled as possible matches:"
        f" {rate(score.policy_blocked_recall)}"
        f" ({score.policy_blocked_recalled} of {score.policy_blocked_pairs})"
    )
    out.append(f"hard negatives merged: {score.hard_negatives_merged}")
    return out
