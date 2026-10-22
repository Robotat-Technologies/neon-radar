"""The copilot's benchmark never deviates from the code book (PHASE-4.md 2.10, M4.0)."""

import pytest
import spec_extract as se  # scripts/ is on the test path (pyproject.toml, pythonpath)


@pytest.mark.parametrize(
    "path",
    [
        "copilot/bench/refusals.yaml",
        "data/fixtures/copilot-bench/records.ftm.jsonl",
        "docs/benchmark-questions.md",
    ],
)
def test_the_benchmark_never_deviates(path: str) -> None:
    assert se.never_deviates(path)
    assert not se.never_deviates("copilot/src/neonradar_copilot/memport.py")
