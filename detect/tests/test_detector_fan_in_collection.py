from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import fan_in_collection as fi
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return fi.run(source_of(k.records), fi.Params(**overrides), WINDOW).findings


def test_collector_opened_recently_pays_on():
    k = Kit()
    k.history()
    coll = k.account("coll", k.person("coll"), opened="2026-02-15")
    out = k.account("out", k.company("out", jurisdiction="hk"))
    ins = []
    for i in range(10):
        s = k.account(
            f"m{i}", k.person(f"m{i}"), opened="2012-05-01"
        )  # senders: often victims, old accounts
        ins.append(k.pay(s, coll, 800, f"2026-03-0{1 + i % 3}T1{i}:00"))
    o = k.pay(coll, out, 7500, "2026-03-05T10:00")
    [f] = _run(k, ring=False)
    assert f.variant == "collector" and f.edge_ids == tuple(sorted([*ins, o]))
    assert f.metrics["senders"] == 10 and f.metrics["collector_account_days"] == 14
    assert f.metrics["onward_ratio"] == 0.9375 and f.metrics["prior_share"] == 0.0
    assert (
        f.pattern_strength == 0.8344
    )  # 0.3 * 10/20 + 0.25 * (1 - 0) + 0.25 * 0.9375 + 0.2 (new collector)
    late = Kit()
    late.history()
    c2 = late.account("c2", late.person("c2"))
    for i in range(10):
        late.pay(late.account(f"n{i}", late.person(f"n{i}")), c2, 800, f"2026-03-02T1{i}:00")
    late.pay(c2, late.account("o2", late.company("o2")), 7500, "2026-03-10T10:00")  # after 72 hours
    assert _run(late, ring=False) == []


def test_charity_and_landlord_lookalikes():
    k = Kit()
    charity = k.account("charity", k.company("charity", sector="charity"))
    for i in range(40):
        s = k.account(f"d{i}", k.person(f"d{i}"), opened="2018-01-01")
        k.pay(s, charity, 200, f"2026-04-0{1 + i % 5}T1{i % 9}:00")
    landlord_acct = k.account("landlord", k.person("landlord"))
    bank = k.account("mortgage", k.company("lender"))
    for i in range(10):
        t = k.account(f"t{i}", k.person(f"t{i}"), opened="2019-01-01")
        for month in ("2025-12", "2026-01", "2026-02"):
            k.pay(t, landlord_acct, 900, f"{month}-01T0{i % 9}:00")
    for month in ("2026-01", "2026-02"):
        k.pay(landlord_acct, bank, 8000, f"{month}-03T09:00")
    assert _run(k) == []


def test_ring_of_new_accounts():
    k = Kit()
    sink = k.account("sink", k.person("sink"), opened="2026-02-25")
    cash = k.account("cash", k.person("cash"), opened="2026-02-26")
    edges, fed = [], []
    for i in range(4):
        mule = k.account(f"r{i}", k.person(f"r{i}"), opened=f"2026-02-2{i}")
        for v in range(2):
            victim = k.account(f"v{i}{v}", k.person(f"v{i}{v}"), opened="2015-05-05")
            fed.append(k.pay(victim, mule, 1500, f"2026-03-0{2 + v}T10:00"))
        edges.append(k.pay(mule, sink, 2900, f"2026-03-04T1{i}:00"))
    edges.append(k.pay(sink, cash, 11000, "2026-03-05T09:00"))
    found = _run(k)
    [ring] = [f for f in found if f.variant == "ring"]
    # the ring's own payments, and the payments from old accounts that fed it
    assert ring.anchor == sink and ring.edge_ids == tuple(sorted(edges + fed))
    assert (
        ring.metrics["ring_accounts"] == 6
        and ring.metrics["hubs"] == 1
        and ring.metrics["fed_payments"] == 8
    )
    assert ring.metrics["feeding_share"] == 0.6667
    assert _run(k, ring=False) == []
