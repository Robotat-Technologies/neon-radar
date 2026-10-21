"""demo-mini against PHASE-1.md M1.8e: contract, targets, guardrail G1 and labels (R9)."""

import re
from collections import Counter
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from neonradar_contracts.records import validate_files
from neonradar_ingest.synth.cycles import Hop, find_cycles

if TYPE_CHECKING:
    from conftest import Load


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _holders(demo: Load) -> dict[str, str]:
    """Account id -> holder id, from the account Ownerships."""
    accounts = {r["id"] for r in demo.schema("BankAccount")}
    return {
        r["properties"]["asset"][0]: r["properties"]["owner"][0]
        for r in demo.schema("Ownership")
        if r["properties"]["asset"][0] in accounts
    }


def test_validates_in_strict_mode(demo_mini: Load) -> None:
    counts, issues = validate_files([demo_mini.path], strict=True)
    assert issues == []
    assert counts.total() == len(demo_mini.records)


def test_counts_meet_the_targets(demo_mini: Load) -> None:
    counts = Counter(r["schema"] for r in demo_mini.records)
    assert (counts["Company"], counts["Person"], counts["Address"]) == (24, 30, 12)
    assert counts["Organization"] == 2  # the two bank branches
    kinds = Counter(r["nr"]["account_kind"] for r in demo_mini.schema("BankAccount"))
    assert kinds == {"customer": 40, "cash_ledger": 2}
    assert 230 <= counts["Payment"] <= 260
    assert 420 <= sum(counts.values()) <= 480
    places = Counter(demo_mini.prop(r["id"], "jurisdiction") for r in demo_mini.schema("Company"))
    assert places == {"gb": 18, "vg": 2, "cy": 2, "ae": 2}
    scripts = [len(r["properties"]["name"]) for r in demo_mini.schema("Person")]
    assert sum(n >= 2 for n in scripts) == 10 and sum(n == 3 for n in scripts) >= 3


def test_registry_has_the_planned_structures(demo_mini: Load) -> None:
    companies = demo_mini.schema("Company")
    shared = Counter(r["properties"]["addressEntity"][0] for r in companies)
    assert sorted(shared.values())[-2:] == [2, 8]  # one address holds 8 companies
    agents = Counter(r["properties"]["agent"][0] for r in demo_mini.schema("Representation"))
    assert list(agents.values()) == [6]
    nominees = [r for r in demo_mini.schema("Directorship") if r["nr"].get("is_nominee")]
    assert len(nominees) == 4 and len({r["properties"]["director"][0] for r in nominees}) == 1
    topics = Counter(t for r in demo_mini.records for t in r["properties"].get("topics", []))
    assert topics == {"role.pep": 1, "sanction": 1}
    pep = next(r["id"] for r in demo_mini.schema("Person") if r["properties"].get("topics"))
    shares = [r for r in demo_mini.schema("Ownership") if "percentage" in r["properties"]]
    assets: dict[str, list[str]] = {}
    for r in shares:
        assets.setdefault(r["properties"]["owner"][0], []).append(r["properties"]["asset"][0])
    chains = [(a, b, c) for a in assets[pep] for b in assets.get(a, []) for c in assets.get(b, [])]
    assert len(chains) == 1  # the PEP -> company -> company -> company
    ledgers = [r["id"] for r in demo_mini.schema("BankAccount")
               if r["nr"]["account_kind"] == "cash_ledger"]  # fmt: skip
    holders = _holders(demo_mini)
    assert {demo_mini.by_id[holders[a]]["schema"] for a in ledgers} == {"Organization"}


def test_payments_are_weekday_office_hours_in_the_account_currency(demo_mini: Load) -> None:
    for pay in demo_mini.schema("Payment"):
        props = pay["properties"]
        when = _ts(props["date"][0])
        assert when.weekday() < 5 and 8 <= when.hour < 18, pay["id"]
        for account in (props["payerAccount"][0], props["beneficiaryAccount"][0]):
            assert demo_mini.prop(account, "currency") == props["currency"][0]
        if pay["nr"]["channel"] == "cash_deposit":
            assert demo_mini.by_id[props["payerAccount"][0]]["nr"]["account_kind"] == "cash_ledger"
    dates = [demo_mini.prop(p["id"], "date") for p in demo_mini.schema("Payment")]
    assert dates == sorted(dates)  # ids follow time, so planted payments are spread out


def test_records_carry_no_labels(demo_mini: Load) -> None:
    text = demo_mini.path.read_text(encoding="utf-8")
    words = r"scenario|typolog|illicit|lookalike|look-alike|round.?trip|circular|scn-|label"
    assert not re.search(words, text, re.IGNORECASE)


def test_label_files(demo_mini: Load) -> None:
    payments = {p["id"] for p in demo_mini.schema("Payment")}
    assert {row["tx_id"] for row in demo_mini.transactions} <= payments
    variants = {row["variant"]: row["is_lookalike"] for row in demo_mini.scenarios}
    assert variants == {"round_trip": "false", "loan_drawdown_repayment": "true", "refund": "true"}
    assert {row["typology"] for row in demo_mini.scenarios} == {"circular_flow"}
    illicit = {row["tx_id"] for row in demo_mini.transactions if row["is_illicit"] == "true"}
    assert len(illicit) == 4


def _steps(demo: Load, scenario_id: str) -> list[dict[str, list[str]]]:
    rows = [r for r in demo.transactions if r["scenario_id"] == scenario_id]
    return [
        demo.by_id[r["tx_id"]]["properties"] for r in sorted(rows, key=lambda r: int(r["step"]))
    ]


def test_the_scenario_touches_only_synthetic_entities(demo_mini: Load) -> None:
    holders = _holders(demo_mini)
    for row in demo_mini.scenarios:
        if row["is_lookalike"] == "true":
            continue
        for props in _steps(demo_mini, row["scenario_id"]):
            accounts = [props["payerAccount"][0], props["beneficiaryAccount"][0]]
            ids = [props["payer"][0], props["beneficiary"][0], *accounts]
            ids += [holders[a] for a in accounts]
            assert all(i.startswith("syn-") for i in ids)
        assert all(p.split(":")[1].startswith("syn-") for p in row["participants"].split(";"))


def test_round_trip_shape(demo_mini: Load) -> None:
    scenario = next(r for r in demo_mini.scenarios if r["variant"] == "round_trip")
    hops = _steps(demo_mini, scenario["scenario_id"])
    accounts = [h["payerAccount"][0] for h in hops]
    assert len(hops) == 4 and len(set(accounts)) == 4
    assert [h["beneficiaryAccount"][0] for h in hops] == [*accounts[1:], accounts[0]]
    assert len({h["currency"][0] for h in hops}) == 1
    times = [_ts(h["date"][0]) for h in hops]
    for before, after, a, b in zip(times, times[1:], hops, hops[1:], strict=False):
        assert timedelta(days=1) <= after.date() - before.date() <= timedelta(days=2)
        assert 0.975 <= float(b["amount"][0]) / float(a["amount"][0]) <= 0.985


def test_every_detectable_cycle_is_labelled(demo_mini: Load) -> None:
    hops = [
        Hop(p["id"], demo_mini.prop(p["id"], "payerAccount"),
            demo_mini.prop(p["id"], "beneficiaryAccount"),
            int(_ts(demo_mini.prop(p["id"], "date") + "+00:00").timestamp()),
            round(float(demo_mini.prop(p["id"], "amount")) * 100))
        for p in demo_mini.schema("Payment")
    ]  # fmt: skip
    labelled = {
        tuple(r["tx_id"] for r in sorted(
            (t for t in demo_mini.transactions if t["scenario_id"] == s["scenario_id"]),
            key=lambda t: int(t["step"])))
        for s in demo_mini.scenarios
    }  # fmt: skip
    assert set(find_cycles(hops)) == labelled


def test_scenario_purposes_also_appear_in_the_background(demo_mini: Load) -> None:
    planted = {row["tx_id"] for row in demo_mini.transactions}
    background = Counter(
        demo_mini.prop(p["id"], "purpose").split(" INV-")[0]
        for p in demo_mini.schema("Payment") if p["id"] not in planted
    )  # fmt: skip
    scenario = next(r for r in demo_mini.scenarios if r["variant"] == "round_trip")
    for props in _steps(demo_mini, scenario["scenario_id"]):
        assert background[props["purpose"][0].split(" INV-")[0]] >= 3
