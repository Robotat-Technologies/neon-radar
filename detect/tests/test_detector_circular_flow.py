from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import circular_flow as cf
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _cycle(
    k: Kit, tag: str, amounts: list[float], times: list[str], *, holder_real: bool = False
) -> list[str]:
    holder = (
        k.company(f"gbch-co-T{tag}", "Test Holder Ltd", real=True)
        if holder_real
        else k.company(f"{tag}o")
    )
    accounts = [k.account(f"{tag}0", holder)]
    for i in range(1, len(amounts)):
        accounts.append(k.account(f"{tag}{i}", k.company(f"{tag}{i}")))
    edges = []
    for i, (amount, when) in enumerate(zip(amounts, times, strict=True)):
        src = accounts[i]
        dst = accounts[(i + 1) % len(accounts)]
        edges.append(k.pay(src, dst, amount, when, pid=f"syn-fx-pay-{tag}{i}"))
    return edges


def _run(k: Kit, **overrides):
    out = cf.run(source_of(k.records), cf.Params(**overrides), WINDOW)
    return {f.edge_ids: f for f in out.findings}


def test_phase1_cases_a_to_e():
    k = Kit()
    a = _cycle(
        k,
        "a",
        [120000, 117600, 115248, 115200],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-05T11:00", "2026-03-08T16:40"],
    )
    b = _cycle(
        k, "b", [50000, 49000, 48500], ["2026-03-10T09:00", "2026-03-11T09:00", "2026-03-12T09:00"]
    )
    _cycle(
        k,
        "c",
        [120000, 117600, 115248, 115200],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-02T11:00", "2026-03-08T16:40"],
    )
    _cycle(
        k,
        "d",
        [120000, 117600, 115248, 115200],
        ["2026-04-01T09:00", "2026-04-15T10:00", "2026-04-30T11:00", "2026-05-11T16:40"],
    )
    _cycle(
        k,
        "e",
        [120000, 117600, 115248, 36000],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-05T11:00", "2026-03-08T16:40"],
    )
    found = _run(k)
    assert set(found) == {tuple(sorted(a)), tuple(sorted(b))}
    fa = found[tuple(sorted(a))]
    assert fa.variant == "same_account" and fa.metrics["cycle_length"] == 4
    assert fa.metrics["return_ratio"] == 0.96 and fa.metrics["duration_days"] == 7
    assert fa.pattern_strength == 0.7946  # 0.5 * 0.96 + 0.3 * (1 - 151.6667 / 336) + 0.2 * 0.75
    assert [s.role for s in fa.subjects] == ["origin", "origin_holder"]
    assert fa.steps == tuple((e,) for e in a)


def test_same_holder_return():
    k = Kit()
    holder = k.company("h")
    a1 = k.account("h1", holder)
    a2 = k.account("h2", holder)
    x = k.account("x", k.company("x"))
    y = k.account("y", k.company("y"))
    e = [
        k.pay(a1, x, 80000, "2026-02-02T09:00"),
        k.pay(x, y, 79000, "2026-02-03T09:00"),
        k.pay(y, a2, 78000, "2026-02-04T09:00"),
    ]
    found = _run(k)
    f = found[tuple(sorted(e))]
    assert (
        f.variant == "same_holder"
        and f.metrics["return_point"] == "another account of the same holder"
    )
    assert [s.role for s in f.subjects] == ["origin", "origin_holder", "return_account"]
    assert _run(k, same_holder=False) == {}


def test_hop_above_first_amount_and_own_account_transfer_are_not_cycles():
    k = Kit()
    _cycle(
        k, "m", [10000, 25000, 9800], ["2026-02-02T09:00", "2026-02-03T09:00", "2026-02-04T09:00"]
    )
    holder = k.company("own")
    a1, a2 = k.account("own1", holder), k.account("own2", holder)
    z = k.account("z", k.company("z"))
    k.pay(a1, a2, 20000, "2026-02-02T09:00")
    k.pay(a2, z, 19900, "2026-02-03T09:00")
    k.pay(z, a1, 19800, "2026-02-04T09:00")
    found = _run(k)
    # the merge hop breaks the first cycle; the own-account transfer closes at once (1 hop),
    # but the transfer a2 -> z -> a1 is a same-holder cycle of 2 hops starting at a2
    assert [f.variant for f in found.values()] == ["same_holder"]


def test_payment_straight_back_needs_three_hops_by_default():
    k = Kit()
    shop = k.account("shop", k.company("shop"))
    buyer = k.account("buyer", k.company("buyer"))
    e = [k.pay(buyer, shop, 5000, "2026-05-04T10:00"), k.pay(shop, buyer, 5000, "2026-05-06T15:00")]
    assert _run(k) == {}  # a refund's shape
    assert tuple(sorted(e)) in _run(k, min_hops_same_account=2)  # the documented false positive


def test_case_f_real_holder_is_reported_for_the_policy_to_withhold():
    k = Kit()
    edges = _cycle(
        k,
        "f",
        [120000, 117600, 115248, 115200],
        ["2026-03-02T09:00", "2026-03-03T10:00", "2026-03-05T11:00", "2026-03-08T16:40"],
        holder_real=True,
    )
    found = _run(k)
    f = found[tuple(sorted(edges))]
    assert f.activity and "gbch-co-Tf" in {s.entity_id for s in f.subjects}
