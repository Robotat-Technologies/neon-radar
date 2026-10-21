import json
from datetime import UTC, date, datetime

import pytest
from names_simple import SimpleNames
from neonradar_ingest.synth import labels, overlay, world, writer
from neonradar_ingest.synth.ctx import Ctx, ScenarioCtx
from neonradar_ingest.synth.dates import Period
from neonradar_ingest.synth.namesource import default_names
from neonradar_ingest.synth.streams import stream

SMALL = world.WorldConfig(companies=60, people=90, agent_every=30, professional_every=30)
KINDS = {"nr_synthetic": "synthetic"}
NAME_KEYS = ("name", "full", "street", "city", "gender")  # what a name source decides


def _overlay(seed: int, names=None, **kw):
    names = names or default_names()
    base = world.generate(seed, SMALL, names)
    cfg = overlay.OverlayConfig(
        seed, illicit=kw.pop("illicit", 2), lookalikes=kw.pop("lookalikes", 2), **kw
    )
    return base, overlay.generate(base, KINDS, cfg, names)


def test_streams_depend_only_on_their_keys():
    a = stream(7, "background", "x").integers(0, 10**9, size=3).tolist()
    stream(7, "other").integers(0, 10**9, size=100)
    assert stream(7, "background", "x").integers(0, 10**9, size=3).tolist() == a
    assert stream(8, "background", "x").integers(0, 10**9, size=3).tolist() != a
    with pytest.raises(ValueError):
        stream(-1, "x")


def test_same_seed_same_bytes():
    _, a = _overlay(11)
    _, b = _overlay(11)
    assert writer.record_lines(a.records) == writer.record_lines(b.records)
    la = labels.files(a.labels, seed=11, record_sha256={}, generator_version="1.0.0")
    lb = labels.files(b.labels, seed=11, record_sha256={}, generator_version="1.0.0")
    assert la == lb
    assert la["scenarios.csv"].startswith(
        "# synthetic: true\n# label_schema: 2.0.0\nscenario_id,typology,variant,"
    )


def _strip_names(records):
    out = []
    for r in records:
        props = {k: v for k, v in r["properties"].items() if k not in NAME_KEYS}
        out.append({**r, "properties": props})
    return out


def test_names_never_move_a_structural_draw():
    base_a, a = _overlay(12)
    base_b, b = _overlay(12, SimpleNames())
    assert _strip_names(base_a) == _strip_names(base_b)
    assert _strip_names(a.records) == _strip_names(b.records)
    assert (
        a.labels.transactions == b.labels.transactions
        and a.labels.participants == b.labels.participants
    )


def test_bridge_rules_and_no_labels_in_records():
    base, ov = _overlay(13)
    base_ids = {r["id"] for r in base}
    records = ov.records
    for r in records:
        assert (
            r["id"].startswith("syn-ov-")
            and r["datasets"] == ["nr_synthetic"]
            and r["nr"]["synthetic"] is True
        )
        text = json.dumps(r).casefold()
        assert not any(
            word in text for word in ("scenario", "typology", "illicit", "lookalike", "scn-")
        )
    holdings = [
        r for r in records if r["schema"] == "Ownership" and r["properties"]["owner"][0] in base_ids
    ]
    assert holdings and all(r["properties"]["role"] == ["account holder"] for r in holdings)
    payments = [r for r in records if r["schema"] == "Payment"]
    base_held = {r["properties"]["asset"][0] for r in holdings}
    assert not any(
        r["properties"]["payerAccount"][0] in base_held
        and r["properties"]["beneficiaryAccount"][0] in base_held
        for r in payments
    )
    doctored = {r["id"]: r for r in records}
    rogue = dict(next(r for r in records if r["schema"] == "Directorship"))
    rogue = {
        **rogue,
        "id": "syn-ov-dir-rogue",
        "properties": {**rogue["properties"], "organization": [sorted(base_ids)[0]]},
    }
    doctored[rogue["id"]] = rogue
    with pytest.raises(ValueError, match="I15"):
        overlay.check_bridge(doctored.values(), base_ids, set())
    base_address = next(r["id"] for r in base if r["schema"] == "Address")
    company = next(r for r in records if r["schema"] == "Company")
    moved = {**company, "properties": {**company["properties"], "addressEntity": [base_address]}}
    with pytest.raises(ValueError, match="I15"):
        overlay.check_bridge([moved], base_ids, set())
    pay = next(r for r in payments if r["properties"]["payerAccount"][0] not in base_held)
    named = {**pay, "properties": {**pay["properties"], "payer": [sorted(base_ids)[0]]}}
    with pytest.raises(ValueError, match="names a base entity"):
        overlay.check_bridge([named], base_ids, base_held)


def test_scenarios_never_reach_base_entities():
    period = Period(datetime(2025, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))
    ctx = Ctx(5, period, default_names(), base_ids={"syn-w-co-000001"})
    s = ScenarioCtx(ctx, "scn-000001", "shell_chain", lookalike=False)
    mine = s.company(incorporated=date(2020, 1, 1))
    with pytest.raises(PermissionError):
        s.owns("syn-w-co-000001", mine, band="75-100")
    with pytest.raises(PermissionError):
        s.label("syn-w-co-000001", "layer")


def test_every_scenario_fits_its_period_and_labels_something():
    for seed in (1, 2, 3):
        _, ov = _overlay(seed, illicit=3, lookalikes=3)
        by = {}
        for row in ov.labels.scenarios:
            by.setdefault(row["typology"], []).append(row)
        assert set(by) == set(overlay.SCENARIOS)
        parts = {row["scenario_id"] for row in ov.labels.participants}
        assert {row["scenario_id"] for row in ov.labels.scenarios} == parts
        assert {row["tx_id"] for row in ov.labels.transactions} <= set(ov.payments)


def test_a_merged_entity_with_a_list_record_gets_no_account(tmp_path):
    """With the base's resolution run, a company merged with a list record is not eligible, and a
    merged pair of registry records gets one account, through its anchor (`BaseView`)."""
    from neonradar_ingest.synth.base import BaseView

    def company(rid: str, dataset: str) -> dict:
        props = {"name": [f"Test Company {rid[-3:]}"], "jurisdiction": ["gb"]}
        return {"id": rid, "schema": "Company", "datasets": [dataset], "properties": props}

    records = [
        company("gbch-co-T0000101", "gb_companies_house"),
        company("uksl-gT0000101", "gb_fcdo_sanctions"),
        company("gbch-co-T0000102", "gb_companies_house"),
        company("gleif-T0000102", "gleif_golden_copy"),
    ]
    kinds = {
        "gb_companies_house": "registry",
        "gleif_golden_copy": "registry",
        "gb_fcdo_sanctions": "list",
    }
    canonical = tmp_path / "canonical.csv"
    canonical.write_text(
        "record_id,canonical_id,class,cluster_size,method,rule,match_probability,via,"
        "path_methods,features\n"
        "gbch-co-T0000101,nr-gbch-co-T0000101,org,2,anchor,,1.0,,,\n"
        "uksl-gT0000101,nr-gbch-co-T0000101,org,2,deterministic,,1.0,,,\n"
        "gbch-co-T0000102,nr-gbch-co-T0000102,org,2,anchor,,1.0,,,\n"
        "gleif-T0000102,nr-gbch-co-T0000102,org,2,deterministic,,1.0,,,\n",
        encoding="utf-8",
    )
    view = BaseView.from_records(records, kinds, canonical)
    assert [o.id for o in view.eligible] == ["gbch-co-T0000102"]
    assert view.skipped == {"list_or_leak_record": 1}
    unresolved = BaseView.from_records(records, kinds)
    assert len(unresolved.eligible) == 3  # without the run, each record stands alone
