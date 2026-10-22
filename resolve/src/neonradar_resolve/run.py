"""One resolution run (PHASE-2.md 7.1.8, M2.10a deliverable 7).

`run(record_dirs, run_dir, config, decisions_file=None, probabilistic=True)` reads the records,
builds members, feature tables, deterministic links, decisions and hints, calls
`cluster.resolve` and writes `canonical.csv`, `candidates.jsonl`, `conflicts.jsonl` and
`run.json`, with sorted rows so that the first three are byte-stable. The probabilistic models
arrive in M2.10b; until then a run links records by the deterministic rules and decisions only.
"""

from __future__ import annotations

import csv
import json
import logging
import time
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neonradar_resolve import __version__, cluster, features, records, rules, schemas
from neonradar_resolve.config import ResolverConfig

log = logging.getLogger(__name__)

CANONICAL_HEADER = (
    "record_id", "canonical_id", "class", "cluster_size", "method", "rule",
    "match_probability", "via", "path_methods", "features",
)  # fmt: skip
SIZE_BUCKETS = ((1, 1, "1"), (2, 2, "2"), (3, 5, "3-5"), (6, 10, "6-10"), (11, 30, "11-30"))
OUTPUTS = ("canonical.csv", "candidates.jsonl", "conflicts.jsonl", "run.json")


@dataclass(frozen=True)
class RunConfig:
    """What one run needs besides its inputs; the CLI fills it from er.yaml and project.yaml."""

    resolver: ResolverConfig
    config_sha256: str
    senior_reviewers: frozenset[str] = frozenset()  # people.er_senior_reviewers
    profile: str | None = None
    temp_directory: Path | None = None  # DuckDB spill folder: layout.duckdb_tmp_dir(...)
    keep_features: bool = False


@dataclass
class RunResult:
    run_id: str
    run_dir: Path
    members: dict[str, cluster.Member]
    result: cluster.Result
    counts: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)


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
    result: cluster.Result,
) -> dict[str, Any]:
    """The counts of `run.json` (7.1.8): records, links, merges, possible matches, conflicts."""
    sizes = {str(r["canonical_id"]): int(str(r["cluster_size"])) for r in result.canonical}
    links_by_rule = Counter(str(x.rule) for x in links)
    if decisions.same:
        links_by_rule["D7"] = len(decisions.same)
    reasons = Counter(str(r) for c in result.candidates for r in c["reasons"])  # type: ignore[attr-defined]
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
) -> RunResult:
    """Resolve the records of `record_dirs` into `run_dir` (whose name is the run id)."""
    timings: dict[str, float] = {}
    run_dir.mkdir(parents=True, exist_ok=False)
    if probabilistic:
        log.info("the probabilistic models arrive in M2.10b: deterministic rules only")
    features_path = run_dir / features.FEATURES_FILE
    try:
        with _step(timings, "read"):
            corpus = records.read(record_dirs)
        with _step(timings, "features"):
            members = features.members(corpus)
            person, org = features.feature_tables(corpus, members)
            features.write_features(features_path, person, org, config.temp_directory)
        with _step(timings, "rules"):
            links = rules.deterministic(corpus, members)
            decisions = rules.read_decisions(decisions_file)
        with _step(timings, "cluster"):
            result = cluster.resolve(
                members.values(),
                links,
                [],
                decisions.same,
                decisions.different,
                corpus.hints,
                config.resolver.cluster_config(config.senior_reviewers),
                schemas.common_schema,
            )
        counts = count(corpus, members, links, decisions, result)
        with _step(timings, "write"):
            write_canonical(run_dir / "canonical.csv", result.canonical)
            write_jsonl(run_dir / "candidates.jsonl", result.candidates)
            write_jsonl(run_dir / "conflicts.jsonl", result.conflicts)
    finally:  # the feature tables hold record values: never left behind by a failed run
        if not config.keep_features:
            features_path.unlink(missing_ok=True)
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
        "probabilistic": False,  # M2.10b adds the Splink models
        "decisions_used": decisions_file is not None,
        "inputs": [vars(f) for f in corpus.inputs],
        "counts": counts,
        "timings": timings,
    }
    (run_dir / "run.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return RunResult(run_dir.name, run_dir, members, result, counts, timings)
