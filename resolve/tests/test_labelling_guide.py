"""The labelling guide's examples come from the synthetic benchmark (PHASE-2.md M2.14).

docs/er/labelling-guide.md shows ten worked examples drawn from data/fixtures/er-bench/, each with
two record ids, the right answer for those cards and the benchmark's answer key. These tests fail
when an id is not a benchmark record (the fixture was regenerated, or an id was mistyped) or when
an answer key disagrees with labels/er_truth.csv.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from neonradar_resolve import bench

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "er" / "labelling-guide.md"
BENCH = ROOT / "data" / "fixtures" / "er-bench"
RECORD_ID = re.compile(r"syn-erb-r-[0-9a-f]+")
EXAMPLE = re.compile(r"^### Example (\d+): ", re.MULTILINE)
PAIR = re.compile(r"^\| Record \| `([^`]+)` \| `([^`]+)` \|$", re.MULTILINE)
RIGHT = re.compile(r"\*\*Right answer:\*\* `(same|different|unsure)`")
TRUTH = re.compile(r"\*\*Benchmark truth:\*\* `(same|different)`")


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _record_ids() -> set[str]:
    ids = set()
    for path in BENCH.glob("*.ftm.jsonl"):
        with path.open(encoding="utf-8") as handle:
            ids.update(json.loads(line)["id"] for line in handle if line.strip())
    return ids


def _examples() -> dict[int, str]:
    """Example number to its text, from the worked examples section to the next section."""
    text = _guide()
    section = text.split("\n## Worked examples\n", 1)[1].split("\n## ", 1)[0]
    starts = list(EXAMPLE.finditer(section))
    return {
        int(match.group(1)): section[match.start() : nxt.start() if nxt else len(section)]
        for match, nxt in zip(starts, [*starts[1:], None], strict=True)
    }


def test_every_record_id_in_the_guide_is_a_benchmark_record() -> None:
    mentioned = set(RECORD_ID.findall(_guide()))
    assert mentioned, "the guide names no benchmark record"
    assert sorted(mentioned - _record_ids()) == []


def test_ten_worked_examples_each_with_one_pair_and_both_answers() -> None:
    examples = _examples()
    assert sorted(examples) == list(range(1, 11))
    for number, text in examples.items():
        assert len(PAIR.findall(text)) == 1, f"example {number}: one Record row with two ids"
        assert len(RIGHT.findall(text)) == 1, f"example {number}: one right answer"
        assert len(TRUTH.findall(text)) == 1, f"example {number}: one benchmark truth"


def test_answer_keys_match_the_benchmark_truth() -> None:
    truth = bench.read_truth(BENCH / "labels" / "er_truth.csv")
    for number, text in _examples().items():
        ((a, b),) = PAIR.findall(text)
        assert a != b and a in truth and b in truth, f"example {number}: two resolvable records"
        same = truth[a].entity == truth[b].entity
        key = TRUTH.search(text)
        right = RIGHT.search(text)
        assert key is not None and right is not None
        assert key.group(1) == ("same" if same else "different"), f"example {number}"
        # A right answer may be `unsure` when the cards do not decide; otherwise it is the key.
        assert right.group(1) in ("unsure", key.group(1)), f"example {number}"


def test_the_examples_cover_each_answer() -> None:
    answers = {m.group(1) for text in _examples().values() for m in RIGHT.finditer(text)}
    assert answers == {"same", "different", "unsure"}
