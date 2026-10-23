from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import mass_registration_address as mr
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    overrides.setdefault("top_share", 0.0)
    return mr.run(source_of(k.records), mr.Params(**overrides), WINDOW).findings


def _address(k: Kit, aid: str, full: str, postcode: str) -> str:
    rid = k.address(aid, full)
    record = next(r for r in k.records if r["id"] == rid)
    record["properties"]["postalCode"] = [postcode]
    return rid


def test_factory_address_with_bursts_shared_directors_and_payments():
    k = Kit()
    addr = _address(k, "factory", "Suite 1, 1 Fixture Lane, QQ9 9QQ", "QQ9 9QQ")
    cos = [
        k.company(
            f"f{i:02d}",
            incorporated=f"2025-09-{1 + i:02d}" if i < 15 else f"2023-0{1 + i % 9}-10",
            address=addr,
        )
        for i in range(25)
    ]
    d1, d2, d3 = k.person("d1"), k.person("d2"), k.person("d3")
    for c in cos[:5]:
        k.director(d1, c)
    for c in cos[5:10]:
        k.director(d2, c)
    for c in cos[10:14]:
        k.director(d3, c, start="2019-01-01", end="2024-01-01")  # resigned: not shared now
    accts = [k.account(f"fa{i}", c) for i, c in enumerate(cos[:4])]
    for a, b in ((0, 1), (1, 2), (2, 3)):
        k.pay(accts[a], accts[b], 40000, f"2026-02-0{a + 2}T10:00")
    [f] = _run(k)
    assert f.anchor == addr and f.metrics["companies"] == 25
    assert f.metrics["incorporated_in_burst"] == 15 and f.metrics["shared_directors"] == 2
    assert f.metrics["companies_with_shared_director"] == 10 and f.metrics["paying_pairs"] == 3
    assert f.activity and len(f.steps) == 3 and f.metrics["po_box"] is False
    assert f.pattern_strength == round(0.3 * 25 / 125 + 0.2 * 15 / 25 + 0.2 * 10 / 25 + 0.2, 4)


def test_below_threshold_dissolved_and_real_cluster_without_payment_terms():
    k = Kit()
    small = k.address("small")
    for i in range(24):
        k.company(f"s{i}", address=small)
    gone = k.company("gone", address=small)
    next(r for r in k.records if r["id"] == gone)["properties"]["dissolutionDate"] = ["2024-05-01"]
    assert _run(k) == []  # 24 active organisations
    assert len(_run(k, active_only=False)) == 1
    agent = k.address("agent")
    cos = [k.company(f"r{i}", address=agent) for i in range(24)]
    k.company("gbch-co-T0000001", "Test Holder Ltd", real=True, address=agent)
    accts = [k.account(f"ra{i}", c) for i, c in enumerate(cos[:2])]
    k.pay(accts[0], accts[1], 5000, "2026-03-03T10:00")
    [f] = _run(k)
    assert f.metrics["companies"] == 25 and f.metrics["paying_pairs"] == 0 and not f.activity


def test_default_addresses_are_skipped_and_po_boxes_flagged():
    k = Kit()
    default = _address(
        k, "chdefault", "Companies House Default Address, PO Box 4385, Cardiff", "cf148lh"
    )
    box = _address(k, "box", "PO Box 77, Fixture Town", "QQ7 7QQ")
    for i in range(30):
        k.company(f"m{i}", address=default)
        k.company(f"b{i}", address=box)
    [f] = _run(k)
    assert f.anchor == box and f.metrics["po_box"] is True


def test_top_share_raises_the_threshold_to_the_quantile():
    k = Kit()
    big, mid = k.address("big"), k.address("mid")
    for i in range(40):
        k.company(f"g{i}", address=big)
    for i in range(30):
        k.company(f"h{i}", address=mid)
    for i in range(98):
        k.company(f"o{i}", address=k.address(f"own{i}"))
    # 100 addresses: the nearest-rank 0.99 quantile is the 99th count in order, 30
    assert {f.anchor for f in _run(k, top_share=0.01)} == {big, mid}
    assert {f.anchor for f in _run(k, top_share=0.001)} == {big}  # the 100th count, 40
