"""L18 steps 1 and 2 without a database (C2 1.2.0, PHASE-3.md M3.4): the record checks and the
bridge check refuse a doctored overlay with exit 2, and the real-data instance refuses a profile
outside `access.real_overlay_profiles` with exit 3, before anything connects."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from neonradar_graph.instances import Instance
from neonradar_graph.overlay import (
    OverlayInstanceRefused,
    OverlayRefused,
    load_overlay,
    plan_overlay,
)

from .conftest import record

BASE, OTHER = "syn-co-0000000001", "syn-co-0000000002"  # base companies (no overlay prefix)
Records = list[dict[str, Any]]


def sound() -> Records:
    """Two overlay accounts, one held by a base company, and a payment between them."""
    return [
        record("syn-ov-acct-1", "BankAccount", accountNumber="NRSYN0000000001", currency="GBP"),
        record("syn-ov-acct-2", "BankAccount", accountNumber="NRSYN0000000002", currency="GBP"),
        record("syn-ov-co-1", "Company", name="Synthetic Example Ltd"),
        record("syn-ov-own-1", "Ownership", owner=BASE, asset="syn-ov-acct-1",
               role="account holder"),
        record("syn-ov-own-2", "Ownership", owner="syn-ov-co-1", asset="syn-ov-acct-2",
               role="account holder"),
        record("syn-ov-pay-1", "Payment", {"channel": "wire"}, payer=BASE,
               payerAccount="syn-ov-acct-1", beneficiary="syn-ov-co-1",
               beneficiaryAccount="syn-ov-acct-2", amount="250", currency="GBP",
               date="2025-03-04T10:00:00"),
    ]  # fmt: skip


def props(records: Records, rid: str) -> dict[str, Any]:
    found: dict[str, Any] = next(r for r in records if r["id"] == rid)["properties"]
    return found


CHANGES: dict[str, Callable[[Records, dict[str, Any]], object]] = {
    "a directorship names a base company": lambda rs, _: rs.append(
        record("syn-ov-dir-1", "Directorship", director="syn-ov-co-1", organization=BASE)
    ),
    "an id without the overlay prefix": lambda rs, _: rs.append(
        record("syn-co-0000000009", "Company", name="Synthetic Example Ltd")
    ),
    "a record of another dataset too": lambda rs, _: rs[2].update(
        datasets=["nr_synthetic", "gb_companies_house"]
    ),
    "a payment names a base record as an account": lambda rs, _: props(rs, "syn-ov-pay-1").update(
        beneficiaryAccount=[OTHER]
    ),
    "a payer that does not hold its account": lambda rs, _: props(rs, "syn-ov-pay-1").update(
        payerAccount=["syn-ov-acct-2"], beneficiaryAccount=["syn-ov-acct-1"]
    ),
    "a payment between two accounts of base holders": lambda rs, _: (
        props(rs, "syn-ov-own-2").update(owner=[OTHER]),
        props(rs, "syn-ov-pay-1").update(beneficiary=[OTHER]),
    ),
    "a base holding with another role": lambda rs, _: props(rs, "syn-ov-own-1").update(
        role=["shareholder"]
    ),
    "overlay.json names another profile": lambda _, meta: meta.update(profile="synth-eval"),
}


def test_a_sound_overlay_plans_its_rows_and_names_its_base_references() -> None:
    plan, refs = plan_overlay(sound(), {"profile": "synth-demo"}, "synth-demo")
    assert refs == [BASE]
    holding = next(row for row in plan.relationships if row.id == "syn-ov-own-1")
    assert (holding.type, holding.source, holding.resolving) == ("HOLDS_ACCOUNT", BASE, True)
    assert {row.id for row in plan.nodes} == {"syn-ov-acct-1", "syn-ov-acct-2", "syn-ov-co-1"}


class NoDriver:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError("connected before L18 steps 1 and 2 passed")


def write(folder: Path, records: Records, meta: dict[str, Any]) -> Path:
    folder.mkdir()
    lines = "".join(json.dumps(item) + "\n" for item in records)
    (folder / "overlay.ftm.jsonl").write_text(lines, encoding="utf-8")
    (folder / "overlay.json").write_text(json.dumps(meta), encoding="utf-8")
    return folder


@pytest.mark.parametrize("change", sorted(CHANGES))
def test_a_doctored_overlay_stops_with_exit_2_before_connecting(
    change: str, tmp_path: Path
) -> None:
    records, meta = sound(), {"profile": "synth-demo"}
    CHANGES[change](records, meta)
    folder = write(tmp_path / "overlay", records, meta)
    with pytest.raises(OverlayRefused) as refused:
        load_overlay(folder, "synth-demo", Instance.DEFAULT, driver=NoDriver(), database="neo4j")  # type: ignore[arg-type]
    assert refused.value.exit_code == 2
    assert "syn-co-" not in str(refused.value)  # counts only: a base id could be real


def test_the_real_data_instance_takes_only_a_listed_profile_s_overlay(tmp_path: Path) -> None:
    with pytest.raises(OverlayInstanceRefused) as refused:  # the folder is never read
        load_overlay(tmp_path / "missing", "uk-tiny", Instance.REAL, ["uk-sample"])
    assert refused.value.exit_code == 3
