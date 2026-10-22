"""Resolution runs end to end on synthetic data (PHASE-2.md M2.10a deliverables 7 to 10).

`er run --profile demo` reads data/fixtures/demo-mini and data/fixtures/er-bench; every folder
it writes is under the temporary tree of the `data_env` fixture (conftest.py).
"""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_contracts.datasets import load_registry
from neonradar_ingest.data import layout
from neonradar_ingest.data.project import REPO_ROOT
from neonradar_resolve import bench, records, run
from neonradar_resolve.config import load_config

BENCH = REPO_ROOT / "data" / "fixtures" / "er-bench"
TRUTH = Path("labels") / "er_truth.csv"
STABLE = ("canonical.csv", "candidates.jsonl", "conflicts.jsonl")
runner = CliRunner()


def _er(*args: str) -> Any:
    result = runner.invoke(app, ["er", *args])
    assert result.exit_code == 0, result.output
    return result


def _latest_run(data_env: Any) -> Path:
    run_id = layout.latest_run("demo")
    assert run_id is not None
    return layout.resolution_dir("demo", run_id)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_er_run_demo_writes_byte_stable_files(data_env: Any) -> None:
    _er("run", "--profile", "demo", "--no-probabilistic")
    first = _latest_run(data_env)
    assert sorted(p.name for p in first.iterdir()) == sorted(run.OUTPUTS)  # features deleted
    _er("run", "--profile", "demo", "--no-probabilistic")
    second = _latest_run(data_env)
    assert first != second
    for name in STABLE:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name
    assert (
        (first / "canonical.csv")
        .read_text(encoding="utf-8")
        .startswith(
            "record_id,canonical_id,class,cluster_size,method,rule,match_probability,via,path_methods,features\n"
        )
    )
    info = json.loads((second / "run.json").read_text(encoding="utf-8"))
    assert info["run_id"] == second.name and info["profile"] == "demo"
    assert info["decisions_used"] is True and info["probabilistic"] is False
    assert {i["file"] for i in info["inputs"]} == {
        "nr_synthetic-20261023-demo-mini.ftm.jsonl",
        "nr_synthetic-20261026-er-bench.ftm.jsonl",
    }
    assert info["counts"]["links_by_rule"]["D1"] > 0
    reports = list(layout.reports_dir("demo").glob("er-run-*.json"))
    assert len(reports) == 2
    assert not list((data_env.cache / "synthetic" / "duckdb-tmp").glob("*"))  # spill removed


def test_er_run_demo_anchors_and_hard_negatives(data_env: Any) -> None:
    _er("run", "--profile", "demo", "--no-probabilistic")
    rows = _rows(_latest_run(data_env) / "canonical.csv")
    corpus = records.read([REPO_ROOT / "data/fixtures/demo-mini", BENCH])
    priority = {s.slug: s.anchor_priority for s in load_registry().datasets}
    clusters: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        clusters[row["canonical_id"]].append(row)
    for cid, group in clusters.items():
        if len(group) == 1:
            assert cid == group[0]["record_id"] and group[0]["method"] == "identity"
            continue
        anchor = min(
            (priority[corpus.records[r["record_id"]].dataset], r["record_id"]) for r in group
        )[1]
        assert cid == f"nr-{anchor}"
        methods = {r["record_id"]: r["method"] for r in group}
        assert methods.pop(anchor) == "anchor"
        assert set(methods.values()) <= {"deterministic", "human"}
    truth = bench.read_truth(BENCH / TRUTH)
    cluster_of = {r["record_id"]: r["canonical_id"] for r in rows}
    entity_clusters: dict[str, set[str]] = defaultdict(set)
    for rid, t in truth.items():
        entity_clusters[t.entity].add(cluster_of[rid])
    merged_twins = [
        t.entity
        for t in truth.values()
        if t.twin_of and entity_clusters[t.entity] & entity_clusters[t.twin_of]
    ]
    assert merged_twins == []


def _write_decisions(path: Path) -> None:
    """Three decisions about benchmark records chosen from the truth file (never from ids)."""
    truth = bench.read_truth(BENCH / TRUTH)
    styles: dict[str, dict[str, str]] = defaultdict(dict)
    for rid in sorted(truth):
        styles[truth[rid].entity].setdefault(truth[rid].style, rid)
    # a person's officer record and list record: the merge crosses P1 (the list record's flag,
    # which no deterministic rule can join to an officer record), and one reviewer must wait
    crossing = next(
        (s["officer"], s["list"])
        for e, s in sorted(styles.items())
        if truth[next(iter(s.values()))].entity_class == "person" and {"officer", "list"} <= set(s)
    )
    twin = next(t for _, t in sorted(truth.items()) if t.twin_of)
    hard_negative = (min(styles[twin.entity].values()), min(styles[twin.twin_of].values()))
    lines = [
        (*crossing, "same"),
        ("syn-gone-1", "syn-gone-2", "different"),  # records outside the run: not applicable
        (*hard_negative, "different"),  # a hard negative pair marked different: applied (X8)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for a, b, decision in lines:
            line = {"record_a": a, "record_b": b, "decision": decision, "by": "@one"}
            line |= {"at": "2026-11-02T10:00:00Z", "note": "synthetic test decision"}
            handle.write(json.dumps(line) + "\n")


def test_er_run_counts_decisions_and_no_decisions_ignores_them(data_env: Any) -> None:
    _write_decisions(layout.decisions_file("demo"))
    _er("run", "--profile", "demo", "--no-probabilistic")
    counts = json.loads((_latest_run(data_env) / "run.json").read_text(encoding="utf-8"))["counts"]
    assert counts["decisions_on_file"] == 3
    assert counts["decisions_awaiting_second_review"] == 1
    assert counts["decisions_not_applicable"] == 1
    assert counts["decisions_applied"] == 1
    _er("run", "--profile", "demo", "--no-probabilistic", "--no-decisions")
    info = json.loads((_latest_run(data_env) / "run.json").read_text(encoding="utf-8"))
    assert info["decisions_used"] is False
    assert info["counts"]["decisions_on_file"] == 0
    assert info["counts"]["decisions_applied"] == 0


def test_er_run_refuses_a_profile_without_resolution(data_env: Any) -> None:
    data_env.write_profile(
        "no-er", real_data=False, sources={"nr_synthetic": {"enabled": True, "fixtures": []}}
    )
    result = runner.invoke(app, ["er", "run", "--profile", "no-er"])
    assert result.exit_code == 2 and "resolution.enabled: false" in result.output


def test_er_show_config_and_bench(data_env: Any) -> None:
    shown = json.loads(_er("show-config").output)
    assert shown["merge_threshold"] == {"person": 0.99, "org": 0.995}
    assert (shown["candidate_threshold"], shown["cluster_cap"], shown["seed"]) == (
        0.8,
        30,
        20261026,
    )
    output = _er("bench", "--size", "small").output
    assert "hard negatives merged: 0" in output
    assert output.splitlines()[0].startswith("person  precision ")
    assert list(layout.reports_dir("er-bench-small").glob("er-bench-*.json"))


def _opaque_copy(source: Path, target: Path, seed: int | None) -> None:
    """The benchmark with every record and entity id replaced by an opaque id (the truth too).

    With `seed=None` the opaque ids keep the original sort order; with a seed they are shuffled.
    """
    items = list(records.iter_records(next(source.glob("*.ftm.jsonl"))))
    truth_lines = (source / TRUTH).read_text(encoding="utf-8").splitlines()
    ids = sorted(str(item["id"]) for item in items)
    entities = sorted({line.split(",")[1] for line in truth_lines[2:]})
    if seed is not None:
        rng = random.Random(seed)  # noqa: S311 - a reproducible shuffle, not a secret
        for group in (ids, entities):
            rng.shuffle(group)
    new = {old: f"syn-opq-{n:05d}" for n, old in enumerate(ids)}
    new |= {old: f"syn-ent-{n:05d}" for n, old in enumerate(entities)}
    target.mkdir(parents=True)
    with (target / "opaque.ftm.jsonl").open("w", encoding="utf-8") as handle:
        for item in sorted(items, key=lambda x: new[str(x["id"])]):
            item["id"] = new[str(item["id"])]
            props = item["properties"]
            for key, values in props.items():
                props[key] = [new.get(v, v) for v in values]
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    (target / "labels").mkdir()
    rows = [truth_lines[0], truth_lines[1]]
    for line in truth_lines[2:]:
        rid, entity, cls, style, twin = line.split(",")
        rows.append(",".join([new[rid], new[entity], cls, style, new[twin] if twin else ""]))
    (target / TRUTH).write_text("\n".join(rows) + "\n", encoding="utf-8")


def _scores(tmp_path: Path, seed: int | None) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    resolver, sha = load_config(REPO_ROOT / "resolve" / "config" / "er.yaml")
    config = run.RunConfig(resolver, sha, temp_directory=tmp_path / "spill")
    opaque = tmp_path / "opaque"
    _opaque_copy(BENCH, opaque, seed)
    scores = []
    for name, folder in (("original", BENCH), ("opaque", opaque)):
        result = run.run([folder], tmp_path / "runs" / name, config, probabilistic=False)
        truth = bench.read_truth(folder / TRUTH)
        score = bench.measure(
            truth, result.members, result.result.canonical, result.result.candidates
        )
        scores.append((bench.as_counts(score), result.counts))
    return scores


def test_benchmark_ids_are_opaque_to_the_resolver(tmp_path: Path) -> None:
    """The ids `syn-erb-<p|o>-<entity>-<record>` hold the true entity. Renaming every id to an
    opaque one in the same order (and the truth with it) changes no measure and no count, so no
    rule, feature or blocking key reads the id text."""
    original, opaque = _scores(tmp_path, None)
    assert original == opaque
    assert original[0]["hard_negatives_merged"] == 0


def test_shuffled_benchmark_ids_change_only_the_order_of_links(tmp_path: Path) -> None:
    """With shuffled opaque ids, 7.1.6 takes the links in another order. A strict name check
    across P1 or P2 compares the two linked records, so a few organisation records can end up
    in another cluster; precision, the hard negatives and the classes' recall stay put."""
    (original, _), (shuffled, _) = _scores(tmp_path, 20261026)
    assert shuffled["hard_negatives_merged"] == original["hard_negatives_merged"] == 0
    for name in bench.CLASSES:
        assert shuffled[name]["precision"] == original[name]["precision"]
        assert shuffled[name]["mergeable_true_pairs"] == original[name]["mergeable_true_pairs"]
        assert abs(shuffled[name]["recall"] - original[name]["recall"]) <= 0.01
    assert shuffled["policy_blocked_pairs"] == original["policy_blocked_pairs"]
    assert abs(shuffled["policy_blocked_recall"] - original["policy_blocked_recall"]) <= 0.01
