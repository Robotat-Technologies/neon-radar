"""The read helper (PHASE-4.md 7.5.1), on a fake driver. The integration file runs it on Neo4j."""

import sys
from pathlib import Path

import neo4j
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakeneo4j import Counters, FakeDriver, Summary
from neonradar_graph.readonly import ReadRefused, run_read


def test_a_read_runs_in_read_mode_with_a_timeout_and_never_commits() -> None:
    driver = FakeDriver(lambda name, p: [{"n": i} for i in range(5)])
    result = run_read(driver, "copilot/probe", "RETURN 1", {"x": 1}, max_rows=3, database="neo4j")  # type: ignore[arg-type]
    assert result.rows == [{"n": 0}, {"n": 1}, {"n": 2}] and result.truncated
    assert driver.sessions == [{"database": "neo4j", "default_access_mode": neo4j.READ_ACCESS}]
    tx = driver.transactions[0]
    assert tx.metadata == {"app": "neonradar", "query": "copilot/probe"}
    assert tx.timeout == 5.0 and tx.closed
    assert driver.steps == ["run", "fetch", "consume", "close"]  # the rows before the summary


def test_exactly_max_rows_is_not_truncated() -> None:
    driver = FakeDriver(lambda name, p: [{"n": 1}, {"n": 2}])
    assert not run_read(driver, "q", "RETURN 1", {}, max_rows=2).truncated  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "summary",
    [
        Summary("rw"),
        Summary("w"),
        Summary("s"),
        Summary("r", Counters(contains_updates=True)),
        Summary("r", Counters(contains_system_updates=True)),
    ],
)
def test_anything_but_a_pure_read_is_refused(summary: Summary) -> None:
    driver = FakeDriver(summary=summary)
    with pytest.raises(ReadRefused):
        run_read(driver, "q", "RETURN 1", {}, max_rows=1)  # type: ignore[arg-type]
    assert driver.transactions[0].closed


def test_the_transaction_is_closed_when_the_query_fails() -> None:
    driver = FakeDriver()
    driver.error = RuntimeError("server gone")
    with pytest.raises(RuntimeError):
        run_read(driver, "q", "RETURN 1", {}, max_rows=1)  # type: ignore[arg-type]
    assert driver.transactions[0].closed
