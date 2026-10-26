"""One resolution run (PHASE-2.md 7.1.8, M2.10a deliverable 7).

`run(record_dirs, run_dir, config, decisions_file=None, probabilistic=True, use_decisions=True)`
reads the records, builds members, feature tables, deterministic links, decisions
(`decisions.load_decisions`, M2.10c) and hints, calls
`cluster.resolve` and writes `canonical.csv`, `candidates.jsonl`, `conflicts.jsonl` and
`run.json`, with sorted rows so that the first three are byte-stable. With `probabilistic`
(M2.10b) it also trains the two Splink models on the run's feature tables (`scoring.py`), passes
their pairs to the clustering, and writes `pairs.parquet` and `models/`.

`guard_decisions` holds back a one-reviewer `same` decision whose merge would join records
with different flag topics or a leaked record with another kind once the rules have run,
because `cluster.resolve` (verbatim) checks D7's second-reviewer rule before the identifier
links, so a later link could otherwise carry a flag across such a decision
(docs/build/phase-2-reconciliation.md 2.8, G1).
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
import time
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neonradar_resolve import __version__, cluster, features, records, rules, schemas, scoring
from neonradar_resolve.config import ResolverConfig
from neonradar_resolve.decisions import count_on_file, load_decisions

log = logging.getLogger(__name__)

CANONICAL_HEADER = (
    "record_id", "canonical_id", "class", "cluster_size", "method", "rule",
    "match_probability", "via", "path_methods", "features",
)  # fmt: skip
SIZE_BUCKETS = ((1, 1, "1"), (2, 2, "2"), (3, 5, "3-5"), (6, 10, "6-10"), (11, 30, "11-30"))
OUTPUTS = ("canonical.csv", "candidates.jsonl", "conflicts.jsonl", "run.json")
PROBABILISTIC_OUTPUTS = ("pairs.parquet", "models")  # with the models (not --no-probabilistic)
# ICIJ link names kept as hints (M2.5); any other hint is counted as source_hint:other.
HINTS = frozenset(
    {
        "same_name_as", "same_id_as", "same_as", "similar", "similar_company_as",
        "same_company_as", "same_intermediary_as", "probably_same_officer_as",
    }
)  # fmt: skip
HINT_REASON = "source_hint:"


class RunError(ValueError):
    """A run that must not continue; the message holds counts and rule ids only."""

    exit_code = 2
    counts_only = True


@dataclass(frozen=True)
class RunConfig:
    """What one run needs besides its inputs; the CLI fills it from er.yaml and project.yaml."""

    resolver: ResolverConfig
    config_sha256: str
    senior_reviewers: frozenset[str] = frozenset()  # people.er_senior_reviewers
    # Handles allowed in the decisions file; None accepts any handle (synthetic profiles).
    reviewers: frozenset[str] | None = None
    profile: str | None = None
    # DuckDB spill folder: layout.duckdb_tmp_dir(...); None: a folder in the run folder
    temp_directory: Path | None = None
    keep_features: bool = False
    # A real profile: a Splink model the data cannot train fails the run instead of being
    # skipped (scoring.score, an orchestrator decision under OD-10). Required, so that no
    # caller can reach a real profile without saying which kind of data it runs on.
    real_data: bool = field(kw_only=True)


@dataclass
class RunResult:
    run_id: str
    run_dir: Path
    members: dict[str, cluster.Member]
    result: cluster.Result
    counts: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)
    probabilistic: dict[str, Any] | None = None  # scoring.Scored.summary(), counts only
    # What `er calibrate` clusters again: the deterministic links and the source hints
    deterministic: list[cluster.Link] = field(default_factory=list)
    hints: list[tuple[str, str, str]] = field(default_factory=list)


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def write_canonical(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CANONICAL_HEADER)
        for row in rows:
            writer.writerow([_cell(row[name]) for name in CANONICAL_HEADER])


def write_jsonl(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def _bucket(size: int) -> str:
    return next((name for low, high, name in SIZE_BUCKETS if low <= size <= high), "over-30")


def count(
    corpus: records.Corpus,
    members: Mapping[str, cluster.Member],
    links: list[cluster.Link],
    decisions: rules.Decisions,
    same: list[cluster.Link],
    result: cluster.Result,
) -> dict[str, Any]:
    """The counts of `run.json` (7.1.8): records, links, merges, possible matches, conflicts."""
    sizes = {str(r["canonical_id"]): int(str(r["cluster_size"])) for r in result.canonical}
    links_by_rule = Counter(str(x.rule) for x in links)
    # D7: decisions passed to the clustering (decisions_applied says how many of them applied);
    # decisions the guard holds back count only in decisions_awaiting_second_review
    applicable = [x for x in same if x.record_a in members and x.record_b in members]
    if applicable:
        links_by_rule["D7"] = len(applicable)
    reasons = Counter(
        _reason_key(str(r))
        for c in result.candidates
        for r in c["reasons"]  # type: ignore[attr-defined]
    )
    return {
        "records_read": sum(f.records for f in corpus.inputs),
        "records_by_class": dict(sorted(Counter(m.entity_class for m in members.values()).items())),
        "links_by_rule": dict(sorted(links_by_rule.items())),
        "merges": len(members) - len(sizes),
        "joined_by_method": dict(
            sorted(Counter(str(r["method"]) for r in result.canonical).items())
        ),
        "possible_matches": len(result.candidates),
        "possible_matches_by_reason": dict(sorted(reasons.items())),
        "conflicts_by_rule": dict(
            sorted(Counter(str(c["rule"]) for c in result.conflicts).items())
        ),
        "cluster_sizes": {
            name: sum(1 for s in sizes.values() if _bucket(s) == name)
            for name in [b[2] for b in SIZE_BUCKETS] + ["over-30"]
        },
        "decisions_on_file": decisions.on_file,
        **result.counts,
    }


def _reason_key(reason: str) -> str:
    """A summary key for a reason: hints outside the allow-list fold into source_hint:other."""
    if reason.startswith(HINT_REASON) and reason[len(HINT_REASON) :] not in HINTS:
        return f"{HINT_REASON}other"
    return reason


def _signature(group: list[cluster.Member]) -> tuple[frozenset[str], frozenset[bool]]:
    """What P1 and P2 compare: the flag topics and whether the records are leaked."""
    return cluster.flags(group), frozenset(m.kind == "leak" for m in group)


Groups = dict[str, list[cluster.Member]]  # record id -> the members of its cluster


def _groups(result: cluster.Result, members: Mapping[str, cluster.Member]) -> Groups:
    by_cluster: dict[str, list[cluster.Member]] = {}
    for row in result.canonical:
        by_cluster.setdefault(str(row["canonical_id"]), []).append(members[str(row["record_id"])])
    return {str(r["record_id"]): by_cluster[str(r["canonical_id"])] for r in result.canonical}


def guard_decisions(
    members: Mapping[str, cluster.Member],
    deterministic: list[cluster.Link],
    probabilistic: list[cluster.Link],
    decisions: rules.Decisions,
    config: cluster.Config,
) -> tuple[list[cluster.Link], int]:
    """The `same` decisions to apply, and how many one-reviewer decisions wait.

    A decision with one reviewer, none of them senior, is held back when, after the rules,
    the strong decisions and the other links, its two records sit in clusters whose flag
    topics differ or of which exactly one holds leaked records (P1, P2). It is also held back
    when, once applied, any record of the cluster it ends up in has other flag topics or leak
    status than that record's cluster had without the one-reviewer decisions (a decision can
    change which later links are refused, and so bring a flag to a third record), and when any
    other record changes so; this repeats until nothing changes. So the order in which
    decisions are applied does not decide what they hold. `probabilistic` must be the very
    list that `cluster.resolve` gets (`run` passes one list object to both).
    """

    def weak(link: cluster.Link) -> bool:
        return len(link.reviewers) < 2 and not link.reviewers & config.senior_reviewers

    def known(link: cluster.Link) -> bool:
        return link.record_a in members and link.record_b in members

    strong = [x for x in decisions.same if not (weak(x) and known(x))]
    pending = [x for x in decisions.same if weak(x) and known(x)]
    if not pending:
        return strong, 0

    def clusters(same: list[cluster.Link]) -> Groups:
        result = cluster.resolve(
            members.values(), deterministic, probabilistic, same, decisions.different, [],
            config, schemas.common_schema,
        )  # fmt: skip
        return _groups(result, members)

    before = clusters(strong)
    kept: list[cluster.Link] = []
    for link in pending:
        left, right = before[link.record_a], before[link.record_b]
        if left is right or _signature(left) == _signature(right):
            kept.append(link)
    while kept:
        after = clusters(strong + kept)
        moved = {
            rid for rid in after if _signature(after[rid]) != _signature(before[rid])
        }  # records whose cluster now has other flag topics or leak status
        if not moved:
            break
        hit = [x for x in kept if any(m.record_id in moved for m in after[x.record_a])]
        decided = {m.record_id for x in kept for m in after[x.record_a]}
        # A record that changed outside every decision's cluster changed through one of them:
        # hold them all back (fail closed), since the cause cannot be told apart.
        kept = [] if moved - decided else [x for x in kept if x not in hit]
    return strong + kept, len(pending) - len(kept)


def resolve(
    members: Mapping[str, cluster.Member],
    deterministic: list[cluster.Link],
    probabilistic: list[cluster.Link],
    decisions: rules.Decisions,
    hints: Iterable[tuple[str, str, str]],
    config: cluster.Config,
) -> tuple[cluster.Result, list[cluster.Link]]:
    """`guard_decisions`, then `cluster.resolve`, with one list of probabilistic links for both.

    Every clustering of a run goes through here (`er calibrate` too); returns the result and
    the `same` decisions passed to the clustering.
    """
    same, held = guard_decisions(members, deterministic, probabilistic, decisions, config)
    result = cluster.resolve(
        members.values(),
        deterministic,
        probabilistic,
        same,
        decisions.different,
        hints,
        config,
        schemas.common_schema,
    )
    result.counts["decisions_awaiting_second_review"] += held
    result.counts["decisions_not_applicable"] += decisions.not_applicable
    return result, same


def remove_features(path: Path) -> None:
    """`features.duckdb`, its write-ahead log and DuckDB's own spill folder beside it."""
    path.unlink(missing_ok=True)
    path.with_name(path.name + ".wal").unlink(missing_ok=True)
    shutil.rmtree(path.with_name(path.name + ".tmp"), ignore_errors=True)


@contextmanager
def _step(timings: dict[str, float], name: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        timings[name] = round(time.perf_counter() - start, 3)


def run(
    record_dirs: Iterable[Path],
    run_dir: Path,
    config: RunConfig,
    decisions_file: Path | None = None,
    probabilistic: bool = True,
    use_decisions: bool = True,
) -> RunResult:
    """Resolve the records of `record_dirs` into `run_dir` (whose name is the run id).

    Without `use_decisions` (`er run --no-decisions`, the evaluation run of 7.3) the decisions
    file is only counted (`decisions_on_file`), never applied, and `decisions_used` is false.
    """
    used = use_decisions and decisions_file is not None
    timings: dict[str, float] = {}
    run_dir.mkdir(parents=True, exist_ok=False)
    features_path = run_dir / features.FEATURES_FILE
    spill = (config.temp_directory / "splink") if config.temp_directory else run_dir / "duckdb-tmp"
    scored: list[cluster.Link] = []  # the Splink pairs: one list for the guard and the run
    found: scoring.Scored | None = None
    try:
        with _step(timings, "read"):
            corpus = records.read(record_dirs)
        with _step(timings, "features"):
            members = features.members(corpus)
            flagged = sum(
                1 for m in members.values() if m.entity_class == "address" and m.flag_topics
            )
            if flagged:  # addresses carry no flags (7.1.1); D6 merges them without P1
                raise RunError(f"{flagged} Address records carry flag topics (7.1.1)")
            person, org = features.feature_tables(corpus, members)
            features.write_features(features_path, person, org, config.temp_directory)
        with _step(timings, "rules"):
            links = rules.deterministic(corpus, members)
            if used:
                decisions = load_decisions(decisions_file, members.keys(), config.reviewers)
            else:
                decisions = rules.Decisions([], [], count_on_file(decisions_file))
        if probabilistic:
            with _step(timings, "models"):
                found = scoring.score(
                    features_path, config.resolver, spill, skip_untrainable=not config.real_data
                )
                scored.extend(scoring.links(found))
            timings.update(found.timings)
        with _step(timings, "cluster"):
            settings = config.resolver.cluster_config(config.senior_reviewers)
            result, same = resolve(members, links, scored, decisions, corpus.hints, settings)
        counts = count(corpus, members, links, decisions, same, result)
        with _step(timings, "write"):
            write_canonical(run_dir / "canonical.csv", result.canonical)
            write_jsonl(run_dir / "candidates.jsonl", result.candidates)
            write_jsonl(run_dir / "conflicts.jsonl", result.conflicts)
            if found is not None:
                scoring.write_pairs(run_dir / "pairs.parquet", scored, members)
                scoring.write_models(run_dir / "models", found)
    finally:  # the feature tables hold record values: never left behind by a failed run
        if not config.keep_features:
            remove_features(features_path)
        shutil.rmtree(spill, ignore_errors=True)  # DuckDB spill files, even after a failure
    resolver = config.resolver
    summary = {
        "run_id": run_dir.name,
        "profile": config.profile,
        "resolver_version": __version__,
        "config_sha256": config.config_sha256,
        "thresholds": {
            "merge_threshold": dict(sorted(resolver.merge_threshold.items())),
            "candidate_threshold": resolver.candidate_threshold,
            "cluster_cap": resolver.cluster_cap,
            "name_check_jaro_winkler": resolver.name_check_jaro_winkler,
        },
        "seed": resolver.seed,
        "probabilistic": probabilistic,
        "splink": found.summary() if found is not None else None,
        "decisions_used": used,
        "inputs": [vars(f) for f in corpus.inputs],
        "counts": counts,
        "timings": timings,
    }
    (run_dir / "run.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return RunResult(
        run_dir.name,
        run_dir,
        members,
        result,
        counts,
        timings,
        found.summary() if found is not None else None,
        links,
        sorted(set(corpus.hints)),
    )
