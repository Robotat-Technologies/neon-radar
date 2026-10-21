"""Counts-only summaries (PHASE-2.md M2.2 deliverable 9)."""

import json
from typing import Any

import pytest

from neonradar_cli import summary
from neonradar_cli.summary import SummaryRefused, clean, emit


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"name": "Petra Marlowe"}, "summary.name: a string under a key that is not allowed"),
        ({"first_record": {"id": "syn-off-0101"}}, "summary.first_record.id: a string"),
        ({"status": "x" * 81}, "not a short string"),
        ({"status": "line\nbreak"}, "not a short string"),
        ({"dataset": "Ünïcode"}, "not a short string"),
        ({"names": ["Petra Marlowe"]}, "a list under a key that is not registered"),
        ({"headers": ["ok", "x" * 81]}, "a list item that is not a short string"),
        ({"Petra Marlowe": 1}, "a key that is not a lower-case name"),
        ({"kinds_by_value": {"Company": 12}}, "a key that is not a lower-case name"),
        ({"kinds_by_value": {"company": "12"}}, "must be a whole count"),
        ({"rate": float("nan")}, "not a finite number"),
        ({"when": object()}, "a object is not allowed"),
    ],
)
def test_record_like_values_are_refused(value: dict[str, Any], message: str) -> None:
    with pytest.raises(SummaryRefused, match=message) as refused:
        clean(value)
    assert "Petra" not in str(refused.value) and "syn-off" not in str(refused.value)


def test_allowed_values_pass() -> None:
    value = {
        "profile": "uk-tiny",
        "records": 12,
        "rate": 0.5,
        "complete": True,
        "missing": None,
        "threshold_match": "0.92",
        "headers": ["CompanyName", " CompanyNumber"],
        "datasets": {"gb_companies_house": {"status": "ok", "version": "2026-10-01"}},
    }
    assert clean(value) == value


def test_registered_string_and_list_keys() -> None:
    value = {"slice_sha256": "ab" * 32, "lei_headers": ["LEI", "Entity.LegalName"]}
    with pytest.raises(SummaryRefused):
        clean(value)
    cleaned = clean(value, string_keys=["slice_sha256"], list_keys=["lei_headers"])
    assert cleaned == value


def test_rare_vocabulary_values_are_folded() -> None:
    value = {"natures_by_value": {"ownership-of-shares-25-to-50-percent": 40, "voting": 9, "x": 1}}
    assert clean(value) == {
        "natures_by_value": {"ownership-of-shares-25-to-50-percent": 40},
        "natures_by_value_rare": 10,
    }
    nested = clean({"datasets": {"gb": {"kinds_by_value": {"company": 3}}}})
    assert nested == {"datasets": {"gb": {"kinds_by_value": {}, "kinds_by_value_rare": 3}}}


def test_emit_prints_and_writes_the_report(
    data_env: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    written = emit("demo", "ingest build", {"profile": "demo", "records": 3})
    emit("demo", "ingest build", {"profile": "demo", "records": 4})  # same second: a new file
    files = sorted((data_env.cache / "reports" / "demo").iterdir(), key=lambda f: len(f.name))
    assert len(files) == 2 and all(f.name.startswith("ingest-build-2") for f in files)
    assert files[1].name == files[0].name.replace(".json", "-2.json")
    assert json.loads(files[0].read_text(encoding="utf-8")) == written
    assert '"records": 3' in capsys.readouterr().out


def test_emit_refuses_before_writing(data_env: Any) -> None:
    with pytest.raises(SummaryRefused):
        emit("demo", "data fetch", {"name": "Petra Marlowe"})
    assert not (data_env.cache / "reports").exists()
    assert summary.SummaryRefused.exit_code == 1
