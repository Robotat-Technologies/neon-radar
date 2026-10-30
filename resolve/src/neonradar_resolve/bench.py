"""Benchmark measures (PHASE-2.md 7.1.7, M2.10a deliverable 9).

A true pair is two records of the same class with the same `entity_id` in
`labels/er_truth.csv`. It is policy-blocked when its records have different flag topics or
exactly one of them is leak-style (P1, P2), and mergeable otherwise. Pairwise precision of a
class is the share of its record pairs in one cluster that are true pairs; recall is the share
of its mergeable true pairs in one cluster. A policy-blocked true pair is recalled as a possible
match when its records ended up in one cluster (only a deterministic rule with the name check or
a decision can put them there) or a line of `candidates.jsonl` joins their clusters. A hard
negative merged is an entity with a record in one cluster with a record of its `twin_of` entity.
Address records are not counted. `gate_failures` holds the G2-05 gates of `er bench` (M2.10b).

OD-27 (the operator's decision): the policy-blocked recall that gates, and that the calibration
rule reads, counts only policy-blocked true pairs with no name-only record
(`features.name_only`). The pairs with a name-only record are counted apart and reported beside
it; that figure never gates. The 0.80 bar is unchanged. A caller that passes no name-only
records counts every policy-blocked pair in the gate.
"""

from __future__ import annotations

import csv
import itertools
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from neonradar_resolve.cluster import Member

CLASSES = ("person", "org")
# G2-05 (M2.10b deliverable 7): `er bench` fails below these at the thresholds in er.yaml
MIN_PRECISION = 0.97
MIN_RECALL = 0.80
MIN_POLICY_BLOCKED_RECALL = 0.80  # unchanged by OD-27, which only sets what it counts


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
    policy_blocked_pairs: int = 0  # OD-27: with no name-only record (the gate)
    policy_blocked_recalled: int = 0
    name_only_pairs: int = 0  # OD-27: policy-blocked, with a name-only record (never gates)
    name_only_recalled: int = 0

    @property
    def policy_blocked_recall(self) -> float | None:
        if not self.policy_blocked_pairs:
            return None
        return self.policy_blocked_recalled / self.policy_blocked_pairs

    @property
    def name_only_recall(self) -> float | None:
        return self.name_only_recalled / self.name_only_pairs if self.name_only_pairs else None

    @property
    def every_blocked_recall(self) -> float | None:
        """Every policy-blocked true pair, as 7.1.7 counted them before OD-27 (reported only)."""
        pairs = self.policy_blocked_pairs + self.name_only_pairs
        return (self.policy_blocked_recalled + self.name_only_recalled) / pairs if pairs else None

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
    unlabelled_records: int  # resolvable records without a truth row
    missing_records: int  # truth rows whose record is not in the run
    name_only_pairs: int = 0  # OD-27: reported beside the gate, never in it
    name_only_recalled: int = 0

    @property
    def left_out(self) -> int:
        """Records and pairs the measures cannot count: `er bench` fails when there are any."""
        return self.unlabelled_records + self.missing_records + self.cross_class_pairs_merged

    @property
    def policy_blocked_recall(self) -> float | None:
        if not self.policy_blocked_pairs:
            return None
        return self.policy_blocked_recalled / self.policy_blocked_pairs

    @property
    def name_only_recall(self) -> float | None:
        return self.name_only_recalled / self.name_only_pairs if self.name_only_pairs else None

    @property
    def every_blocked_recall(self) -> float | None:
        """Every policy-blocked true pair, as 7.1.7 counted them before OD-27 (reported only)."""
        pairs = self.policy_blocked_pairs + self.name_only_pairs
        return (self.policy_blocked_recalled + self.name_only_recalled) / pairs if pairs else None


def read_truth(path: Path) -> dict[str, Truth]:
    """`labels/er_truth.csv`: comment lines start with `#`, then a header row."""
    with path.open(encoding="utf-8", newline="") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    out = {}
    for number, row in enumerate(csv.DictReader(lines), start=1):
        if row["class"] not in CLASSES:
            raise ValueError(f"{path.name}: truth row {number}: class must be person or org")
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
    name_only: Collection[str] = frozenset(),
) -> Score:
    """The measures; `name_only` holds the ids of name-only records (OD-27)."""
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
    blocked: dict[str, int] = dict.fromkeys(CLASSES, 0)
    blocked_recalled: dict[str, int] = dict.fromkeys(CLASSES, 0)
    weak: dict[str, int] = dict.fromkeys(CLASSES, 0)  # OD-27: with a name-only record
    weak_recalled: dict[str, int] = dict.fromkeys(CLASSES, 0)
    by_entity: dict[str, list[str]] = defaultdict(list)
    for rid in labelled:
        by_entity[truth[rid].entity].append(rid)
    for ids in by_entity.values():
        for a, b in itertools.combinations(ids, 2):
            together = cluster_of[a] == cluster_of[b]
            name = truth[a].entity_class
            if _blocked(members[a], members[b]):
                found = together or frozenset((cluster_of[a], cluster_of[b])) in joined
                if a in name_only or b in name_only:  # OD-27: reported, never gates
                    weak[name] += 1
                    weak_recalled[name] += found
                else:
                    blocked[name] += 1
                    blocked_recalled[name] += found
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
    scores = {
        c: ClassScore(
            merged[c],
            true_merged[c],
            mergeable[c],
            recalled[c],
            blocked[c],
            blocked_recalled[c],
            weak[c],
            weak_recalled[c],
        )
        for c in CLASSES
    }
    missing = sum(1 for rid in truth if rid not in cluster_of)
    total, total_recalled = sum(blocked.values()), sum(blocked_recalled.values())
    return Score(
        scores, cross, total, total_recalled, hard, unlabelled, missing,
        sum(weak.values()), sum(weak_recalled.values()),
    )  # fmt: skip


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
            "policy_blocked_recall": rate(s.policy_blocked_recall),
            "name_only_recall": rate(s.name_only_recall),
        }
    out.update(
        cross_class_pairs_merged=score.cross_class_pairs_merged,
        policy_blocked_pairs=score.policy_blocked_pairs,
        policy_blocked_recalled=score.policy_blocked_recalled,
        policy_blocked_recall=rate(score.policy_blocked_recall),
        name_only_pairs=score.name_only_pairs,
        name_only_recalled=score.name_only_recalled,
        name_only_recall=rate(score.name_only_recall),
        hard_negatives_merged=score.hard_negatives_merged,
        unlabelled_records=score.unlabelled_records,
        missing_records=score.missing_records,
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
        f" ({score.policy_blocked_recalled} of {score.policy_blocked_pairs};"
        f" pairs with a name-only record are counted on the next line, OD-27)"
    )
    out.append(
        f"policy-blocked true pairs with a name-only record, recalled as possible matches"
        f" (reported, does not gate): {rate(score.name_only_recall)}"
        f" ({score.name_only_recalled} of {score.name_only_pairs})"
    )
    out.append(f"hard negatives merged: {score.hard_negatives_merged}")
    out.append(
        f"left out: {score.unlabelled_records} records without truth,"
        f" {score.missing_records} truth records not in the run,"
        f" {score.cross_class_pairs_merged} person-organisation pairs merged"
    )
    return out


def gate_failures(score: Score) -> list[str]:
    """The G2-05 gates that fail: precision, recall, policy-blocked recall (OD-27: the pairs
    with no name-only record), hard negatives. The policy-blocked gate fails, rather than
    passing on nothing, when every policy-blocked true pair has a name-only record."""
    out = []
    for name, s in score.classes.items():
        if s.precision is not None and s.precision < MIN_PRECISION:
            out.append(f"{name} precision {s.precision:.4f} is below {MIN_PRECISION}")
        if s.recall is not None and s.recall < MIN_RECALL:
            out.append(f"{name} recall {s.recall:.4f} is below {MIN_RECALL}")
    blocked = score.policy_blocked_recall
    if blocked is not None and blocked < MIN_POLICY_BLOCKED_RECALL:
        out.append(f"policy-blocked recall {blocked:.4f} is below {MIN_POLICY_BLOCKED_RECALL}")
    if blocked is None and score.name_only_pairs:  # OD-27 must not empty the gate unseen
        out.append(
            f"policy-blocked recall counts no pair: all {score.name_only_pairs} policy-blocked"
            " true pairs have a name-only record"
        )
    if score.hard_negatives_merged:
        out.append(f"{score.hard_negatives_merged} hard negatives merged")
    return out
