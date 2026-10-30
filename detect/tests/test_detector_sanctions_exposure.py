from datetime import UTC, datetime

import pytest
from kit import Kit, detect, source_of
from neonradar_detect.detectors import sanctions_exposure as se
from neonradar_detect.source import Window

WINDOW = Window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))
MET, OPEN, NOT_MET, NONE = se.MET, se.OPEN, se.NOT_MET, se.NONE


def _run(k: Kit, **overrides):
    out = se.run(source_of(k.records), se.Params(**overrides), WINDOW)
    return {f.anchor: f for f in out.findings}


def _tests(f):
    return f.metrics["us_test"], f.metrics["uk_test"], f.metrics["eu_test"]


def _listed(k: Kit, name: str, *, person: bool = True):
    return (k.person if person else k.company)(name, topics=("sanction",))


# OFAC FAQ 401, examples 1 to 5 (typology-detection-definitions.md 10.1 and 10.3) -----------------


def test_faq_401_example_1_status_passes_entity_by_entity():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "exact:50")
    k.owns(a, b, "exact:50")
    found = _run(k)
    assert _tests(found[a]) == (MET, NOT_MET, MET)  # 50 is not "more than 50" for the UK
    assert _tests(found[b]) == (MET, NOT_MET, MET)
    # multiplying gives 25 percent, which is why the effective share is a teaching figure only
    assert (found[b].metrics["effective_share_min"], found[b].metrics["effective_share_max"]) == (
        25.0,
        25.0,
    )
    assert found[b].metrics["shortest_path"] == 2 and found[b].variant == "ownership"
    assert [s.role for s in found[b].subjects] == ["exposed_entity"]
    assert se.priority(found[b]) == "high"


def test_faq_401_example_2_two_owned_entities_add_up():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:50")
    k.owns(x, b, "exact:50")
    k.owns(a, c, "exact:25")
    k.owns(b, c, "exact:25")
    assert _tests(_run(k)[c]) == (MET, NOT_MET, MET)


def test_faq_401_example_3_direct_and_indirect_add_up():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "exact:50")
    k.owns(x, b, "exact:10")
    k.owns(a, b, "exact:40")
    assert _tests(_run(k)[b]) == (MET, NOT_MET, MET)


def test_faq_401_example_4_an_entity_below_50_does_not_pass_its_holding_on():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:50")
    k.owns(x, b, "exact:25")
    k.owns(a, c, "exact:25")
    k.owns(b, c, "exact:25")
    found = _run(k)
    assert _tests(found[b]) == (NOT_MET, NOT_MET, NOT_MET) and se.priority(found[b]) is None
    # only A passes the test, so only A's 25 percent counts in C: reported, and not met
    assert _tests(found[c]) == (NOT_MET, NOT_MET, NOT_MET)
    assert (found[c].metrics["listed_share_min"], found[c].metrics["listed_share_max"]) == (
        25.0,
        25.0,
    )


def test_faq_401_example_5_two_minority_stakes_do_not_pass_on():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:25")
    k.owns(x, b, "exact:25")
    k.owns(a, c, "exact:50")
    k.owns(b, c, "exact:50")
    found = _run(k)
    assert (
        _tests(found[a]) == (NOT_MET, NOT_MET, NOT_MET)
        and found[a].metrics["listed_share_min"] == 25.0
    )
    assert c not in found  # neither A nor B passes the test, so no listed holding reaches C


# the worked examples with Companies House bands (10.3) ----------------------------------------


@pytest.mark.parametrize(
    ("band", "expected"),
    [
        ("25-50", (OPEN, NOT_MET, OPEN)),  # (25, 50]: the upper bound 50 is closed
        ("50-75", (MET, MET, MET)),  # (50, 75)
        ("75-100", (MET, MET, MET)),
    ],
)
def test_one_listed_owner_with_a_band(band, expected):
    k = Kit()
    x = _listed(k, "x")
    e = k.company("e")
    k.owns(x, e, band)
    assert _tests(_run(k)[e]) == expected


def test_two_listed_owners_add_up_except_in_the_uk():
    k = Kit()
    x, y = _listed(k, "x"), _listed(k, "y")
    e = k.company("e")
    k.owns(x, e, "25-50")
    k.owns(y, e, "25-50")
    f = _run(k)[e]
    assert _tests(f) == (MET, NOT_MET, MET)  # the sum is (50, 100]; OFSI does not add persons up
    assert f.metrics["listed_parties"] == 2


def test_band_left_open_down_a_chain():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "75-100")
    k.owns(a, b, "25-50")
    found = _run(k)
    # A meets reg 7(2)(a) on its own shares: no stand-in for votes is needed
    assert _tests(found[a]) == (MET, MET, MET) and found[a].metrics["votes_follow_shares"] is False
    assert _tests(found[b]) == (OPEN, NOT_MET, OPEN)
    assert se.priority(found[b]) is None and found[b].pattern_strength < found[a].pattern_strength


def test_uk_chain_through_shares_says_votes_follow_shares():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "75-100")
    k.owns(a, b, "75-100")
    f = _run(k)[b]
    assert _tests(f) == (MET, MET, MET) and f.metrics["votes_follow_shares"] is True
    k.controls(x, a, "voting", band="75-100")  # the register also records X's votes in A
    f = _run(k)[b]
    assert _tests(f) == (MET, MET, MET) and f.metrics["votes_follow_shares"] is False


def test_uk_majority_stake_chain():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.owns(x, a, "50-75")
    k.owns(a, b, "50-75")
    assert _tests(_run(k)[b]) == (MET, MET, MET)


def test_uk_voting_rights_carry_a_chain_that_ownership_does_not():
    k = Kit()
    x = _listed(k, "x")
    a, b = k.company("a"), k.company("b")
    k.controls(x, a, "voting", band="50-75")
    k.owns(a, b, "75-100")
    found = _run(k)
    assert _tests(found[b]) == (NONE, MET, NONE)  # control never counts for OFAC
    assert found[b].metrics["votes_follow_shares"] is False and found[b].variant == "control"
    assert _tests(found[a]) == (NONE, MET, NONE)
    assert found[a].metrics["us_control_caution"] is True


def test_board_appointment_right_meets_the_uk_test_and_eu_criterion_a():
    k = Kit()
    x = _listed(k, "x")
    c = k.company("c")
    k.controls(x, c, "appointment")
    f = _run(k)[c]
    assert _tests(f) == (NONE, MET, NONE)
    assert f.metrics["eu_control_criteria"] == "(a)" and f.metrics["us_control_caution"] is True


def test_significant_influence_and_directorship_are_reported_apart():
    k = Kit()
    x = _listed(k, "x", person=False)
    p = _listed(k, "p")
    d, e = k.company("d"), k.company("e")
    k.controls(x, d, "influence")
    k.director(p, e)
    found = _run(k)
    assert _tests(found[d]) == (NONE, NOT_MET, NONE)
    assert found[d].metrics["uk_control_to_assess"] is True and found[d].variant == "control"
    assert found[e].variant == "director" and found[e].metrics["director_links"] == 1
    assert found[e].pattern_strength < found[d].pattern_strength


def test_consolidation_is_eu_criterion_g():
    k = Kit()
    x = _listed(k, "x", person=False)
    c = k.company("c")
    k.consolidates(x, c)
    f = _run(k)[c]
    assert f.metrics["eu_control_criteria"] == "(g)" and f.metrics["consolidation_links"] == 1


# seeds: each regime its own list -------------------------------------------------------------


def test_each_regime_uses_its_own_list():
    k = Kit()
    us = k.company("ofac-T0000001", topics=("sanction",), dataset="us_ofac_sdn")
    k.sanction(us, "us_ofac_sdn")
    uk = k.company("uksl-gT0000001", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k.sanction(uk, "gb_fcdo_sanctions", provisions=("Asset freeze", "Travel ban"))
    ban = k.person("uksl-gT0000002", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k.sanction(ban, "gb_fcdo_sanctions", provisions=("Travel ban",))
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(us, a, "75-100")
    k.owns(uk, b, "75-100")
    k.owns(ban, c, "75-100")
    found = _run(k)
    assert _tests(found[a]) == (MET, NONE, NONE) and found[a].metrics["lists"] == "us"
    assert _tests(found[b]) == (NONE, MET, NONE) and found[b].metrics["lists"] == "uk"
    assert c not in found  # a travel ban alone seeds no ownership test


def test_ended_designation_seeds_nothing_and_listed_targets_are_skipped():
    k = Kit()
    old = k.company("eufsf-T0000001", topics=("sanction",), dataset="eu_fsf")
    k.sanction(old, "eu_fsf", end="2025-12-31")
    x = _listed(k, "x")
    a, listed_too = k.company("a"), k.company("lt", topics=("sanction",))
    k.owns(old, a, "75-100")
    k.owns(x, listed_too, "75-100")
    assert _run(k) == {}


def test_missing_upper_bound_counts_as_100_and_is_reported():
    k = Kit()
    x = _listed(k, "x")
    e = k.company("e")
    rid = k.owns(x, e, "25-50")
    record = next(r for r in k.records if r["id"] == rid)
    del record["nr"]["share_pct_max"]
    f = _run(k)[e]
    assert f.metrics["unbounded"] is True
    assert _tests(f) == (OPEN, OPEN, OPEN)


def test_small_holdings_that_meet_no_test_are_left_out():
    k = Kit()
    x = _listed(k, "x")
    a, b, c = k.company("a"), k.company("b"), k.company("c")
    k.owns(x, a, "exact:20")
    k.owns(x, b, "exact:30")
    k.owns(b, c, "exact:40")  # 12 percent through B
    found = _run(k)
    assert set(found) == {b} and _tests(found[b]) == (NOT_MET, NOT_MET, NOT_MET)
    # C's 12 percent runs through B, which does not pass the test: no listed holding reaches C
    assert set(_run(k, min_reported_share=10.0)) == {a, b}


def test_registry_alert_about_a_real_organisation_is_a_structural_pattern():
    k = Kit()
    real_co = k.company("gbch-co-T0000002", "Test Holding Ltd", real=True)
    listed = k.company(
        "uksl-gT0000001", "Test Listed Ltd", topics=("sanction",), dataset="gb_fcdo_sanctions"
    )
    k.sanction(listed, "gb_fcdo_sanctions", provisions=("Asset freeze",))
    k.owns(listed, real_co, "75-100")
    [alert] = detect(k.records, {"sanctions_exposure": se.Params()}).alerts
    assert alert["wording_class"] == "structural_pattern"
    assert alert["data_flags"]["involves_real_entities"] is True
    assert alert["headline"] == (
        "Organisation with recorded ownership or control links to parties on the UK Sanctions List"
    )
    summary = alert["explanation"]["summary"]
    assert se.RESULT[("uk", MET)].format(list="the UK Sanctions List") in summary
    assert se.CLOSING in summary and "US test" not in summary
    assert alert["priority"] == "high"


def test_ended_links_count_no_more():
    """A resigned listed director and a listed owner who sold are history (OFAC FAQ 402: below
    50 percent an entity "is no longer considered automatically to be a blocked entity")."""
    k = Kit()
    x = _listed(k, "x")
    resigned, sold, kept = k.company("resigned"), k.company("sold"), k.company("kept")
    k.director(x, resigned, start="2019-01-01", end="2026-02-28")
    k.owns(x, sold, "75-100", start="2019-01-01", end="2026-05-31")
    k.owns(x, kept, "75-100", start="2019-01-01", end="2026-12-31")  # ends after the window
    assert set(_run(k)) == {kept}


def test_uk_nominee_holdings_and_entries_without_provisions():
    k = Kit()
    x = _listed(k, "x")
    n = k.company("n")
    k.owns(x, n, "75-100", nominee=True)
    f = _run(k)[n]
    assert _tests(f) == (MET, NOT_MET, MET) and f.metrics["uk_nominee_holdings"] == 1
    assert se.UK_NOMINEE in f.metrics["assessment"]
    k2 = Kit()
    entry = k2.company("uksl-gT0000005", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k2.sanction(entry, "gb_fcdo_sanctions")  # the list entry records no provisions
    m = k2.company("m")
    k2.owns(entry, m, "75-100")
    g = _run(k2)[m]
    assert _tests(g) == (NONE, OPEN, NONE) and g.metrics["uk_measures_unknown"] is True
    assert se.UK_UNKNOWN in g.metrics["assessment"]


def test_the_assessment_names_control_left_unassessed_and_eu_criteria():
    k = Kit()
    uk = k.company("uksl-gT0000006", topics=("sanction",), dataset="gb_fcdo_sanctions")
    k.sanction(uk, "gb_fcdo_sanctions", provisions=("Asset freeze",))
    eu = k.company("eufsf-T0000002", topics=("sanction",), dataset="eu_fsf")
    k.sanction(eu, "eu_fsf")
    d, e = k.company("d"), k.company("e")
    k.controls(uk, d, "influence")
    k.controls(eu, e, "appointment")
    found = _run(k)
    text_d, text_e = found[d].metrics["assessment"], found[e].metrics["assessment"]
    assert se.UK_CONTROL.format(list="the UK Sanctions List") in text_d
    assert "EU control criterion (a)" in text_e and found[e].metrics["lists_text"] == (
        "the EU consolidated list"
    )
    assert _tests(found[e]) == (NONE, NONE, NONE)  # no ownership test applies, yet it is reported


def test_the_stricter_option_withholds_registry_alerts_about_real_organisations():
    from kit import WINDOW, source_of
    from neonradar_detect import catalog, runner

    k = Kit()
    real_co = k.company("gbch-co-T0000002", "Test Holding Ltd", real=True)
    k.owns(_listed(k, "lst", person=False), real_co, "75-100")
    result = runner.run_detection(
        source_of(k.records),
        {"sanctions_exposure": se.Params()},
        WINDOW,
        catalog.load(),
        run_id="run-20261102T090000-0002",
        created_at=WINDOW.end,
        real_registry_alerts=False,
    )
    assert result.alerts == [] and result.summary["withheld"]["registry_on_real"] == 1
