from datetime import UTC, date, datetime, timedelta

from kit import Kit, detect, source_of
from neonradar_detect.detectors import formation_agent_cluster as fa
from neonradar_detect.detectors import pep_exposure as pe
from neonradar_detect.detectors import recycled_directors as rd
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))


def _run(module, k: Kit, **overrides):
    return {
        f.anchor: f
        for f in module.run(source_of(k.records), module.Params(**overrides), WINDOW).findings
    }


# formation_agent_cluster ---------------------------------------------------------------------


def _agency(
    k: Kit, name: str, *, spread_days: int = 1, shared: int = 2, n: int = 12
) -> tuple[str, list[str]]:
    office = k.address(f"{name}-office")
    agent = k.company(f"{name}-agent", address=office)
    clients = []
    for i in range(n):
        incorporated = (date(2025, 3, 1) + timedelta(days=i * spread_days)).isoformat()
        c = k.company(
            f"{name}-c{i:02d}", incorporated=incorporated, address=office if i < 6 else ""
        )
        k.represents(agent, c)
        clients.append(c)
    for s in range(shared):
        officer = k.person(f"{name}-officer{s}")
        for c in clients[s * 4 : s * 4 + 4]:
            k.director(officer, c, nominee=s == 0)
    return agent, clients


def test_agent_behind_a_burst_with_shared_officers_and_payments():
    k = Kit()
    agent, clients = _agency(k, "fac")
    accts = [k.account(f"fac{i}", c) for i, c in enumerate(clients[:4])]
    for a, b in ((0, 1), (1, 2), (2, 3)):
        k.pay(accts[a], accts[b], 25000, f"2026-02-0{a + 2}T10:00")
    [f] = _run(fa, k).values()
    assert f.anchor == agent and [s.role for s in f.subjects] == ["agent"]
    m = f.metrics
    assert (
        m["incorporated_in_burst"],
        m["shared_officers"],
        m["companies_with_shared_officer"],
    ) == (12, 2, 8)
    assert (m["at_agent_address"], m["nominee_officers"], m["paying_pairs"]) == (6, 1, 3)
    assert f.activity and f.pattern_strength == round(
        0.3 * 12 / 30 + 0.25 * 8 / 12 + 0.15 * 6 / 12 + 0.15 + 0.15, 4
    )


def test_spread_out_formations_or_one_shared_officer_are_not_a_cluster():
    k = Kit()
    _agency(k, "slow", spread_days=30)
    _agency(k, "solo", shared=1)
    assert _run(fa, k) == {}


# recycled_directors --------------------------------------------------------------------------


def test_many_unrelated_boards_but_not_one_group():
    k = Kit()
    busy = k.person("busy")
    for i in range(10):
        k.director(busy, k.company(f"u{i}"), start=f"20{15 + i % 8}-0{1 + i % 9}-01")
    group_man = k.person("group")
    hold = k.company("hold")
    k.director(group_man, hold, start="2018-01-01")
    for i in range(11):
        sub = k.company(f"sub{i}")
        k.owns(hold, sub)
        k.director(group_man, sub, start="2018-01-01")
    found = _run(rd, k)
    assert set(found) == {busy}  # twelve boards in one group are one group
    f = found[busy]
    assert f.variant == "many_boards" and f.metrics["active_groups"] == 10
    assert [s.role for s in f.subjects] == ["director"]


def test_burst_of_short_appointments_and_a_relative_owner():
    k = Kit()
    straw = k.person("straw")
    brother = k.person("bro")
    k.family(straw, brother, "sibling")
    companies = [k.company(f"s{i}", incorporated="2025-05-01") for i in range(5)]
    for i, c in enumerate(companies):
        k.director(straw, c, start=f"2025-05-{2 + i:02d}", end=f"2025-07-{2 + i:02d}")
    k.owns(brother, companies[0])
    [f] = _run(rd, k).values()
    m = f.metrics
    assert f.variant == "burst" and (
        m["burst_groups"],
        m["short_tenures"],
        m["relative_owned_companies"],
    ) == (5, 5, 1)
    assert m["active_groups"] == 0 and brother in f.node_ids


# pep_exposure --------------------------------------------------------------------------------


def _pep(k: Kit, name: str, *, end: str = "", country: str = "zz") -> str:
    pep = k.person(name, topics=("role.pep",))
    k.occupancy(pep, k.position(f"{name}-post", country=country), start="2019-01-01", end=end)
    return pep


def test_pep_holdings_through_companies():
    k = Kit()
    pep = _pep(k, "minister")
    a, b = k.company("pa"), k.company("pb")
    k.owns(pep, a, "75-100")
    k.owns(a, b, "25-50")
    found = _run(pe, k)
    assert (
        set(found) == {a, b}
        and found[a].variant == "pep"
        and found[a].metrics["office"] == "in office"
    )
    assert found[a].pattern_strength == round(0.35 + 0.3 + 0.2 + 0.15, 4)
    assert found[b].metrics["shortest_path"] == 2 and pep in found[b].node_ids
    assert found[b].pattern_strength == round(0.35 + 0.3 * (1 - 1 / 3) + 0.2 + 0.15, 4)


def test_family_while_in_office_only_and_former_peps_for_twelve_months():
    k = Kit()
    pep = _pep(k, "mayor")
    spouse, cousin = k.person("spouse"), k.person("cousin")
    k.family(pep, spouse, "spouse")
    k.family(pep, cousin, "cousin")
    c, d, own = k.company("sc"), k.company("cc"), k.company("own")
    k.owns(spouse, c)
    k.owns(cousin, d)
    k.director(pep, own)
    found = _run(pe, k)
    assert set(found) == {c, own} and found[c].variant == "family"
    assert (
        found[c].metrics["family_relationship"] == "spouse"
        and found[own].metrics["first_link"] == "DIRECTOR_OF"
    )
    k2 = Kit()
    left = _pep(k2, "left", end="2025-12-31")  # left office six months before the end of the window
    spouse2 = k2.person("spouse2")
    k2.family(left, spouse2, "spouse")
    e, g = k2.company("e"), k2.company("g")
    k2.owns(left, e)
    k2.owns(spouse2, g)
    found2 = _run(pe, k2)
    assert set(found2) == {e} and found2[e].metrics["office"] == "former"
    k3 = Kit()
    long_gone = _pep(k3, "gone", end="2024-12-31")  # eighteen months before the end of the window
    h = k3.company("h")
    k3.owns(long_gone, h)
    assert _run(pe, k3) == {}
    assert set(_run(pe, k3, after_office_months=24)) == {h}


def test_family_links_are_read_from_the_relatives_side():
    """FtM names the relative from the person's side: a PEP recorded as someone's mother makes
    that someone the PEP's child; a PEP recorded as someone's son-in-law makes that someone a
    parent-in-law, outside reg 35(12)(b); a bare "partner" is not in the default list."""
    k = Kit()
    pep = _pep(k, "judge")
    child, in_law, partner = k.person("child"), k.person("inlaw"), k.person("partner")
    k.family(child, pep, "mother")
    k.family(in_law, pep, "son-in-law")
    k.family(pep, partner, "partner")
    c, i, q = k.company("child-co"), k.company("inlaw-co"), k.company("partner-co")
    k.owns(child, c)
    k.owns(in_law, i)
    k.owns(partner, q)
    found = _run(pe, k)
    assert set(found) == {c} and found[c].variant == "family"
    assert found[c].metrics["family_relationship"] == "child"  # what the person is to the PEP


def test_associates_need_business_relations_or_a_joint_holding_and_links_must_be_current():
    k = Kit()
    pep = _pep(k, "senator")
    friend, partner = k.person("friend"), k.person("joint")
    k.associate(pep, friend, "friend")
    k.associate(pep, partner, "friend")
    joint = k.company("joint-co")
    k.owns(pep, joint, "25-50")
    k.owns(partner, joint, "25-50")
    f_co, p_co, old = k.company("friend-co"), k.company("joint-other"), k.company("old-board")
    k.owns(friend, f_co)
    k.owns(partner, p_co)
    k.director(pep, old, start="2018-01-01", end="2025-03-31")  # resigned before the window ends
    found = _run(pe, k)
    assert set(found) == {joint, p_co} and found[p_co].variant == "associate"


def test_rca_follows_the_office_of_the_pep_it_is_linked_to():
    k = Kit()
    former = _pep(k, "ex", end="2023-06-30")
    current = _pep(k, "now")
    rca_old = k.person("rca-old", topics=("role.rca",))
    rca_new = k.person("rca-new", topics=("role.rca",))
    k.family(former, rca_old, "sibling")
    k.associate(current, rca_new, "adviser")
    a, b = k.company("rca-old-co"), k.company("rca-new-co")
    k.owns(rca_old, a)
    k.owns(rca_new, b)
    found = _run(pe, k)
    assert a not in found  # reg 35(11): the linked PEP left office
    assert found[b].variant == "rca" and found[b].metrics["office"] == "in office"


def test_associates_rca_and_domestic_peps():
    k = Kit()
    pep = _pep(k, "envoy", country="gb")
    partner = k.person("partner")
    k.associate(pep, partner, "business partner")
    a = k.company("assoc-co")
    k.owns(partner, a, "50-75")
    rca = k.person("rca", topics=("role.rca",))
    r = k.company("rca-co")
    k.controls(rca, r, "appointment")
    found = _run(pe, k)
    assert found[a].variant == "associate" and found[a].metrics["domestic"] is True
    assert found[a].pattern_strength == round(0.35 * 0.6 + 0.3 + 0.2 + 0.15 - 0.1, 4)
    assert found[r].variant == "rca" and found[r].metrics["office_dates_unknown"] is True


def test_a_real_person_as_subject_is_withheld():
    k = Kit()
    real_person = k.person("gbch-p-T0000003", "Test Person", real=True)
    for i in range(10):
        k.director(real_person, k.company(f"board{i}"), start=f"201{i}-01-01")
    result = detect(k.records, {"recycled_directors": rd.Params()})
    assert result.alerts == []
    assert result.summary["withheld"] == {
        "activity_on_real": 0,
        "real_person_subject": 1,
        "real_person_evidence": 0,
        "registry_on_real": 0,
    }


def test_an_agent_whose_kind_the_source_does_not_state_is_withheld():
    """An ICIJ intermediary may be a person: as the subject of a real-data finding it is withheld
    like a person (R-REAL (b))."""
    k = Kit()
    agent = k.legal_entity("icij-T0000001", "Test Intermediary", dataset="icij_offshore_leaks")
    officers = [k.person("io0"), k.person("io1")]
    for i in range(12):
        c = k.company(f"ic{i:02d}", incorporated=(date(2025, 3, 1) + timedelta(days=i)).isoformat())
        k.represents(agent, c)
        if i < 8:
            k.director(officers[i // 4], c)
    result = detect(k.records, {"formation_agent_cluster": fa.Params()})
    assert result.alerts == [] and result.summary["withheld"]["real_person_subject"] == 1
