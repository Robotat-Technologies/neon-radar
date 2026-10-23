from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import layering_chain as lc
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _chain(
    k: Kit, tag: str, amounts: list[float], times: list[str], *, shared_address: bool = False
) -> list[str]:
    addr = k.address(f"{tag}-addr") if shared_address else ""
    accounts = [
        k.account(f"{tag}{i}", k.company(f"{tag}{i}", address=addr if 0 < i < len(amounts) else ""))
        for i in range(len(amounts) + 1)
    ]
    return [k.pay(accounts[i], accounts[i + 1], amounts[i], times[i]) for i in range(len(amounts))]


def _run(k: Kit, **overrides):
    out = lc.run(source_of(k.records), lc.Params(**overrides), WINDOW)
    return out.findings


def test_four_hop_chain_with_shared_address():
    k = Kit()
    e = _chain(
        k,
        "a",
        [250000, 245000, 240100, 235300],
        ["2026-02-02T09:00", "2026-02-03T11:00", "2026-02-04T15:00", "2026-02-06T10:00"],
        shared_address=True,
    )
    [f] = _run(k)
    assert f.steps[:4] == tuple((x,) for x in e)
    assert f.metrics["chain_length"] == 4 and f.metrics["linked_holder_pairs"] == 3
    assert f.metrics["quiet_intermediaries"] == 3
    assert len(f.steps) == 7  # four payments, three shared-address links
    assert [s.role for s in f.subjects] == [
        "origin",
        "origin_holder",
        "destination",
        "destination_holder",
    ]


def test_prefix_and_suffix_are_not_reported_separately():
    k = Kit()
    _chain(
        k,
        "b",
        [50000, 49000, 48000, 47500, 47000],
        [
            "2026-03-02T09:00",
            "2026-03-02T15:00",
            "2026-03-03T09:00",
            "2026-03-04T09:00",
            "2026-03-05T09:00",
        ],
    )
    found = _run(k)
    assert [f.metrics["chain_length"] for f in found] == [5]


def test_dwell_amount_and_holder_rules():
    k = Kit()
    _chain(
        k, "c", [50000, 49000, 48000], ["2026-03-02T09:00", "2026-03-08T09:00", "2026-03-09T09:00"]
    )  # 6 days dwell
    _chain(
        k, "d", [50000, 30000, 29500], ["2026-03-02T09:00", "2026-03-02T15:00", "2026-03-03T09:00"]
    )  # split
    # third hop back to an account of the first holder: left to circular_flow
    holder = k.company("eh")
    a0, a3 = k.account("e0", holder), k.account("e3", holder)
    a1, a2 = k.account("e1", k.company("e1")), k.account("e2", k.company("e2"))
    k.pay(a0, a1, 40000, "2026-04-01T09:00")
    k.pay(a1, a2, 39500, "2026-04-01T12:00")
    k.pay(a2, a3, 39000, "2026-04-01T18:00")
    assert _run(k) == []


def test_three_hops_found_when_allowed_but_not_below_min_amount():
    k = Kit()
    _chain(k, "f", [9000, 8900, 8800], ["2026-05-02T09:00", "2026-05-02T12:00", "2026-05-02T18:00"])
    assert _run(k) == []
    assert len(_run(k, min_amount=5000)) == 1
