"""The decisions file (PHASE-2.md 7.1.8, M2.10c deliverables 1, 6 and 8). Synthetic only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from nr_resolve_support import syn

from neonradar_resolve import decisions, run
from neonradar_resolve.config import load_config
from neonradar_resolve.decisions import DecisionsError

CONFIG = Path(__file__).resolve().parents[1] / "config" / "er.yaml"
RUN_IDS = {"syn-test-a1", "syn-test-a2", "syn-test-b1", "syn-test-b2"}


def _file(tmp_path: Path, lines: list[dict[str, Any]]) -> Path:
    path = tmp_path / "decisions.jsonl"
    base = {"note": "synthetic test line"}
    path.write_text("".join(json.dumps(base | line) + "\n" for line in lines), encoding="utf-8")
    return path


def _line(a: str, b: str, decision: str, by: str, at: str) -> dict[str, str]:
    return {"record_a": a, "record_b": b, "decision": decision, "by": by, "at": at}


def test_the_newest_line_wins(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        [
            _line("syn-test-a1", "syn-test-a2", "different", "@example-one", "2026-11-02T10:05Z"),
            _line("syn-test-a2", "syn-test-a1", "same", "@example-two", "2026-11-02T10:00Z"),
            # same time as the first line: the later line decides
            _line("syn-test-b1", "syn-test-b2", "same", "@example-one", "2026-11-02T11:00Z"),
            _line("syn-test-b1", "syn-test-b2", "different", "@example-two", "2026-11-02T11:00Z"),
        ],
    )
    found = decisions.load_decisions(path, RUN_IDS)
    assert found.same == []
    assert found.different == [("syn-test-a1", "syn-test-a2"), ("syn-test-b1", "syn-test-b2")]
    assert (found.on_file, found.not_applicable) == (2, 0)


def test_supporters_are_counted_per_handle(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        [
            _line("syn-test-a1", "syn-test-a2", "same", "@example-one", "2026-11-02T10:00Z"),
            _line("syn-test-a1", "syn-test-a2", "same", "@example-one", "2026-11-02T10:01Z"),
            _line("syn-test-a1", "syn-test-a2", "same", "@Example-Two", "2026-11-02T10:02Z"),
            # @example-three said same, then different: not a supporter
            _line("syn-test-a1", "syn-test-a2", "same", "@example-three", "2026-11-02T10:03Z"),
            _line("syn-test-a1", "syn-test-a2", "different", "@example-three", "2026-11-02T10:04Z"),
            _line("syn-test-a1", "syn-test-a2", "same", "@example-one", "2026-11-02T10:05Z"),
        ],
    )
    [link] = decisions.load_decisions(path, RUN_IDS).same
    assert (link.method, link.rule) == ("human", "D7")
    assert link.reviewers == {"@example-one", "@example-two"}


def test_a_decision_about_a_record_outside_the_run_is_counted_not_applied(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        [
            _line("syn-test-a1", "syn-test-a2", "same", "@example-one", "2026-11-02T10:00Z"),
            _line("syn-test-a1", "syn-other-1", "same", "@example-one", "2026-11-02T10:00Z"),
            _line("syn-other-1", "syn-other-2", "different", "@example-one", "2026-11-02T10:00Z"),
            _line("syn-test-b1", "syn-test-b2", "different", "@example-one", "2026-11-02T10:00Z"),
        ],
    )
    found = decisions.load_decisions(path, RUN_IDS)
    assert [(x.record_a, x.record_b) for x in found.same] == [("syn-test-a1", "syn-test-a2")]
    assert found.different == [("syn-test-b1", "syn-test-b2")]
    assert (found.on_file, found.not_applicable) == (4, 2)
    assert decisions.load_decisions(None, RUN_IDS).on_file == 0


def test_supporters_name_the_handles_behind_a_newest_same(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        [
            _line("syn-test-a1", "syn-test-a2", "same", "@example-one", "2026-11-02T10:00:00Z"),
            _line("syn-test-a2", "syn-test-a1", "same", "@example-two", "2026-11-02T10:05:00Z"),
            _line("syn-test-b1", "syn-test-b2", "same", "@example-one", "2026-11-02T10:00:00Z"),
            _line("syn-test-b2", "syn-test-b1", "different", "@example-two", "2026-11-02T11:00Z"),
        ],
    )
    both = {"@example-one", "@example-two"}
    assert decisions.supporters(path, "syn-test-a2", "syn-test-a1") == both
    assert decisions.supporters(path, "syn-test-b1", "syn-test-b2") == frozenset()  # X8 now
    assert decisions.supporters(None, "syn-test-a1", "syn-test-a2") == frozenset()


def test_append_decision_refuses_same_without_a_note(tmp_path: Path) -> None:
    path = tmp_path / "data" / "decisions.jsonl"
    for note in (None, "", "   "):
        with pytest.raises(DecisionsError, match="needs a note"):
            decisions.append_decision(path, "syn-test-a1", "syn-test-a2", "same", "@ex", note)
    assert not path.exists()
    at = datetime(2026, 11, 2, 10, 15, tzinfo=UTC)
    decisions.append_decision(path, "syn-test-b2", "syn-test-b1", "different", "@Ex", None, at=at)
    decisions.append_decision(
        path, "syn-test-a1", "syn-test-a2", "same", "@ex", " same birth month ", at=at
    )
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert lines[0] == {
        "record_a": "syn-test-b1", "record_b": "syn-test-b2", "decision": "different",
        "by": "@ex", "at": "2026-11-02T10:15:00Z", "note": None,
    }  # fmt: skip
    assert lines[1]["note"] == "same birth month"
    found = decisions.load_decisions(path, RUN_IDS)
    assert [x.reviewers for x in found.same] == [{"@ex"}]
    assert found.different == [("syn-test-b1", "syn-test-b2")]


@pytest.mark.parametrize(
    ("a", "b", "decision", "by", "message"),
    [
        ("syn-test-a1", "syn-test-a2", "maybe", "@ex", "same or different"),
        ("syn-test-a1", "syn-test-a2", "different", "example", "GitHub handle"),
        ("syn-test-a1", "syn-test-a1", "different", "@ex", "two different records"),
        ("syn-test-a1", "", "different", "@ex", "two record ids"),
    ],
)
def test_append_decision_refuses_other_lines(
    tmp_path: Path, a: str, b: str, decision: str, by: str, message: str
) -> None:
    with pytest.raises(DecisionsError, match=message):
        decisions.append_decision(tmp_path / "d.jsonl", a, b, decision, by, "a note")


def _run(tmp_path: Path, name: str, path: Path, use: bool) -> dict[str, Any]:
    folder = tmp_path / "records"
    if not folder.exists():
        folder.mkdir()
        person = {"name": "Testa Example", "birthDate": "1970-01-02"}
        items = [
            syn("syn-test-a1", "Person", **person),
            syn("syn-test-a2", "Person", kind="list", topics="sanction", **person),
            syn("syn-test-b1", "Person", **person),
            syn("syn-test-b2", "Person", **person),
        ]
        lines = "".join(json.dumps(x) + "\n" for x in items)
        (folder / "test.ftm.jsonl").write_text(lines, encoding="utf-8")
    resolver, sha = load_config(CONFIG)
    config = run.RunConfig(resolver, sha, temp_directory=tmp_path / "spill")
    result = run.run(
        [folder], tmp_path / name, config, path, probabilistic=False, use_decisions=use
    )
    data: dict[str, Any] = json.loads((result.run_dir / "run.json").read_text(encoding="utf-8"))
    return data


def test_a_run_without_decisions_counts_the_file_and_applies_nothing(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        [
            # one reviewer, across P1 (a listed and an unlisted record): waits (D7)
            _line("syn-test-a1", "syn-test-a2", "same", "@example-one", "2026-11-02T10:00Z"),
            _line("syn-test-b1", "syn-test-b2", "same", "@example-one", "2026-11-02T10:00Z"),
            _line("syn-test-b1", "syn-gone-1", "different", "@example-one", "2026-11-02T10:00Z"),
        ],
    )
    used = _run(tmp_path, "with", path, use=True)
    assert used["decisions_used"] is True
    counts = used["counts"]
    assert (counts["decisions_on_file"], counts["decisions_not_applicable"]) == (3, 1)
    assert counts["decisions_awaiting_second_review"] == 1  # the guard still holds it back
    assert counts["decisions_applied"] == 1 and counts["merges"] == 1
    ignored = _run(tmp_path, "without", path, use=False)
    assert ignored["decisions_used"] is False
    counts = ignored["counts"]
    assert counts["decisions_on_file"] == 3
    assert counts["decisions_applied"] == counts["decisions_not_applicable"] == 0
    assert counts["decisions_awaiting_second_review"] == 0 and counts["merges"] == 0
    assert "D7" not in counts["links_by_rule"]


def test_review_queue_order_and_what_it_leaves_out(tmp_path: Path) -> None:
    clusters = {
        "syn-c1": ["syn-c1"],
        "syn-c2": ["syn-c2"],
        "nr-syn-c3": ["syn-c3", "syn-c3b"],
        "syn-c4": ["syn-c4"],
        "syn-c5": ["syn-c5"],
        "syn-c6": ["syn-c6"],
    }

    def match(a: str, b: str, p: float | None) -> dict[str, Any]:
        rb = clusters[b][0]
        return {"a": a, "b": b, "record_a": clusters[a][0], "record_b": rb, "match_probability": p}

    candidates = [
        match("syn-c1", "syn-c2", None),
        match("syn-c1", "syn-c4", 0.9),
        match("syn-c2", "syn-c4", 0.95),
        match("nr-syn-c3", "syn-c5", 0.85),
        match("syn-c5", "syn-c6", 0.97),
        match("syn-c4", "syn-c6", 0.99),
    ]
    path = _file(
        tmp_path,
        [
            # a different decision about another record of the cluster: X8 for the clusters
            _line("syn-c3b", "syn-c5", "different", "@example-two", "2026-11-02T10:00Z"),
            # same with two supporters: a run applies it
            _line("syn-c5", "syn-c6", "same", "@example-two", "2026-11-02T10:00Z"),
            _line("syn-c5", "syn-c6", "same", "@example-three", "2026-11-02T10:01Z"),
            # this reviewer's own decision
            _line("syn-c4", "syn-c6", "different", "@example-one", "2026-11-02T10:00Z"),
            # one supporter, not senior: other reviewers still see the pair
            _line("syn-c2", "syn-c4", "same", "@example-two", "2026-11-02T10:00Z"),
        ],
    )
    queue = decisions.review_queue(candidates, path, "@example-one", set(), clusters)
    assert [(c["a"], c["b"]) for c in queue] == [
        ("syn-c2", "syn-c4"),
        ("syn-c1", "syn-c4"),
        ("syn-c1", "syn-c2"),  # no probability: last
    ]
    seniors = {"@example-two"}
    queue = decisions.review_queue(candidates, path, "@example-one", seniors, clusters)
    assert ("syn-c2", "syn-c4") not in [(c["a"], c["b"]) for c in queue]
    # a real profile reads the file as er run does: a line by an unlisted handle fails instead
    # of hiding a pair or a second supporter
    listed = frozenset({"@example-one", "@example-two"})
    with pytest.raises(DecisionsError, match=r"not in people\.er_labellers"):
        decisions.review_queue(candidates, path, "@example-one", set(), clusters, listed)
    with pytest.raises(DecisionsError, match=r"not in people\.er_labellers"):
        decisions.supporters(path, "syn-c5", "syn-c6", listed)
    listed |= {"@example-three"}
    assert (
        len(decisions.review_queue(candidates, path, "@example-one", set(), clusters, listed)) == 3
    )
    assert decisions.supporters(path, "syn-c6", "syn-c5", listed) == {
        "@example-two",
        "@example-three",
    }


def test_er_review_refuses_to_run_without_a_terminal(tmp_path: Path, data_env: Any) -> None:
    code = "from neonradar_cli.main import app; app()"
    command = [sys.executable, "-c", code, "er", "review", "--profile", "demo", "--run", "latest"]
    result = subprocess.run(  # noqa: S603 (this interpreter; stdin closed: not a terminal, G10)
        [*command, "--reviewer", "@example-one"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=tmp_path,
        env={**os.environ, "NR_PROJECT_FILE": str(data_env.project)},
    )
    assert result.returncode == 2, result.stderr
    assert "er review is for a person at a terminal" in result.stderr
