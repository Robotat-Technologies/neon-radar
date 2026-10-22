"""The scenario and bridge guards (G1; M3.3 review S1 and S2). Test look-alike ids only."""

from datetime import UTC, date, datetime

import pytest
from names_simple import SimpleNames

from neonradar_ingest.synth import overlay
from neonradar_ingest.synth.ctx import Ctx, ScenarioCtx, name_key
from neonradar_ingest.synth.dates import Period

BASE_ORG = "gbch-co-T0000501"
PERIOD = Period(datetime(2025, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def background() -> tuple[Ctx, str, str]:
    ctx = Ctx(5, PERIOD, SimpleNames(), base_ids={BASE_ORG})
    account = ctx.account("bg|base", BASE_ORG, opened=date(2020, 1, 1))
    other = ctx.account(
        "bg|cp", ctx.organization("cp", "Test Counterparty Ltd"), opened=date(2020, 1, 1)
    )
    payment = ctx.pay("bg|1", other, account, 120.0, datetime(2025, 3, 3, 10, tzinfo=UTC))
    return ctx, account, payment


def test_a_scenario_cannot_label_background_records() -> None:
    ctx, account, payment = background()
    holding = next(
        r["id"] for r in ctx.records.values()
        if r["schema"] == "Ownership" and r["properties"]["asset"] == [account]
    )  # fmt: skip
    s = ScenarioCtx(ctx, "scn-000001", "rapid_pass_through", lookalike=False)
    with pytest.raises(PermissionError):
        s.label_payment(payment, "layer")
    with pytest.raises(PermissionError):
        s.label(holding, "holder")
    mine = s.account(s.person(), opened=date(2020, 1, 1))
    theirs = s.account(s.person(), opened=date(2020, 1, 1))
    own = s.pay(mine, theirs, 50.0, datetime(2025, 4, 1, 10, tzinfo=UTC))
    assert s.label_payment(own, "layer") == own  # its own payment it may label


def test_the_bridge_needs_an_eligible_holder_and_never_a_base_account() -> None:
    ctx, _, payment = background()
    records = [*ctx.records.values(), ctx.record(payment)]
    overlay.check_bridge(records, {BASE_ORG}, ctx.base_accounts, {BASE_ORG})
    with pytest.raises(ValueError, match="I15"):
        overlay.check_bridge(records, {BASE_ORG}, ctx.base_accounts, set())  # not eligible
    pay = ctx.record(payment)
    named = {**pay, "properties": {**pay["properties"], "beneficiaryAccount": [BASE_ORG]}}
    with pytest.raises(ValueError, match="base record as an account"):
        overlay.check_bridge([named], {BASE_ORG}, ctx.base_accounts, {BASE_ORG})


def test_names_that_differ_only_by_legal_form_collide() -> None:
    """N3: "X Ltd" and "X LIMITED" are one name; a new name never repeats a base name."""
    assert name_key("Sorrel Tarn Freight Ltd") == name_key("SORREL TARN FREIGHT LIMITED")
    ctx = Ctx(5, PERIOD, SimpleNames(), base_names={"Sorrel Tarn Freight LIMITED"})
    draws = iter(["Sorrel Tarn Freight Ltd", "Teasel Wold Freight Ltd"])
    assert ctx._unique(lambda: next(draws)) == "Teasel Wold Freight Ltd"
