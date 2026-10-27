"""L18 steps 1 and 2 without a database (C2 1.2.0, PHASE-3.md M3.4): the record checks and the
bridge check refuse a doctored overlay with exit 2, and the real-data instance refuses a profile
outside `access.real_overlay_profiles` with exit 3, before anything connects."""

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from neonradar_graph import cypher, overlay
from neonradar_graph.instances import Instance, InstanceRefused
from neonradar_graph.loader import LoadReport
from neonradar_ingest.synth import base

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
    "a second holder of a base holder's account": lambda rs, _: rs.append(
        record(
            "syn-ov-own-3",
            "Ownership",
            owner="syn-ov-co-1",
            asset="syn-ov-acct-1",
            role="account holder",
        )
    ),
    "a base holding with a second owner": lambda rs, _: props(rs, "syn-ov-own-1").update(
        owner=[BASE, "syn-ov-co-1"]
    ),
    "a base holding of two base companies": lambda rs, _: props(rs, "syn-ov-own-1").update(
        owner=[BASE, OTHER]
    ),
    "a payment on a base holder's account names a synthetic payer": lambda rs, _: props(
        rs, "syn-ov-pay-1"
    ).update(payer=["syn-ov-co-1"]),
    "overlay.json names another profile": lambda _, meta: meta.update(profile="synth-eval"),
}


def test_a_sound_overlay_plans_its_rows_and_names_its_base_references() -> None:
    plan, refs = overlay.plan_overlay(sound(), {"profile": "synth-demo"}, "synth-demo")
    assert refs == [BASE]
    holding = next(row for row in plan.relationships if row.id == "syn-ov-own-1")
    assert (holding.type, holding.source, holding.resolving) == ("HOLDS_ACCOUNT", BASE, True)
    assert {row.id for row in plan.nodes} == {"syn-ov-acct-1", "syn-ov-acct-2", "syn-ov-co-1"}


class NoDriver:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError("connected before L18 steps 1 and 2 passed")


NO_DRIVER: Any = NoDriver()


def write(folder: Path, records: Records, meta: dict[str, Any]) -> Path:
    folder.mkdir()
    lines = "".join(json.dumps(item) + "\n" for item in records)
    (folder / "overlay.ftm.jsonl").write_text(lines, encoding="utf-8")
    (folder / "overlay.json").write_text(json.dumps(meta), encoding="utf-8")
    return folder


@pytest.mark.parametrize("change", sorted(CHANGES))
def test_a_doctored_overlay_stops_before_connecting(change: str, tmp_path: Path) -> None:
    records, meta = sound(), {"profile": "synth-demo"}
    CHANGES[change](records, meta)
    folder = write(tmp_path / "overlay", records, meta)
    with pytest.raises(overlay.OverlayRefused) as refused:
        overlay.load_overlay(folder, "synth-demo", Instance.DEFAULT, driver=NO_DRIVER, database="x")
    assert refused.value.exit_code == 2
    assert "syn-co-" not in str(refused.value)  # counts only: a base id could be real


def test_the_real_data_instance_takes_only_a_listed_profile_s_overlay(tmp_path: Path) -> None:
    with pytest.raises(overlay.OverlayInstanceRefused) as refused:  # the folder is never read
        overlay.load_overlay(tmp_path / "missing", "uk-tiny", Instance.REAL, ["uk-sample"])
    assert refused.value.exit_code == 3


def test_a_profile_list_given_as_one_string_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TypeError):  # "uk" in "uk-tiny" would be a substring test
        overlay.load_overlay(tmp_path, "uk", Instance.REAL, "uk-tiny")


@pytest.mark.parametrize(
    ("protected", "instance"),
    [("Real", Instance.DEFAULT), ("spikes", Instance.DEFAULT), ("holdout", Instance.REAL)],
)
def test_an_overlay_in_a_protected_folder_is_never_read(
    protected: str, instance: Instance, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inside = tmp_path / "data" / "cache" / protected / "overlay"
    inside.mkdir(parents=True)
    linked = tmp_path / "copy"
    linked.mkdir()
    (linked / "overlay.json").symlink_to(inside / "overlay.json")  # a file that resolves inside
    listed: list[Path] = []
    iterdir = Path.iterdir

    def listing(path: Path) -> Iterator[Path]:
        listed.append(path)
        return iterdir(path)

    monkeypatch.setattr(Path, "iterdir", listing)
    for folder in (inside, linked):
        with pytest.raises(overlay.OverlayInstanceRefused) as refused:
            overlay.load_overlay(folder, "uk-tiny", instance, ["uk-tiny"], driver=NO_DRIVER)
        assert refused.value.exit_code == 3
    assert listed == [linked]  # a protected folder's names are never listed


def test_another_profile_s_overlay_is_refused_before_its_records_are_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = write(tmp_path / "overlay", sound(), {"profile": "uk-tiny"})
    monkeypatch.setattr(overlay, "read_input", lambda *_: pytest.fail("the records were read"))
    with pytest.raises(overlay.OverlayRefused, match="does not name the profile synth-demo"):
        overlay.load_overlay(folder, "synth-demo", Instance.DEFAULT, driver=NO_DRIVER, database="x")


def test_the_row_check_runs_before_the_previous_overlay_is_purged() -> None:
    plan, refs = overlay.plan_overlay(sound(), {"profile": "synth-demo"}, "synth-demo")
    plan.nodes[0].props["synthetic"] = False  # a row L17 refuses on either instance
    with pytest.raises(InstanceRefused, match="nothing was written"):
        overlay._execute(NO_DRIVER, plan, refs, LoadReport(True), "neo4j", 10)


def test_the_holders_check_takes_the_generator_s_status_allowlist() -> None:
    """overlay_holders.cypher refuses a status outside 7.2.4's allowlist (OD-10, L18a)."""
    assert set(overlay.LIVE) == base.LIVE
    assert "$live" in cypher.query("overlay_holders.cypher")
