"""The scenario and bridge guards (G1; M3.3 review S1 and S2). Test look-alike ids only."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest
from names_simple import SimpleNames

from neonradar_ingest.synth import overlay, world
from neonradar_ingest.synth.ctx import RELATIONSHIP_SCHEMAS, Ctx, ScenarioCtx, name_key
from neonradar_ingest.synth.dates import Period

BASE_ORG = "gbch-co-T0000501"
PERIOD = Period(datetime(2025, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def background() -> tuple[Ctx, str, str]:
    ctx = Ctx(5, PERIOD, SimpleNames(), base_ids={BASE_ORG})
    account = ctx.account("bg|base", BASE_ORG, opened=date(2020, 1, 1))
    other = ctx.account("bg|cp", ctx.organization("cp", "Test Holder Ltd"), opened=date(2020, 1, 1))
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


def test_a_link_is_never_an_endpoint() -> None:
    """Independent review of #72: a scenario may label the payments and relationships it made
    (`links`), but every endpoint check accepts only `created` or a branch ledger, as the code
    book's `_check` does, so a link id is refused as an account, party, holder or address."""
    s = ScenarioCtx(Ctx(5, PERIOD, SimpleNames()), "scn-000001", "shell_chain", lookalike=False)
    person, company = s.person(), s.company(incorporated=date(2020, 1, 1))
    mine = s.account(person, opened=date(2020, 1, 1))
    theirs = s.account(company, opened=date(2020, 1, 1))
    payment = s.pay(mine, theirs, 50.0, datetime(2025, 4, 1, 10, tzinfo=UTC))
    ownership = s.owns(person, company, band="75-100")
    day, moment = date(2025, 2, 1), datetime(2025, 5, 1, 10, tzinfo=UTC)
    uses: list[Callable[[str], object]] = [
        lambda x: s.pay(x, theirs, 10.0, moment),
        lambda x: s.pay(mine, x, 10.0, moment),
        lambda x: s.owns(x, company, band="25-50"),
        lambda x: s.owns(person, x, band="25-50"),
        lambda x: s.director(x, company, start=day),
        lambda x: s.represents(company, x),
        lambda x: s.family(person, x),
        lambda x: s.control(x, company),
        lambda x: s.associate(x, person),
        lambda x: s.occupancy(person, x, start=day),
        lambda x: s.consolidates(x, company),
        lambda x: s.sanction(x, start=day),
        lambda x: s.company(incorporated=day, address=x),
        lambda x: s.account(x, opened=day),
    ]
    for link in (payment, ownership):
        assert link in s.links and link not in s.created
        for use in uses:
            with pytest.raises(PermissionError, match="may not use"):
                use(link)
    assert s.label_payment(payment, "layer") == payment  # a label may name a link
    assert s.label(ownership, "owner") == ownership


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


def test_owned_payments_and_relationships_move_no_scenario_draw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Independent review of #72: `created` holds what the code book puts there (entities,
    accounts, addresses, positions), and the payments and relationships a scenario owns live
    in `links`, so cash_commingling, which keys a stream on `len(s.created)`, draws the same
    incorporation and opening dates however many it owns. The overlay's incorporation and
    opening dates (302 values, cash_commingling's among them) are pinned by a SHA-256: the
    code book's draw (0da5bed and f5a6c34 give it; 90165a5, which put the links in
    `created`, did not)."""
    made: list[ScenarioCtx] = []

    class Recording(ScenarioCtx):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
            made.append(self)

    monkeypatch.setattr(overlay, "ScenarioCtx", Recording)
    small = world.WorldConfig(companies=40, people=60, agent_every=20, professional_every=20)
    base = world.generate(5, small, SimpleNames())
    config = overlay.OverlayConfig(5, illicit=2, lookalikes=2, typologies=("cash_commingling",))

    def dates() -> dict[str, list[str]]:
        records = overlay.generate(base, {"nr_synthetic": "synthetic"}, config, SimpleNames())
        keep = {"Company": "incorporationDate", "BankAccount": "openingDate"}
        return {
            r["id"]: r["properties"][keep[r["schema"]]]
            for r in records.other_records.values()
            if r["schema"] in keep
        }

    first = dates()
    digest = hashlib.sha256(json.dumps(first, sort_keys=True).encode()).hexdigest()
    assert digest == "e50636f4cbd7bb0db83a699ad6caa900e38ebc5ccbaa1563b2a7ca3ea68c1edf"
    assert len(made) == 4
    for s in made:
        assert s.links and s.links.isdisjoint(s.created)
        for rid in s.created:
            assert rid not in s.ctx.payments
            assert s.ctx.records[rid]["schema"] not in RELATIONSHIP_SCHEMAS
    real_pay = ScenarioCtx.pay

    def padded_pay(self: ScenarioCtx, *args: object, **kwargs: object) -> str:
        rid = real_pay(self, *args, **kwargs)  # type: ignore[arg-type]
        self.links.update(f"pad-{len(self.links)}-{n}" for n in range(3))  # owns many more
        return rid

    monkeypatch.setattr(ScenarioCtx, "pay", padded_pay)
    assert dates() == first
