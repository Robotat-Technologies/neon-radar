"""Synthetic join with real-looking input built here, never committed (PHASE-1.md M1.8e, G1)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from neonradar_contracts.records import iter_records, validate_files
from neonradar_ingest.synth.companies import name_key
from neonradar_ingest.synth.cycles import Hop, find_cycles
from neonradar_ingest.synth.join import synthetic_join, touches_input

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "contracts" / "examples" / "c1" / "demo.ftm.jsonl"
FIXTURE = ROOT / "data" / "fixtures" / "demo-mini" / "nr_synthetic-20261023-demo-mini.ftm.jsonl"
NOT_LIVE = ["liquidation", "receivership", "administration", "insolvency-proceedings",
            "removed", "struck-off", "defunct", "dead", "deregistered", "bankrupt",
            "inactivated", "dissolved", "closed", "converted-closed"]  # fmt: skip
LIVE_IDS = {"gbch-co-T0000001", "gbch-co-T0000007", "gleif-TEST0000000000000005"}


def _rec(rid: str, schema: str, dataset: str, **props: list[str]) -> dict[str, Any]:
    return {"id": rid, "schema": schema, "datasets": [dataset], "properties": props}


def real_input() -> list[dict[str, Any]]:
    """Non-synthetic records of the kinds the spikes write: three live registry organisations
    and everything that must get nothing."""
    gb = {"jurisdiction": ["gb"], "incorporationDate": ["2001-05-04"]}
    return [
        _rec("gbch-co-T0000001", "Company", "gb_companies_house", name=["Test Holder Ltd"], **gb),
        _rec("gbch-co-T0000007", "Company", "gb_companies_house", name=["Test Second Ltd"],
             status=["active"], **gb),
        _rec("gleif-TEST0000000000000005", "Company", "gleif_lei", name=["TEST PARENT AG"],
             jurisdiction=["de"], status=["ACTIVE"]),
        _rec("gbch-co-T0000002", "Company", "gb_companies_house", name=["Test Closed Ltd"],
             dissolutionDate=["2020-01-31"], **gb),
        *(_rec(f"gbch-co-T00001{i:02d}", "Company", "gb_companies_house",
               name=[f"Test Status {i} Ltd"], status=[s], **gb) for i, s in enumerate(NOT_LIVE)),
        _rec("gbch-co-T0000008", "Company", "gb_companies_house", name=["Test New Ltd"],
             jurisdiction=["gb"], incorporationDate=["2026-01-02"]),
        _rec("gbch-co-T0000009", "PublicBody", "gb_companies_house", name=["Test Council"]),
        _rec("icij-T0000010", "Company", "icij_offshore_leaks", name=["Test Offshore Ltd"]),
        _rec("gbch-off-T0000003", "Person", "gb_companies_house", name=["Test Officer"]),
        _rec("icij-T0000004", "LegalEntity", "icij_offshore_leaks", name=["Test Intermediary"]),
        _rec("gbch-dir-T0000006", "Directorship", "gb_companies_house",
             director=["gbch-off-T0000003"], organization=["gbch-co-T0000001"]),
    ]  # fmt: skip


def _write(path: Path, records: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    return path


def _payments(records: list[dict[str, Any]]) -> list[dict[str, list[str]]]:
    return [{"id": [r["id"]], **r["properties"]} for r in records if r["schema"] == "Payment"]


def test_only_live_registry_organisations_get_background_activity(tmp_path: Path) -> None:
    inputs = real_input()
    real = {r["id"] for r in inputs}
    result = synthetic_join(inputs, seed=7)
    assert all(v == 0 for v in touches_input(result, real).values())
    assert all(r["id"].startswith("syn-") and r["nr"]["synthetic"] for r in result.records)
    holders = {
        r["properties"]["owner"][0]: r["properties"]["asset"][0]
        for r in result.records
        if r["schema"] == "Ownership" and r["properties"]["owner"][0] in real
    }
    assert set(holders) == LIVE_IDS  # never a person, legal entity, public body, ICIJ record,
    # dissolved or not-live company, or one founded after the accounts open
    assert result.counts["skipped: status not live"] == len(NOT_LIVE) + 1
    held = set(holders.values())
    for r in result.records:  # real ids only as account holder, payer or beneficiary
        for prop, values in r["properties"].items():
            if set(values) & real:
                assert (r["schema"], prop) in {
                    ("Ownership", "owner"), ("Payment", "payer"), ("Payment", "beneficiary")
                }  # fmt: skip
    for sc in result.scenarios:
        assert all(rid.startswith("syn-") and rid not in held for _, rid in sc.participants)
    output = _write(tmp_path / "out.ftm.jsonl", result.records)
    _, issues = validate_files([_write(tmp_path / "in.ftm.jsonl", inputs), output], strict=True)
    assert issues == []


def test_the_scenario_is_the_only_detectable_cycle_and_looks_like_background() -> None:
    result = synthetic_join(real_input(), seed=7)
    pays = _payments(result.records)
    hops = [
        Hop(p["id"][0], p["payerAccount"][0], p["beneficiaryAccount"][0],
            int(datetime.fromisoformat(p["date"][0] + "+00:00").timestamp()),
            round(float(p["amount"][0]) * 100))
        for p in pays
    ]  # fmt: skip
    trip = [tx for tx, _, _ in result.scenarios[0].steps]
    assert find_cycles(hops) == [tuple(trip)]
    planted = [p for p in pays if p["id"][0] in trip]
    ring = {p["payerAccount"][0] for p in planted}
    background = [p for p in pays if p["id"][0] not in trip and
                  {p["payerAccount"][0], p["beneficiaryAccount"][0]} & ring]  # fmt: skip
    purposes = {p["purpose"][0].split(" INV-")[0] for p in background}
    assert {p["purpose"][0].split(" INV-")[0] for p in planted} <= purposes
    assert max(float(p["amount"][0]) for p in background) > max(
        float(p["amount"][0]) for p in planted
    )


def test_generated_names_never_equal_an_input_name() -> None:
    first = synthetic_join(real_input(), seed=7)
    names = [r["properties"]["name"][0] for r in first.records if r["schema"] == "Company"]
    inputs = real_input() + [
        _rec(f"gbch-co-T10000{i:02d}", "Company", "gb_companies_house", name=[name.upper()])
        for i, name in enumerate(names)
    ]
    again = synthetic_join(inputs, seed=7)
    keys = {name_key(n) for r in inputs for n in r["properties"].get("name", [])}
    new = [r["properties"]["name"][0] for r in again.records if r["schema"] == "Company"]
    assert len(new) == 12 and not {name_key(n) for n in new} & keys


def _numbers(records: list[dict[str, Any]]) -> set[str]:
    return {n for r in records for n in r["properties"].get("accountNumber", [])}


def test_ids_and_account_numbers_never_collide() -> None:
    inputs = list(iter_records(DEMO))
    result = synthetic_join(inputs, seed=7)
    assert not {r["id"] for r in inputs} & {r["id"] for r in result.records}
    demo_mini = _numbers(list(iter_records(FIXTURE)))
    seven, eight = _numbers(result.records), _numbers(synthetic_join(inputs, seed=8).records)
    assert not (_numbers(inputs) | demo_mini) & (seven | eight) and not seven & eight
    taken = [_rec("syn-acct-9999", "BankAccount", "nr_synthetic", accountNumber=[min(seven)])]
    assert min(seven) not in _numbers(synthetic_join(inputs + taken, seed=7).records)


def test_same_input_and_seed_give_the_same_records() -> None:
    def run(seed: int) -> list[str]:
        return [
            json.dumps(r, ensure_ascii=False) for r in synthetic_join(real_input(), seed).records
        ]

    assert run(7) == run(7)
    assert run(7) != run(8)
