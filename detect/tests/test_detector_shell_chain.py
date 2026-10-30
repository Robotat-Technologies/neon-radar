from datetime import UTC, datetime

from kit import Kit, source_of
from neonradar_detect.detectors import shell_chain as sc
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(k: Kit, **overrides):
    overrides.setdefault("min_indicators", 1)  # these cases test each indicator on its own
    return sc.run(source_of(k.records), sc.Params(**overrides), WINDOW).findings


def test_chain_across_jurisdictions_with_a_nominee_owner():
    k = Kit()
    person = k.person("ubo")
    a = k.company("a", jurisdiction="vg")
    b = k.company("b", jurisdiction="cy")
    c = k.company("c", jurisdiction="gb")
    k.owns(person, a)
    k.owns(a, b, nominee=True)
    k.owns(b, c, "50-75")
    [f] = _run(k)
    assert f.anchor == c and f.variant == "chain" and f.metrics["indicators"] == "nominee"
    assert f.metrics["company_layers"] == 3 and f.metrics["jurisdiction_list"] == "cy, gb, vg"
    assert f.metrics["top_kind"] == "person" and f.metrics["nominee_links"] == 1
    assert [s.role for s in f.subjects] == ["owned_company"]
    assert not f.activity
    assert f.pattern_strength == round(0.15 * 2 / 3 + 0.15 + 0.2, 4)


def test_layers_alone_are_not_enough_and_two_layers_with_an_indicator_are():
    k = Kit()
    person = k.person("p2")
    a, b, c = (k.company(x, jurisdiction=j) for x, j in (("a2", "vg"), ("b2", "cy"), ("c2", "gb")))
    k.owns(person, a)
    k.owns(a, b)
    k.owns(b, c)
    assert _run(k) == []  # a group across three jurisdictions with a person at the top
    hold, op = k.company("hold"), k.company("op")
    k.owns(k.person("p3"), hold)
    k.owns(hold, op)
    k.director(k.person("nd"), op, nominee=True)
    [f] = _run(k)
    assert f.anchor == op and f.metrics["company_layers"] == 2 and f.metrics["jurisdictions"] == 1
    assert _run(k, min_company_layers=3) == []


def test_ownerless_top_loop_and_professional_director():
    k = Kit()
    x = k.company("x", jurisdiction="vg")
    y, z = k.company("y"), k.company("z")
    k.owns(x, y)
    k.owns(y, z)
    l1, l2, l3 = k.company("l1", jurisdiction="pa"), k.company("l2"), k.company("l3")
    k.owns(l1, l2, "50-75")
    k.owns(l2, l3, "50-75")
    k.owns(l3, l1, "25-50")
    found = {f.variant: f for f in _run(k)}
    assert (
        found["chain"].anchor == z
        and found["chain"].metrics["top_kind"] == "company without a recorded owner"
    )
    assert (
        found["loop"].metrics["top_kind"] == "loop" and found["loop"].metrics["company_layers"] == 3
    )
    k.controls(
        k.person("ctl"), x, "influence"
    )  # a recorded controller: the top is no longer ownerless
    assert {f.variant for f in _run(k)} == {"loop"}
    k2 = Kit()
    person = k2.person("u")
    m, n, o = k2.company("m", jurisdiction="je"), k2.company("n"), k2.company("o")
    k2.owns(person, m)
    k2.owns(m, n)
    k2.owns(n, o)
    pro = k2.person("pro")
    for i in range(12):
        k2.director(pro, k2.company(f"client{i}", jurisdiction="je"))
    k2.director(pro, m)
    [f] = _run(k2)
    assert f.metrics["professional_directors"] == 1 and pro in f.node_ids


def test_psc_statement_po_box_and_crowded_address():
    k = Kit()
    person = k.person("own")
    box = k.address("box", "PO Box 12, Fixture Town")
    a = k.company("sa", psc_statements=("psc-exists-but-not-identified",), address=box)
    b = k.company("sb")
    k.owns(person, a)
    k.owns(a, b)
    [f] = _run(k)
    assert f.metrics["indicators"] == "unknown_owner, po_box" and box in f.node_ids
    k2 = Kit()
    hub = k2.address("hub")
    for i in range(25):
        k2.company(f"tenant{i}", address=hub)
    c = k2.company("sc", address=hub)
    d = k2.company("sd")
    k2.owns(k2.person("own2"), c)
    k2.owns(c, d)
    [f2] = _run(k2)
    assert f2.metrics["indicators"] == "mass_registration_address"
    assert _run(k2, mass_address_companies=27) == []


def test_default_needs_two_indicators_except_for_a_loop():
    k = Kit()
    x = k.company("tx", jurisdiction="us")  # a foreign parent with no owner recorded
    y = k.company("ty")
    k.owns(x, y)
    assert sc.run(source_of(k.records), sc.Params(), WINDOW).findings == []
    k.director(k.person("nd2"), y, nominee=True)
    [f] = sc.run(source_of(k.records), sc.Params(), WINDOW).findings
    assert f.metrics["indicators"] == "nominee, unknown_owner"
    loop = Kit()
    a, b = loop.company("la"), loop.company("lb", jurisdiction="pa")
    loop.owns(a, b, "50-75")
    loop.owns(b, a, "50-75")
    [g] = sc.run(source_of(loop.records), sc.Params(), WINDOW).findings
    assert g.variant == "loop"


def test_ended_holdings_and_resigned_appointments_are_history():
    k = Kit()
    a, b, c = k.company("ea", jurisdiction="vg"), k.company("eb"), k.company("ec")
    k.owns(k.person("old-ubo"), a)
    k.owns(a, b, nominee=True, end="2025-06-30")  # sold before the end of the window
    k.owns(b, c)
    [f] = _run(k)  # B is now the top: B and C, with no recorded owner above B
    assert f.anchor == c and f.metrics["company_layers"] == 2
    assert f.metrics["indicators"] == "unknown_owner" and f.metrics["nominee_links"] == 0
    k2 = Kit()
    m, n = k2.company("rm", jurisdiction="je"), k2.company("rn")
    k2.owns(k2.person("u2"), m)
    k2.owns(m, n)
    pro = k2.person("retired")
    for i in range(12):
        k2.director(pro, k2.company(f"past{i}"), start="2015-01-01", end="2020-01-01")
    k2.director(pro, m)
    assert _run(k2) == []  # one current appointment: not a director of many companies
