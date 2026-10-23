import pytest
from neonradar_detect.evaluation.match import AlertView, ScenarioView, evaluate, iou
from neonradar_detect.evaluation.metrics import figures, macro, rate, t_interval
from neonradar_detect.evaluation.stats import wilson_interval


def _a(aid, typ, edges=(), nodes=(), subjects=None):
    return AlertView(aid, typ, frozenset(edges), frozenset(nodes), subjects or {})


def _s(sid, typ, tx=(), parts=None, look=False):
    return ScenarioView(sid, typ, look, frozenset(tx), parts or {})


def test_wilson_and_t():
    assert [round(x, 4) for x in wilson_interval(180, 200)] == [0.8506, 0.9343]
    lo, hi = wilson_interval(92, 100)
    assert (round(lo, 3), round(hi, 3)) == (0.850, 0.959)
    t = t_interval([1.0, 0.9, 1.0, 0.8, 0.9, 1.0, 0.9, 0.9, 1.0, 0.8])
    assert (round(t[0], 3), round(t[1], 3)) == (0.864, 0.976)
    r = rate(
        [
            (10, 10),
            (9, 10),
            (10, 10),
            (8, 10),
            (9, 10),
            (10, 10),
            (9, 10),
            (9, 10),
            (10, 10),
            (8, 10),
        ]
    )
    assert r.k == 92 and r.headline == r.across_seeds  # the t interval is wider here
    assert rate([(0, 0)]).value is None and rate([(0, 0)]).headline is None


def test_payment_matching_counts_every_kind():
    pay = frozenset({f"p{i}" for i in range(40)})
    scenarios = [
        _s("s1", "circular_flow", ["p0", "p1", "p2", "p3"]),
        _s("s2", "circular_flow", ["p10", "p11", "p12"]),
        _s("s3", "circular_flow", ["p20", "p21"], look=True),
        _s("s4", "circular_flow", ["p30", "p31", "p32", "p33"]),
    ]
    alerts = [
        _a(
            "a1", "circular_flow", ["p0", "p1", "p2", "p3", "acct-x"]
        ),  # exact on s1 (non-PAID ids ignored)
        _a("a2", "circular_flow", ["p0", "p1", "p2"]),  # also s1: duplicate
        _a("a3", "circular_flow", ["p20", "p21"]),  # look-alike
        _a("a4", "circular_flow", ["p38", "p39"]),  # background
        _a("a5", "circular_flow", ["p30"]),  # IoU 0.25 with s4: not a match, partial
        _a("a6", "circular_flow", ["p35", "p36"]),  # a layering chain's payments: other
        _a("b1", "layering_chain", ["p10", "p11", "p12"]),  # other typology: ignored here
    ]
    scenarios.append(_s("t1", "layering_chain", ["p35", "p36", "p37"]))
    out = evaluate("circular_flow", alerts, scenarios, pay)
    assert (
        out.alerts,
        out.true,
        out.duplicate,
        out.lookalike,
        out.partial,
        out.other,
        out.background,
    ) == (6, 1, 1, 1, 1, 1, 1)
    assert (out.planted, out.detected, out.lookalikes, out.lookalikes_alerted) == (3, 1, 1, 1)
    assert out.kinds == {
        "a1": "true",
        "a2": "duplicate",
        "a3": "lookalike",
        "a4": "background",
        "a5": "partial",
        "a6": "other",
    }
    assert (out.labelled_payments, out.covered_payments) == (11, 4)
    assert iou({"a"}, {"a", "b"}) == 0.5


def test_best_overlap_wins_and_ties_break_by_id():
    pay = frozenset({"p1", "p2", "p3", "p4"})
    scenarios = [_s("s1", "structuring", ["p1", "p2", "p3", "p4"])]
    alerts = [
        _a("a2", "structuring", ["p1", "p2", "p3", "p4"]),
        _a("a1", "structuring", ["p1", "p2", "p3", "p4"]),
    ]
    out = evaluate("structuring", alerts, scenarios, pay)
    assert out.matches == {"a1": "s1"} and out.kinds["a2"] == "duplicate"


def test_chain_exposure_and_hub_kinds():
    chain = _s(
        "c1",
        "shell_chain",
        parts={"co1": "owned_company", "co2": "layer", "co3": "layer", "p1": "top_owner"},
    )
    out = evaluate(
        "shell_chain", [_a("x", "shell_chain", nodes=["co1", "co2", "co3"])], [chain], frozenset()
    )
    assert out.true == 1  # IoU 3/4
    exp = _s("e1", "sanctions_exposure", parts={"t": "exposed_entity", "s": "listed_owner"})
    ok = _a("y", "sanctions_exposure", nodes=["t", "s", "m"], subjects={"t": "exposed_entity"})
    miss = _a("z", "sanctions_exposure", nodes=["t", "m"], subjects={"t": "exposed_entity"})
    assert evaluate("sanctions_exposure", [ok], [exp], frozenset()).true == 1
    assert evaluate("sanctions_exposure", [miss], [exp], frozenset()).background == 1
    chain_exp = ScenarioView(
        "e2",
        "sanctions_exposure",
        False,
        frozenset(),
        {"t": "exposed_entity", "mid": "exposed_entity", "s": "listed_owner"},
        frozenset({"t", "s"}),
    )
    two = [
        _a("y1", "sanctions_exposure", nodes=["t", "s", "mid"], subjects={"t": "exposed_entity"}),
        _a("y2", "sanctions_exposure", nodes=["mid", "s"], subjects={"mid": "exposed_entity"}),
    ]
    out = evaluate("sanctions_exposure", two, [chain_exp], frozenset())
    assert (out.true, out.duplicate, out.detected) == (
        2,
        0,
        1,
    )  # each exposed organisation is a unit
    only_mid = evaluate("sanctions_exposure", two[1:], [chain_exp], frozenset())
    assert (only_mid.true, only_mid.detected) == (1, 0)  # the core unit was missed
    hub = _s("h1", "mass_registration_address", parts={"addr": "registered_address"})
    out = evaluate(
        "mass_registration_address",
        [_a("w", "mass_registration_address", subjects={"addr": "registered_address"})],
        [hub],
        frozenset(),
    )
    assert out.true == 1 and out.detected == 1


def test_figures_and_macro():
    from neonradar_detect.evaluation.match import Outcome

    per_seed = {
        1: {"structuring": Outcome("structuring", alerts=12, true=9, planted=10, detected=9)},
        2: {"structuring": Outcome("structuring", alerts=0, true=0, planted=10, detected=0)},
    }
    f = figures(per_seed, "structuring")
    assert f.recall.k == 9 and f.recall.n == 20 and f.precision.seeds_counted == 1
    assert f.seed_recall == (0.0, 0.45, 0.9)
    m = macro([f])
    assert m["macro_recall"] == pytest.approx(0.45) and m["macro_f1"] == pytest.approx(
        2 * 0.45 * 0.75 / 1.2
    )
