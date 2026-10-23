"""R-REAL rule (a) for the M3.5a payment detectors (G12): a cash burst into a real company's
synthetic account, and a funnel through one, are found, then withheld and counted, never emitted;
so are both when the real company is only a second holder of the account (both detectors then
make it a subject), and when it holds only a counterparty's account in the evidence (the bank of
the branch ledgers, the funnel's beneficiary): no subject, so only the holders of evidence
accounts in `policy.involved_ids` withhold that case. The general policy tests in
test_alert_builder.py use circular_flow only. The real look-alike is built at run time (kit
`real=True`); every other record is synthetic."""

from collections.abc import Callable
from typing import Any

import pytest
from kit import Kit, detect

from neonradar_detect.detectors import rapid_pass_through, structuring

WITHHELD = {
    "activity_on_real": 1,
    "real_person_subject": 0,
    "real_person_evidence": 0,
    "registry_on_real": 0,
}


def _company(k: Kit, tag: str, real: bool) -> str:
    """The real look-alike, or a synthetic company."""
    return k.company("gbch-co-T0000002", "Test Holding Ltd", real=True) if real else k.company(tag)


def _account(k: Kit, tag: str, holding: str) -> str:
    """The account the shape centres on: held by the real look-alike ("holder"), by a synthetic
    company with the look-alike as a second holder ("joint"), or by a synthetic company only
    ("counterparty" and "")."""
    acct = k.account(tag, _company(k, tag, holding == "holder"))
    if holding == "joint":
        k.hold(_company(k, tag, True), acct)
    return acct


def _deposits(k: Kit, holding: str) -> None:
    """Four cash deposits just under the GBP threshold at three branches in three days."""
    bank = _company(k, "bank", holding == "counterparty")
    branches = [k.account(f"branch{i}", bank, kind="cash_ledger") for i in range(3)]
    acct = _account(k, "held", holding)
    for i, (amount, day) in enumerate([(9500, 2), (9700, 2), (9300, 3), (9800, 4)]):
        k.pay(branches[i % 3], acct, amount, f"2026-03-0{day}T1{i}:00", channel="cash_deposit")


def _funnel(k: Kit, holding: str) -> None:
    """Four inflows, 98 percent of them passed on to one beneficiary within two days."""
    k.history()
    hub = _account(k, "hub", holding)
    out = k.account("dest", _company(k, "dest", holding == "counterparty"))
    for i in range(4):
        k.pay(k.account(f"s{i}", k.person(f"s{i}")), hub, 6000, f"2026-03-0{2 + i % 2}T1{i}:00")
    k.pay(hub, out, 23500, "2026-03-04T09:00")


CASES = [
    pytest.param("structuring", structuring.Params(), _deposits, id="structuring"),
    pytest.param(
        "rapid_pass_through", rapid_pass_through.Params(), _funnel, id="rapid_pass_through"
    ),
]
Build = Callable[[Kit, str], None]


@pytest.mark.parametrize("holding", ["holder", "joint", "counterparty"])
@pytest.mark.parametrize(("slug", "params", "build"), CASES)
def test_activity_on_a_real_company_is_withheld(
    slug: str, params: Any, build: Build, holding: str
) -> None:
    k = Kit()
    build(k, holding)
    result = detect(k.records, {slug: params})
    assert result.alerts == []
    assert result.summary["withheld"] == WITHHELD
    per = result.summary["typologies"][slug]
    assert per["findings"] == 1 and per["alerts"] == 0


@pytest.mark.parametrize(("slug", "params", "build"), CASES)
def test_the_same_shape_on_synthetic_holders_gives_one_alert(
    slug: str, params: Any, build: Build
) -> None:
    k = Kit()
    build(k, "")
    result = detect(k.records, {slug: params})
    assert len(result.alerts) == 1
    assert result.summary["withheld"]["activity_on_real"] == 0
