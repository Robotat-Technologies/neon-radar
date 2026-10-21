"""Synthetic join with real-looking input built here, never committed (PHASE-1.md M1.8e, G1)."""

import json
from pathlib import Path
from typing import Any

from neonradar_contracts.records import iter_records, validate_files
from neonradar_ingest.synth.companies import name_key
from neonradar_ingest.synth.join import synthetic_join, touches_input

DEMO = Path(__file__).resolve().parents[2] / "contracts" / "examples" / "c1" / "demo.ftm.jsonl"


def _rec(rid: str, schema: str, dataset: str, **props: list[str]) -> dict[str, Any]:
    return {"id": rid, "schema": schema, "datasets": [dataset], "properties": props}


def real_input() -> list[dict[str, Any]]:
    """Non-synthetic records of the kinds the spikes write, plus one synthetic company."""
    return [
        _rec("gbch-co-T0000001", "Company", "gb_companies_house", name=["Test Holder Ltd"],
             jurisdiction=["gb"], incorporationDate=["2001-05-04"]),
        _rec("gbch-co-T0000002", "Company", "gb_companies_house", name=["Test Closed Ltd"],
             jurisdiction=["gb"], dissolutionDate=["2020-01-31"]),
        _rec("gbch-off-T0000003", "Person", "gb_companies_house", name=["Test Officer"]),
        _rec("icij-T0000004", "LegalEntity", "icij_offshore_leaks", name=["Test Intermediary"]),
        _rec("gleif-TEST0000000000000005", "Company", "gleif_lei", name=["TEST PARENT AG"],
             jurisdiction=["de"]),
        _rec("gbch-dir-T0000006", "Directorship", "gb_companies_house",
             director=["gbch-off-T0000003"], organization=["gbch-co-T0000001"]),
    ]  # fmt: skip


def _write(path: Path, records: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    return path


def test_real_entities_get_background_activity_only(tmp_path: Path) -> None:
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
    assert set(holders) == {"gbch-co-T0000001", "gleif-TEST0000000000000005"}  # no person,
    # no bare legal entity, no dissolved company
    held = set(holders.values())
    payments = [r["properties"] for r in result.records if r["schema"] == "Payment"]
    senders = {p["payerAccount"][0] for p in payments}
    receivers = {p["beneficiaryAccount"][0] for p in payments}
    for p in payments:  # every real-held account deals only with one-way synthetic accounts
        source, target = p["payerAccount"][0], p["beneficiaryAccount"][0]
        if target in held:
            assert source not in receivers and p["payer"][0].startswith("syn-")
        if source in held:
            assert target not in senders and p["beneficiary"][0].startswith("syn-")
    for sc in result.scenarios:
        assert all(rid.startswith("syn-") and rid not in held for _, rid in sc.participants)
    for r in result.records:  # real ids only as account holder, payer or beneficiary
        for prop, values in r["properties"].items():
            if set(values) & real:
                assert (r["schema"], prop) in {
                    ("Ownership", "owner"), ("Payment", "payer"), ("Payment", "beneficiary")
                }  # fmt: skip
    output = _write(tmp_path / "out.ftm.jsonl", result.records)
    _, issues = validate_files([_write(tmp_path / "in.ftm.jsonl", inputs), output], strict=True)
    assert issues == []


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


def test_ids_and_account_numbers_never_collide_with_synthetic_input() -> None:
    inputs = list(iter_records(DEMO))
    result = synthetic_join(inputs, seed=7)
    assert not {r["id"] for r in inputs} & {r["id"] for r in result.records}
    used = {n for r in inputs for n in r["properties"].get("accountNumber", [])}
    new = {n for r in result.records for n in r["properties"].get("accountNumber", [])}
    assert not used & new and min(new) > max(used)


def test_same_input_and_seed_give_the_same_records() -> None:
    def run(seed: int) -> list[str]:
        return [
            json.dumps(r, ensure_ascii=False) for r in synthetic_join(real_input(), seed).records
        ]

    assert run(7) == run(7)
    assert run(7) != run(8)
