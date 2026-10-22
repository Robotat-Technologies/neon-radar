"""The Phase 4 additions to scripts/spec_extract.py and the Makefile (PHASE-4.md 2.10, M4.0)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import spec_extract as se

BENCHMARK = [
    "copilot/bench/benchmark.yaml",
    "copilot/bench/refusals.yaml",
    "data/fixtures/copilot-bench/records.ftm.jsonl",
    "docs/benchmark-questions.md",
]


@pytest.mark.parametrize("path", BENCHMARK)
def test_the_benchmark_never_deviates(tmp_path: Path, path: str) -> None:
    row = {"sha256": "0" * 64, "milestone": "M4.3b", "reason": "import path"}
    record = tmp_path / "deviations.json"
    record.write_text(json.dumps({path: row}))
    assert se.never_deviates(path)
    with pytest.raises(se.BookError, match="never deviates"):
        se.deviations(record)


def test_other_copilot_files_may_record_a_mechanical_deviation() -> None:
    assert not se.never_deviates("copilot/src/neonradar_copilot/memport.py")
    assert not se.never_deviates("docs/benchmark-questions.txt")


@pytest.mark.parametrize(
    ("milestone", "book", "deviations"),
    [
        ("M4.0", "docs/build/PHASE-4-CODE.md", "docs/build/phase-4-deviations.json"),
        ("M4.3a", "docs/build/PHASE-4-CODE.md", "docs/build/phase-4-deviations.json"),
        ("M3.0", "docs/build/PHASE-3-CODE.md", "docs/build/phase-3-deviations.json"),
        ("M3.5a", "docs/build/PHASE-3-CODE.md", "docs/build/phase-3-deviations.json"),
    ],
)
def test_make_picks_the_book_from_the_milestone_id(
    milestone: str, book: str, deviations: str
) -> None:
    for target in ("spec-check", "spec-extract"):
        result = subprocess.run(
            ["make", "-n", target, f"M={milestone}", "REF=/tmp/m4-ref"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        assert f"--milestone {milestone} --book {book} --deviations {deviations}" in result.stdout
    assert "--reference /tmp/m4-ref" in result.stdout
