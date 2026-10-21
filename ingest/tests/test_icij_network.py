"""The real ICIJ spike: needs the internet, never runs in CI (guardrail G3). Run it by hand:

    uv run pytest -m network ingest/tests/test_icij_network.py -s

It reads icij.org's bulk archive over byte ranges and writes the slice to
data/cache/spikes/icij/ (gitignored; `neonradar spike clean` deletes it).
"""

import pytest

from neonradar_contracts.records import validate_files
from neonradar_ingest.sources.icij.spike import run, summary_lines


@pytest.mark.network
def test_real_archive_gives_a_slice_that_validates_strictly() -> None:
    result = run(rows=1000)
    print("\n".join(summary_lines(result)))  # header facts and counts only
    counts, issues = validate_files([result.output], strict=True)
    assert issues == []
    assert result.mode == "range"
    assert counts["Company"] == 1000
