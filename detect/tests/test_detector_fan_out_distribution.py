from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import fan_out_distribution as fo
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    return fo.run(source_of(k.records), fo.Params(**overrides), WINDOW).findings


def test_distribution_to_new_accounts_that_cash_out():
    k = Kit()
    k.history()
    branch = k.account("branch", k.company("bank"), kind="cash_ledger")
    dist = k.account("dist", k.company("dist"))
    edges = []
    for i in range(10):
        r = k.account(f"r{i}", k.person(f"r{i}"), opened="2026-02-01")
        edges.append(k.pay(dist, r, 950, f"2026-03-02T1{i % 9}:00"))
        edges.append(k.pay(r, branch, 900, "2026-03-04T12:00", channel="cash_withdrawal"))
    [f] = _run(k)
    assert f.edge_ids == tuple(sorted(edges))
    assert f.metrics["recipients"] == 10 and f.metrics["onward_share"] == 1.0
    assert f.metrics["round_share"] == 0.0 and f.metrics["amount_cv"] == 0.0


def test_payroll_and_refund_lookalikes():
    k = Kit()
    employer = k.account("employer", k.company("employer"))
    employees = [k.account(f"e{i}", k.person(f"e{i}")) for i in range(10)]
    shop = k.account("shopx", k.company("shopx"))
    for month in ("01", "02", "03"):
        for i, e in enumerate(employees):
            k.pay(employer, e, 1800 + 140 * i, f"2026-{month}-25T08:00")
            k.pay(e, shop, 300, f"2026-{month}-26T12:00")
    organiser = k.account("organiser", k.company("organiser"))
    for i in range(12):
        c = k.account(f"c{i}", k.person(f"c{i}"))
        k.pay(c, organiser, 400, "2026-04-02T10:00")
        k.pay(organiser, c, 400, "2026-05-10T10:00")
    assert _run(k) == []


def test_first_payroll_is_not_found_because_salaries_stay():
    k = Kit()
    employer = k.account("employer", k.company("employer"))
    shop = k.account("shopy", k.company("shopy"))
    for i in range(10):
        e = k.account(f"n{i}", k.person(f"n{i}"))
        k.pay(employer, e, 2000, "2026-01-30T08:00")
        k.pay(e, shop, 250, "2026-02-01T12:00")
    assert _run(k) == []
