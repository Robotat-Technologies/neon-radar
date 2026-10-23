from datetime import UTC, datetime

from kit import Kit, detect, source_of
from neonradar_detect.detectors import structuring as st
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _branches(k: Kit, n: int = 3) -> list[str]:
    bank = k.company("bank", "Fixture Bank plc")
    return [k.account(f"branch{i}", bank, kind="cash_ledger") for i in range(n)]


def _run(k: Kit, **overrides):
    return st.run(source_of(k.records), st.Params(**overrides), WINDOW).findings


def test_burst_below_threshold_across_branches():
    k = Kit()
    b = _branches(k)
    acct = k.account("s1", k.company("s1"))
    e = [
        k.pay(b[0], acct, 9500, "2026-03-02T10:00", channel="cash_deposit"),
        k.pay(b[1], acct, 9700, "2026-03-02T15:00", channel="cash_deposit"),
        k.pay(b[2], acct, 9300, "2026-03-03T11:00", channel="cash_deposit"),
        k.pay(b[0], acct, 9800, "2026-03-04T09:30", channel="cash_deposit"),
    ]
    [f] = _run(k)
    assert f.edge_ids == tuple(sorted(e))
    assert f.metrics["deposits"] == 4 and f.metrics["total_amount"] == 38300.0
    assert (
        f.metrics["branches"] == 3
        and f.metrics["days"] == 3
        and f.metrics["max_day_total"] == 19200.0
    )
    assert f.variant == "single_account" and len(f.steps) == 3


def test_two_accounts_of_one_holder():
    k = Kit()
    b = _branches(k, 2)
    holder = k.company("s2")
    a1, a2 = k.account("s2a", holder), k.account("s2b", holder)
    k.pay(b[0], a1, 9400, "2026-04-06T10:00", channel="cash_deposit")
    k.pay(b[1], a2, 9600, "2026-04-06T12:00", channel="cash_deposit")
    k.pay(b[0], a2, 9900, "2026-04-07T10:00", channel="cash_deposit")
    [f] = _run(k)
    assert f.variant == "multi_account" and f.metrics["accounts"] == 2
    assert [s.role for s in f.subjects] == ["holder", "receiving_account", "receiving_account"]


def test_lookalikes_are_not_found():
    k = Kit()
    b = _branches(k, 1)
    shop = k.account("shop", k.company("shop", sector="retail"))
    amounts = [3200, 12500, 9100, 4100, 15000, 2800, 11000, 6400, 9900, 7300, 13800, 5100]
    for day, amount in enumerate(amounts, start=2):
        k.pay(b[0], shop, amount, f"2026-02-{day:02d}T18:00", channel="cash_deposit")
    saver = k.account("saver", k.person("saver"))
    for week in range(8):
        k.pay(
            b[0],
            saver,
            9500,
            f"2026-03-{2 + 7 * week:02d}T12:00"
            if 2 + 7 * week <= 31
            else f"2026-04-{2 + 7 * week - 31:02d}T12:00",
            channel="cash_deposit",
        )
    two = k.account("two", k.company("two"))
    k.pay(b[0], two, 9500, "2026-05-04T10:00", channel="cash_deposit")
    k.pay(b[0], two, 9500, "2026-05-04T14:00", channel="cash_deposit")
    assert _run(k) == []


def test_band_edges():
    k = Kit()
    b = _branches(k, 1)
    acct = k.account("edge", k.company("edge"))
    k.pay(b[0], acct, 9000.00, "2026-06-01T10:00", channel="cash_deposit")  # lower edge: in band
    k.pay(b[0], acct, 9999.99, "2026-06-01T11:00", channel="cash_deposit")
    k.pay(
        b[0], acct, 10000.00, "2026-06-01T12:00", channel="cash_deposit"
    )  # at the threshold: not in band
    assert _run(k) == []  # two in band out of three: below min_deposits
    k.pay(b[0], acct, 9500.00, "2026-06-02T12:00", channel="cash_deposit")
    [f] = _run(k)
    assert f.metrics["deposits"] == 3 and f.metrics["band_share"] == 0.75


def test_a_usd_deposit_of_exactly_the_threshold_is_below_it():
    """31 CFR 1010.311 covers cash "of more than $10,000"; GBP and EUR are modelled on "or more"."""
    k = Kit()
    b = _branches(k, 1)
    usd = k.account("usd", k.company("usd"), currency="USD")
    gbp = k.account("gbp", k.company("gbp"))
    for day in range(3):
        when = f"2026-06-0{2 + day}T10:00"
        k.pay(b[0], usd, 10000, when, channel="cash_deposit", currency="USD")
        k.pay(b[0], gbp, 10000, when, channel="cash_deposit")
    [f] = _run(k)
    assert f.anchor == usd and f.metrics["currency"] == "USD" and f.metrics["deposits"] == 3


def test_headline_through_the_runner():
    k = Kit()
    acct = k.account("dep", k.person("depositor"))
    branch = k.account("branch", k.company("bank"), kind="cash_ledger")
    for d, amount in enumerate((9500, 9800, 9700, 9900)):
        k.pay(branch, acct, amount, f"2026-04-0{1 + d}T11:00", channel="cash_deposit")
    [alert] = detect(k.records, {"structuring": st.Params()}).alerts
    assert alert["headline"] == (
        "Synthetic scenario: 4 cash deposits just below GBP 10,000 within 3 days, "
        "GBP 38,900 in total"
    )
