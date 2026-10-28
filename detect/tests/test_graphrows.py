"""The C2 labels and properties the detectors read (PHASE-3.md 7.1.2), pinned on one small graph.

`graphrows.from_records` is the oracle's own reading of C2 and does not call the loader's
mapping; this test pins what it gives. The Neo4j test mode and the world parity test compare it
with the loader (PHASE-3.md 7.1.5): when they differ, find which side departs from C2 1.2.0 and
fix that side, never this test.
"""

from datetime import UTC, datetime

from kit import Kit
from neonradar_detect.graphrows import from_records


def _graph():
    k = Kit()
    addr = k.address_at("a", "Suite 2, 3 Fixture Road, Fixture Town, QQ3 3QQ", "QQ3 3QQ")
    co = k.company(
        "c",
        incorporated="2019-05-06",
        sector="retail",
        address=addr,
        accounts_category="DORMANT",
        psc_statements=("no-individual-or-entity-with-signficant-control",),
    )
    parent = k.company("p", jurisdiction="je")
    person = k.person("x", topics=("role.pep",))
    rel = k.person("y")
    listed = k.person("s", topics=("sanction",))
    k.sanction(listed, provisions=("Asset freeze",), end="2027-01-01")
    acct = k.account("1", co, opened="2024-02-03")
    ledger = k.account("2", k.company("bank"), kind="cash_ledger")
    pay = k.pay(ledger, acct, 9500, "2026-03-02T10:15", channel="cash_deposit")
    own = k.owns(parent, co, "50-75", nominee=True, start="2020-01-01")
    ctl = k.controls(person, co, "voting", band="25-50")
    k.consolidates(parent, co)
    k.director(person, co, start="2021-01-01", end="2023-01-01", nominee=True)
    k.represents(parent, co)
    k.family(person, rel, "spouse")
    k.associate(person, listed)
    post = k.position("m", country="zz")
    k.occupancy(person, post, start="2022-01-01", end="2025-06-30")
    return from_records(k.records), {"co": co, "acct": acct, "pay": pay, "own": own, "ctl": ctl}


def test_node_labels_and_properties():
    g, ids = _graph()
    co = g.node(ids["co"])
    assert {"Entity", "LegalEntity", "Organization", "Company", "Synthetic"} <= co.labels
    assert (co.get("incorporation_date"), co.get("sector")) == ("2019-05-06", "retail")
    assert co.get("accounts_category") == "DORMANT"
    assert co.get("psc_statements") == ["no-individual-or-entity-with-signficant-control"]
    assert co.get("datasets") == ["nr_synthetic"] and co.synthetic is True
    acct = g.node(ids["acct"])
    assert {"Entity", "Account"} <= acct.labels
    assert (acct.get("opening_date"), acct.get("account_kind")) == ("2024-02-03", "customer")
    assert acct.get("caption") == acct.get("account_number")
    addr = g.node("syn-fx-addr-a")
    assert (addr.get("postal_code"), addr.get("city")) == ("QQ3 3QQ", "Fixture Town")
    assert addr.get("full").startswith("Suite 2")
    assert {"PEP"} <= g.node("syn-fx-p-x").labels
    assert {"Sanctioned"} <= g.node("syn-fx-p-s").labels
    [sanction] = g.nodes("Sanction")
    assert (
        sanction.get("provisions") == ["Asset freeze"] and sanction.get("end_date") == "2027-01-01"
    )
    assert g.node("syn-fx-pos-m").get("country") == "zz"
    assert g.node("syn-fx-co-p").get("countries") == ["je"]


def test_relationship_types_and_properties():
    g, ids = _graph()
    [paid] = g.rels("PAID")
    assert paid.id == ids["pay"] and paid.get("ts") == datetime(2026, 3, 2, 10, 15, tzinfo=UTC)
    assert (paid.get("amount"), paid.get("currency"), paid.get("channel")) == (
        9500.0,
        "GBP",
        "cash_deposit",
    )
    [owns] = g.rels("OWNS")
    assert (owns.get("share_pct_min"), owns.get("share_pct_max")) == (50.0, 75.0)
    assert owns.get("share_min_exclusive") is True and owns.get("share_max_exclusive") is True
    assert owns.get("is_nominee") is True and owns.get("start_date") == "2020-01-01"
    [ctl] = g.rels("CONTROLS")
    assert ctl.get("control_type") == "voting" and ctl.get("share_pct_min") == 25.0
    assert ctl.get("share_min_exclusive") is True and ctl.get("share_max_exclusive") is False
    [cons] = g.rels("CONSOLIDATES")
    assert cons.get("level") == "ultimate"
    [d] = g.rels("DIRECTOR_OF")
    assert (d.get("start_date"), d.get("end_date"), d.get("is_nominee")) == (
        "2021-01-01",
        "2023-01-01",
        True,
    )
    [h] = g.rels("HAS_ADDRESS")
    assert h.get("role") == "registered" and h.id == f"{ids['co']}|addr|syn-fx-addr-a"
    [fam] = g.rels("FAMILY_OF")
    assert fam.get("relationship") == "spouse"
    [assoc] = g.rels("ASSOCIATE_OF")
    assert assoc.get("relationship") == "business partner"
    [occ] = g.rels("HOLDS_POSITION")
    assert (occ.get("start_date"), occ.get("end_date")) == ("2022-01-01", "2025-06-30")
    [subject] = g.rels("SUBJECT_OF")
    assert subject.source == "syn-fx-p-s"
    assert len(g.rels("HOLDS_ACCOUNT")) == 2 and len(g.rels("REPRESENTS")) == 1
    assert g.holders(ids["acct"])[0].id == ids["co"]
