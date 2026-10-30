from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import dormant_reactivation as dr
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return dr.run(source_of(k.records), dr.Params(**overrides), WINDOW).findings


def _burst(k: Kit, acct: str, day: str, n: int = 6, amount: float = 10000) -> list[str]:
    others = [k.account(f"{acct[-6:]}x{i}", k.company(f"{acct[-6:]}x{i}")) for i in range(n)]
    return [
        k.pay(o, acct, amount, f"{day}T1{i}:00")
        if i % 2 == 0
        else k.pay(acct, o, amount * 0.95, f"{day}T1{i}:30")
        for i, o in enumerate(others)
    ]


def _quiet_account(k: Kit, name: str, opened: str = "2013-01-01") -> tuple[str, str]:
    co = k.company(name, incorporated="2012-05-01")
    acct = k.account(name, co, opened=opened)
    old = k.account(f"{name}-old", k.company(f"{name}-old"))
    k.pay(old, acct, 500, "2025-02-03T10:00")
    k.pay(acct, old, 450, "2025-02-20T10:00")
    return co, acct


def test_long_gap_then_burst_after_new_director():
    k = Kit()
    co, acct = _quiet_account(k, "dorm")
    director = k.person("newdir")
    k.director(director, co, start="2026-02-10")
    e = _burst(k, acct, "2026-03-02")
    [f] = _run(k)
    # the longest quiet period: little activity (one payment of 450) for 392 days
    assert (
        f.variant == "account" and f.metrics["gap_days"] == 392 and f.metrics["quiet_payments"] == 1
    )
    assert f.metrics["change_event"] == "director appointed" and f.metrics["burst_payments"] == 6
    assert (
        f.metrics["burst_threshold"] == 50000.0
    )  # 10 times the pre-gap mean (500 a month) is lower
    assert set(e) <= set(f.edge_ids) and director in f.node_ids
    assert f.pattern_strength == round(0.3 + 0.3 * 58500 / 250000 + 0.2 * 6 / 12 + 0.2, 4)


def test_little_activity_is_allowed_in_the_quiet_period():
    k = Kit()
    _, acct = _quiet_account(k, "small")
    fee = k.account("fee", k.company("fee"))
    k.pay(acct, fee, 12.5, "2025-10-01T09:00")
    k.pay(fee, acct, 400, "2025-12-01T09:00")
    _burst(k, acct, "2026-03-02")
    [f] = _run(k)
    assert f.metrics["quiet_payments"] == 2 and f.metrics["gap_days"] == 375  # from 2025-02-20
    assert _run(k, max_quiet_payments=1) == []  # the second small payment breaks the gap


def test_quiet_period_needs_history_before_it():
    k = Kit()
    k.history("2025-02-03T10:00")
    old = k.account("censored", k.company("censored"), opened="2020-01-01")
    _burst(k, old, "2026-03-02")
    young = k.account("young", k.company("young"), opened="2025-03-01")
    _burst(k, young, "2026-03-03")
    # opened before the first payment in the data: nothing is known about its earlier activity
    assert [(f.anchor, f.metrics["gap_days"]) for f in _run(k)] == [(young, 367)]


def test_seasonal_business_comes_back_at_its_usual_level():
    k = Kit()
    acct = k.account("season", k.company("season", sector="tourism"), opened="2020-01-01")
    guests = [k.account(f"g{i}", k.person(f"g{i}")) for i in range(6)]
    for month in range(4, 10):  # open April to September 2025, then closed until April 2026
        for d, g in enumerate(guests):
            k.pay(g, acct, 4000, f"2025-{month:02d}-{d + 10:02d}T12:00")
        k.pay(acct, guests[0], 9000, f"2025-{month:02d}-28T12:00")
    _burst(k, acct, "2026-04-02")
    assert _run(k) == []  # a 183-day gap, but the burst is below 10 times the monthly mean
    assert len(_run(k, burst_ratio=1.0)) == 1


def test_company_variants():
    k = Kit()
    dormant = k.account(
        "dco", k.company("dco", incorporated="2016-01-01", accounts_category="DORMANT")
    )
    _burst(k, dormant, "2026-02-02")
    fresh = k.account("fresh", k.company("fresh", incorporated="2026-02-15"), opened="2026-02-20")
    funders = [k.account(f"fund{i}", k.company(f"fund{i}")) for i in range(2)]
    for i, f in enumerate(funders):
        k.pay(f, fresh, 40000, f"2026-03-0{3 + i}T10:00")
    for i in range(3):
        k.pay(fresh, k.account(f"away{i}", k.company(f"away{i}")), 25000, f"2026-03-0{5 + i}T12:00")
    trader = k.account(
        "trader", k.company("trader", incorporated="2026-02-15"), opened="2026-02-20"
    )
    _burst(k, trader, "2026-03-03")  # ordinary trading: GBP 30,000 in, 28,500 out
    found = {f.anchor: f.variant for f in _run(k)}
    assert found == {dormant: "dormant_company", fresh: "new_company"}
    # without them nothing is left: both accounts lack history before a quiet period
    assert _run(k, company_variants=False) == []
