from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import rapid_pass_through as rp
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    if not any(r["id"] == "syn-fx-acct-hist-a" for r in k.records):
        k.history()  # data from 2025-10-01: the 90-day history before the window is known
    return rp.run(source_of(k.records), rp.Params(**overrides), WINDOW).findings


def _senders(k: Kit, tag: str, n: int) -> list[str]:
    return [k.account(f"{tag}s{i}", k.person(f"{tag}s{i}")) for i in range(n)]


def test_funnel_found_and_slow_dwell_not():
    k = Kit()
    hub = k.account("hub", k.company("hub"))
    out = k.account("dest", k.company("dest", jurisdiction="ae"))
    ins = [
        k.pay(s, hub, 6000, f"2026-03-0{2 + i % 2}T1{i}:00")
        for i, s in enumerate(_senders(k, "a", 4))
    ]
    o = k.pay(hub, out, 23500, "2026-03-04T09:00")
    [f] = _run(k)
    assert f.edge_ids == tuple(sorted([*ins, o]))
    assert (
        f.metrics["pass_ratio"] == 0.9792
        and f.metrics["sources"] == 4
        and f.metrics["beneficiaries"] == 1
    )
    slow = Kit()
    hub2 = slow.account("hub", slow.company("hub"))
    out2 = slow.account("dest", slow.company("dest"))
    for i, s in enumerate(_senders(slow, "b", 4)):
        slow.pay(s, hub2, 6000, f"2026-03-02T1{i}:00")
    slow.pay(hub2, out2, 23500, "2026-03-09T09:00")
    assert _run(slow) == []


def test_lookalikes():
    k = Kit()
    bureau = k.account("bureau", k.company("bureau"))
    client = k.account("client", k.company("client"))
    k.pay(client, bureau, 30000, "2026-04-01T09:00")
    for i in range(20):
        k.pay(bureau, k.account(f"emp{i}", k.person(f"emp{i}")), 1450, "2026-04-01T15:00")
    escrow = k.account("escrow", k.company("escrow"))
    for i, s in enumerate(_senders(k, "e", 3)):
        k.pay(s, escrow, 10000, f"2026-04-0{i + 1}T10:00")
    k.pay(escrow, k.account("seller", k.company("seller")), 29900, "2026-05-15T10:00")
    assert _run(k) == []
    # a marketplace settlement account has the same shape and is found (documented false positive)
    market = k.account("market", k.company("market"))
    merchant = k.account("merchant", k.company("merchant"))
    for i, s in enumerate(_senders(k, "m", 10)):
        k.pay(s, market, 3000, f"2026-06-0{1 + i % 3}T1{i % 9}:00")
    k.pay(market, merchant, 29000, "2026-06-04T08:00")
    [f] = _run(k)
    assert f.anchor == market


def test_two_bursts_give_two_findings():
    k = Kit()
    hub = k.account("hub", k.company("hub"))
    dest = k.account("dest", k.company("dest"))
    senders = _senders(k, "t", 3)
    for day in (2, 20):
        for i, s in enumerate(senders):
            k.pay(s, hub, 8000, f"2026-02-{day:02d}T1{i}:00")
        k.pay(hub, dest, 23900, f"2026-02-{day + 1:02d}T10:00")
    found = _run(k)
    assert len(found) == 2 and found[0].window[0] < found[1].window[0]
