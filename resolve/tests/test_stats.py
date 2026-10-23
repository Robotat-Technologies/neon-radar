import pytest

from neonradar_resolve.stats import cohens_kappa, specific_agreement, wilson_interval


def test_worked_example():
    lo, hi = wilson_interval(180, 200)
    assert (round(lo, 4), round(hi, 4)) == (0.8506, 0.9343)


def test_edges():
    assert wilson_interval(0, 10)[0] == 0.0
    assert wilson_interval(10, 10)[1] == 1.0
    low, _ = wilson_interval(10, 10)
    assert round(low, 4) == 0.7225
    with pytest.raises(ValueError):
        wilson_interval(3, 0)


def test_unsure_bound():
    # 400 drawn: 330 same, 10 different, 60 unsure (7.3 rule 3). The headline excludes unsure;
    # the bound counts every unsure pair as wrong.
    assert [round(x, 4) for x in wilson_interval(330, 340)] == [0.9467, 0.9839]
    assert [round(x, 4) for x in wilson_interval(330, 400)] == [0.7847, 0.8591]


def test_kappa():
    a = ["same"] * 40 + ["different"] * 10
    b = ["same"] * 38 + ["different"] * 2 + ["different"] * 8 + ["same"] * 2
    assert round(cohens_kappa(a, b), 4) == 0.75
    assert cohens_kappa(["same"] * 5, ["same"] * 5) == 1.0


def test_high_agreement_low_kappa():
    # 48 pairs both "same", one split each way: 96 percent agreement, kappa below zero.
    a = ["same"] * 49 + ["different"]
    b = ["same"] * 48 + ["different", "same"]
    assert round(cohens_kappa(a, b), 4) == -0.0204
    agreement = specific_agreement(a, b)
    assert round(agreement.positive or 0, 4) == 0.9796
    assert agreement.negative == 0.0
    assert agreement.excluded == 0


def test_specific_agreement_leaves_out_unsure():
    first = ["same", "same", "unsure", "different"]
    second = ["same", "unsure", "different", "different"]
    assert specific_agreement(first, second) == (1.0, 1.0, 2)
    assert specific_agreement(["unsure"], ["same"]) == (None, None, 1)
    with pytest.raises(ValueError):
        specific_agreement(["same"], [])
