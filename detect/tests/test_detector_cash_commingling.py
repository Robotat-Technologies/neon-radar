from datetime import UTC, date, datetime, timedelta

from kit import Kit, source_of
from neonradar_detect.detectors import cash_commingling as cc
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 4, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return cc.run(source_of(k.records), cc.Params(**overrides), WINDOW).findings


def _restaurant(
    k: Kit,
    name: str,
    postcode: str,
    weekly: float,
    *,
    sunday: bool = False,
    sector: str = "restaurant",
):
    branch = "syn-fx-acct-branch"
    addr = k.address_at(f"{name}-addr", f"1 {name} Road, {postcode}", postcode)
    co = k.company(name, sector=sector, address=addr)
    acct = k.account(name, co)
    day = date(2026, 1, 5)  # a Monday
    while day < date(2026, 4, 1):
        when = day + timedelta(days=6 if sunday else 1)
        if when < date(2026, 4, 1):
            k.pay(branch, acct, weekly, f"{when.isoformat()}T16:00", channel="cash_deposit")
        day += timedelta(days=7)
    return co, acct


def _town(k: Kit) -> None:
    k.account("branch", k.company("bank"), kind="cash_ledger")
    k.history("2025-01-02T10:00")
    for i, weekly in enumerate((900, 1000, 1100, 950, 1050)):
        _restaurant(k, f"peer{i}", "QQ1 2AB", weekly)


def test_front_business_against_its_peers():
    k = Kit()
    _town(k)
    front, acct = _restaurant(k, "front", "QQ1 9ZZ", 5000, sunday=True)
    owner = k.person("owner")
    k.owns(owner, front)
    own_acct = k.account("owner", owner)
    for m in (1, 2, 3):
        k.pay(acct, own_acct, 15000, f"2026-0{m}-27T12:00")
    k.pay(acct, k.account("supplier", k.company("supplier")), 5000, "2026-02-10T12:00")
    [f] = _run(k)
    assert f.anchor == acct and [s.role for s in f.subjects] == ["business", "receiving_account"]
    m = f.metrics
    ratio = 12 * 5000 / (13 * 1000)  # twelve Sundays against the peers' median of thirteen Tuesdays
    assert (m["peers"], m["peer_ratio"], m["area"], m["sector"]) == (
        5,
        round(ratio, 2),
        "QQ1",
        "restaurant",
    )
    assert (m["related_party_share"], m["sunday_share"], m["change_ratio"]) == (0.9, 1.0, -1)
    assert f.pattern_strength == round(0.4 * ratio / 6 + 0.25 + 0.15, 4)
    assert len(f.steps) == 2 and len(f.steps[1]) == 3


def test_peers_must_share_sector_and_area():
    k = Kit()
    _town(k)
    _restaurant(k, "far", "QQ7 1AA", 5000)  # another district: no peers there
    _restaurant(k, "shop", "QQ1 3CD", 5000, sector="retail")  # another sector
    assert _run(k) == []
    _restaurant(k, "busy", "QQ1 4EF", 2500)  # 2.5 times the median
    assert _run(k) == []
    assert len(_run(k, min_ratio=2.5)) == 1
