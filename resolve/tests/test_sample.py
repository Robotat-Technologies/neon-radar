"""The evaluation sample (PHASE-2.md 7.3, M2.10c deliverables 2 and 8). Synthetic only."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import layout
from neonradar_resolve import cluster, run, sample
from neonradar_resolve.sample import Frames, Item, SampleError

ADR = (
    Path(__file__).resolve().parents[2]
    / "docs/decisions/0014-entity-resolution-approach-and-thresholds.md"
)
LABELLERS = ["@a", "@b", "@c", "@d"]
CONFIG = cluster.Config({"person": 0.99, "org": 0.995}, 0.8)
runner = CliRunner()


def _member(rid: str, entity_class: str = "person", **kw: Any) -> cluster.Member:
    schema = {"person": "Person", "org": "Company"}[entity_class]
    return cluster.Member(rid, "nr_synthetic", "synthetic", 10, schema, entity_class, True, **kw)


def _common(names: Any) -> str | None:
    return sorted(names)[0] if len(set(names)) == 1 else None


def _run_files(tmp_path: Path) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """A clustering with every path kind, written and read back as a run's files."""
    name = frozenset({"testa example"})
    members = [
        _member("syn-s-a", name_keys=name),  # anchor of a probabilistic cluster
        _member("syn-s-b", name_keys=name),  # joins a by probability
        _member("syn-s-c", name_keys=name),  # joins b by D3: its path holds a probabilistic link
        _member("syn-s-d", "org", company_numbers=frozenset({"SY000001"}), name_keys=name),
        _member("syn-s-e", "org", company_numbers=frozenset({"SY000001"}), name_keys=name),
        _member("syn-s-f", name_keys=name),
        _member("syn-s-g", name_keys=name),  # joins f by a reviewer's decision
        _member("syn-s-h"),
        _member("syn-s-i"),  # a possible match of h
    ]
    p = "probabilistic"
    result = cluster.resolve(
        members,
        [
            cluster.Link("syn-s-b", "syn-s-c", "deterministic", "D3"),
            cluster.Link("syn-s-d", "syn-s-e", "deterministic", "D1"),
        ],
        [
            cluster.Link("syn-s-a", "syn-s-b", p, None, 0.999, 9.0, model="person"),
            cluster.Link("syn-s-h", "syn-s-i", p, None, 0.85, 2.0, model="person"),
        ],
        [cluster.Link("syn-s-f", "syn-s-g", "human", "D7", reviewers=frozenset({"@x", "@y"}))],
        [],
        [],
        CONFIG,
        _common,
    )
    run.write_canonical(tmp_path / "canonical.csv", result.canonical)
    run.write_jsonl(tmp_path / "candidates.jsonl", result.candidates)
    return (
        sample.read_canonical(tmp_path / "canonical.csv"),
        sample.read_candidates(tmp_path / "candidates.jsonl"),
    )


def test_frames_follow_the_path_methods(tmp_path: Path) -> None:
    found = sample.frames(*_run_files(tmp_path))
    assert found.s1 == [Item("S1", "syn-s-b", "syn-s-a"), Item("S1", "syn-s-c", "syn-s-a")]
    # c joined b by D3, and b joined by probability: c is in S1, not S2
    assert found.s2 == [Item("S2", "syn-s-e", "syn-s-d", "D1")]
    assert found.s3 == [Item("S3", "syn-s-h", "syn-s-i")]
    assert found.human == 1


def _frames(n1: int = 500, n2: int = 70, n3: int = 80) -> Frames:
    return Frames(
        [Item("S1", f"syn-r-{i:04d}", f"syn-x-{i:04d}") for i in range(n1)],
        [Item("S2", f"syn-d-{i:04d}", f"syn-y-{i:04d}", f"D{i % 5 + 1}") for i in range(n2)],
        [Item("S3", f"syn-p-{i:04d}", f"syn-q-{i:04d}") for i in range(n3)],
        3,
    )


def test_sampling_is_deterministic_for_a_seed() -> None:
    first, census = sample.draw(_frames(), 7, LABELLERS)
    again, _ = sample.draw(_frames(), 7, LABELLERS)
    other, _ = sample.draw(_frames(), 8, LABELLERS)
    assert first == again and first != other
    assert census == {"S1": False, "S2": False, "S3": False}
    assert Counter(p.stratum for p in first) == {"S1": 400, "S2": 50, "S3": 50}
    assert [p.pair_id for p in first] == [f"pair-{n:04d}" for n in range(1, 501)]


def test_s4_holds_40_s1_and_10_s3_pairs_for_two_different_labellers() -> None:
    pairs, _ = sample.draw(_frames(), 7, LABELLERS)
    overlap = [p for p in pairs if p.overlap]
    assert Counter(p.stratum for p in overlap) == {"S1": 40, "S3": 10}
    assert all(len(set(p.labellers)) == 2 for p in overlap)
    assert all(len(p.labellers) == 1 for p in pairs if not p.overlap)
    load = Counter(h for p in pairs for h in p.labellers)
    assert set(load) == set(LABELLERS) and max(load.values()) - min(load.values()) <= 1


def test_the_strata_are_interleaved() -> None:
    pairs, _ = sample.draw(_frames(), 7, LABELLERS)
    strata = [p.stratum for p in pairs]
    assert set(strata[:60]) == {"S1", "S2", "S3"}
    changes = sum(a != b for a, b in itertools.pairwise(strata))
    assert changes > 100  # 500 pairs grouped by stratum would change twice
    # the anchor is not always on the same side, so the order of a pair says nothing either
    s1 = [p for p in pairs if p.stratum == "S1"]
    assert 100 < sum(p.record_a.startswith("syn-r-") for p in s1) < 300


def test_a_small_frame_is_taken_whole_as_a_census() -> None:
    pairs, census = sample.draw(_frames(30, 70, 5), 7, LABELLERS)
    assert census == {"S1": True, "S2": False, "S3": True}
    found = Counter((p.stratum, p.overlap) for p in pairs)
    assert found == {("S1", True): 30, ("S2", False): 50, ("S3", True): 5}


def test_the_sample_needs_two_different_labellers() -> None:
    for labellers in (["@a"], ["@a", "@a"]):
        with pytest.raises(SampleError, match="two different labellers"):
            sample.draw(_frames(), 7, labellers)


def test_check_run_refuses_a_run_that_used_decisions_on_a_real_profile() -> None:
    for run_json in ({"decisions_used": True}, {}, {"decisions_used": None}):
        with pytest.raises(SampleError, match="er run --no-decisions"):
            sample.check_run(run_json, real_data=True)
        sample.check_run(run_json, real_data=False)  # a synthetic profile may use decisions
    sample.check_run({"decisions_used": False}, real_data=True)


def _adr(status: str, seed: str) -> str:
    return f"# ADR\n\n- **Status:** {status}\n\nEvaluation sample seed: {seed}\n"


def test_check_seed_follows_adr_0014() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert sample.adr_seed(text) == ("proposed", None)  # the seed is set at the freeze
    assert sample.check_seed(text, 7, real_data=True) is None
    accepted = _adr("accepted", "20261029")
    assert sample.check_seed(accepted, 20261029, real_data=True) == 20261029
    with pytest.raises(SampleError, match="another evaluation sample seed"):
        sample.check_seed(accepted, 7, real_data=True)
    with pytest.raises(SampleError, match="sets no evaluation sample seed"):
        sample.check_seed(_adr("accepted", "(set at the freeze)"), 7, real_data=True)
    for unreadable in (None, _adr("superseded", "1"), "no status line"):
        with pytest.raises(SampleError, match="no readable status"):
            sample.check_seed(unreadable, 7, real_data=True)
        sample.check_seed(unreadable, 7, real_data=False)
    assert sample.check_seed(accepted, 7, real_data=False) == 20261029


def test_a_sample_is_never_replaced(tmp_path: Path) -> None:
    found = _frames(20, 5, 3)
    pairs, census = sample.draw(found, 7, LABELLERS)
    counts = sample.sample_counts(found, pairs, census, run_id="er-test", seed=7)
    sample.write_sample(tmp_path, pairs, counts)
    assert sample.read_sample(tmp_path) == (pairs, json.loads(json.dumps(counts)))
    with pytest.raises(SampleError, match="already has a sample"):
        sample.write_sample(tmp_path, pairs, counts)
    assert counts["frames"] == {"s1": 20, "s2": 5, "s3": 3} and counts["human_joined"] == 3


def test_er_sample_draws_once_and_prints_counts_only(data_env: Any) -> None:
    result = runner.invoke(app, ["er", "run", "--profile", "demo", "--no-probabilistic"])
    assert result.exit_code == 0, result.output
    run_id = layout.latest_run("demo")
    assert run_id is not None
    labels = layout.labels_dir("demo", run_id)
    args = ["er", "sample", "--profile", "demo", "--run", "latest", "--seed", "7"]
    result = runner.invoke(app, [*args, "--labellers", "@a,@b,@c"])
    assert result.exit_code == 0, result.output
    assert "sample seed 7 (ADR-0014 sets no evaluation sample seed yet)" in result.output
    assert "syn-" not in result.output  # counts only, never a record id
    pairs, counts = sample.read_sample(labels)
    assert counts["run_id"] == run_id and counts["decisions_used"] is True
    assert len(pairs) == counts["pairs"] and counts["sampled"]["s1"] == 0  # no Splink pairs
    assert list(layout.reports_dir("demo").glob("er-sample-*.json"))
    again = runner.invoke(app, [*args, "--labellers", "@a,@b,@c"])
    assert again.exit_code == 2 and "already has a sample" in again.output
    bad = runner.invoke(app, [*args, "--labellers", "@a,not a handle"])
    assert bad.exit_code == 2 and "not a GitHub handle" in bad.output


def test_er_sample_on_a_real_profile_runs_the_gate_first(data_env: Any) -> None:
    args = ["--run", "latest", "--seed", "7", "--labellers", "@a,@b"]
    result = runner.invoke(app, ["er", "sample", "--profile", "uk-tiny", *args])
    assert result.exit_code == 3, result.output
    assert not (data_env.cache / "real").exists()
