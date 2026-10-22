"""Labels, adjudication and the precision report (PHASE-2.md 7.3, M2.10c deliverables 5, 7 and
8). Every label here is a synthetic test label on a synthetic sample built in the test (G10)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from neonradar_cli import er_labelling
from neonradar_cli.main import app
from neonradar_contracts.datasets import load_registry
from neonradar_ingest.data import layout
from neonradar_ingest.data.project import load_project
from neonradar_resolve import labels, precision, sample
from neonradar_resolve.labels import Label, LabelsError
from neonradar_resolve.sample import Pair
from neonradar_resolve.stats import cohens_kappa, specific_agreement, wilson_interval

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
TECH_LEAD = "@example-lead"
runner = CliRunner()
ID_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(sorted({d.id_prefix for d in load_registry().datasets} | {"nr"}))
    + r")-[A-Za-z0-9]"
)


def _pair(n: int, stratum: str, labellers: tuple[str, ...], rule: str | None = None) -> Pair:
    a, b = f"syn-r-{n:04d}", f"syn-x-{n:04d}"
    return Pair(f"pair-{n:04d}", stratum, a, b, labellers, len(labellers) == 2, rule)


def _label(pair: str, label: str, by: str, minutes: int, adjudication: bool = False) -> Label:
    return Label(pair, label, by, T0 + timedelta(minutes=minutes), adjudication)


def test_labels_from_three_handles_and_one_adjudication_combine() -> None:
    pairs = [
        _pair(1, "S1", ("@a",)),
        _pair(2, "S1", ("@a", "@b")),
        _pair(3, "S1", ("@b", "@c")),
        _pair(4, "S3", ("@c", "@a")),
        _pair(5, "S2", ("@c",), "D3"),
        _pair(6, "S2", ("@a",), "D1"),
        _pair(7, "S1", ("@b",)),
    ]
    found = [
        _label("pair-0001", "same", "@a", 1),
        _label("pair-0001", "different", "@b", 2),  # @b is not assigned to pair 1: not counted
        _label("pair-0002", "same", "@a", 3),
        _label("pair-0002", "same", "@b", 4),
        _label("pair-0003", "same", "@b", 5),
        _label("pair-0003", "different", "@c", 6),
        _label("pair-0003", "different", "@a", 7, adjudication=True),  # @a labelled neither
        _label("pair-0004", "unsure", "@c", 8),
        _label("pair-0004", "same", "@a", 9),
        _label("pair-0004", "same", TECH_LEAD, 10, adjudication=True),  # set the thresholds
        _label("pair-0004", "same", "@c", 11, adjudication=True),  # labelled the pair
        _label("pair-0005", "different", "@c", 12),
        _label("pair-0006", "different", "@a", 13),
        _label("pair-0006", "same", "@a", 14),  # the newest answer counts
    ]
    outcome = precision.measure(pairs, found, {TECH_LEAD})
    assert outcome.final == {
        "pair-0001": "same",
        "pair-0002": "same",
        "pair-0003": "different",
        "pair-0004": None,  # still waits for an eligible adjudicator
        "pair-0005": "different",
        "pair-0006": "same",
        "pair-0007": None,
    }
    assert outcome.strata["S1"] == precision.Figure(2, 3, 0)
    assert outcome.strata["S2"] == precision.Figure(1, 2, 0)
    assert outcome.strata["S3"] == precision.Figure(0, 0, 0)
    assert outcome.by_rule["D1"] == precision.Figure(1, 1, 0)
    assert outcome.by_rule["D3"] == precision.Figure(0, 1, 0)
    assert (outcome.unlabelled, outcome.awaiting_adjudication) == (1, 1)
    assert outcome.ignored == 3  # @b's label of pair 1 and two refused adjudications
    assert outcome.labellers == 3 and outcome.adjudicators == {"@a"}
    assert outcome.agreement.pairs == 3 and outcome.agreement.by_stratum == {"S1": 2, "S3": 1}


def test_adjudicators_never_set_the_thresholds_nor_labelled_the_pair(data_env: Any) -> None:
    pairs = [_pair(1, "S1", ("@a", "@b")), _pair(2, "S3", ("@c", "@d"))]
    found = [
        _label("pair-0001", "same", "@a", 1),
        _label("pair-0001", "different", "@b", 2),
        _label("pair-0002", "same", "@c", 3),
        _label("pair-0002", "unsure", "@d", 4),
    ]
    assert labels.disagreements(pairs, found) == pairs
    assert labels.adjudication_queue(pairs, found, "@a", {TECH_LEAD}) == ([pairs[1]], 1)
    assert labels.adjudication_queue(pairs, found, "@e", {TECH_LEAD}) == (pairs, 0)
    assert not labels.eligible_adjudicator(pairs[0], TECH_LEAD, {TECH_LEAD})
    adjudicated = [*found, _label("pair-0001", "same", "@e", 5, adjudication=True)]
    assert labels.adjudication_queue(pairs, adjudicated, "@a", {TECH_LEAD}) == ([pairs[1]], 0)
    # the barred handles come from people.tech_lead and squads.graph.mentor
    data_env.project.write_text(
        yaml.safe_dump(
            {
                "people": {"tech_lead": "@Example-Lead", "project_lead": "@example-pl"},
                "squads": {"graph": {"mentor": "@example-mentor"}, "ui": {"mentor": "@x"}},
            }
        ),
        encoding="utf-8",
    )
    assert er_labelling._barred(load_project()) == {TECH_LEAD, "@example-mentor"}


def test_er_label_adjudicate_refuses_the_tech_lead_and_anyone_who_labelled_the_pair() -> None:
    with pytest.raises(LabelsError, match="set the thresholds"):
        labels.check_adjudicator(TECH_LEAD, {TECH_LEAD}, None)
    with pytest.raises(LabelsError, match="project lead or in people"):
        labels.check_adjudicator("@e", {TECH_LEAD}, {"@f"})  # a real profile's list
    labels.check_adjudicator("@e", {TECH_LEAD}, None)
    pairs = [_pair(1, "S1", ("@a", "@b"))]
    found = [
        _label("pair-0001", "same", "@a", 1),
        _label("pair-0001", "different", "@b", 2),
        _label("pair-0001", "unsure", "@e", 3),  # not assigned, but labelled the pair
    ]
    assert not labels.eligible_adjudicator(pairs[0], "@e", {TECH_LEAD}, found)
    assert labels.adjudication_queue(pairs, found, "@e", {TECH_LEAD}) == ([], 1)
    late = [*found, _label("pair-0001", "same", "@e", 4, adjudication=True)]
    assert precision.final_label(pairs[0], late, {TECH_LEAD})[1] == "awaiting adjudication"
    by_f = [*found[:2], _label("pair-0001", "same", "@f", 4, adjudication=True)]
    assert precision.final_label(pairs[0], by_f, {TECH_LEAD})[0] == "same"
    # on a real profile only the project lead and people.er_labellers adjudicate
    assert precision.final_label(pairs[0], by_f, {TECH_LEAD}, {"@g"})[0] is None
    assert labels.adjudication_queue(pairs, by_f, "@g", {TECH_LEAD}, {"@g"}) == ([pairs[0]], 0)


def test_real_profile_commands_wait_until_people_are_named(data_env: Any) -> None:
    # OD-22: people.er_labellers and er_senior_reviewers hold @TODO until people join
    real, synthetic = SimpleNamespace(real_data=True), SimpleNamespace(real_data=False)

    def project(labellers: list[str], seniors: list[str]) -> Any:
        people = {"er_labellers": labellers, "er_senior_reviewers": seniors}
        data_env.project.write_text(yaml.safe_dump({"people": people}), encoding="utf-8")
        return load_project()

    todo = project(["@TODO", "@TODO"], ["@TODO"])
    assert er_labelling._team(todo, synthetic) == (frozenset(), frozenset())
    for refused in (todo, project(["@example-one", "@TODO"], []), project([], [])):
        with pytest.raises(er_labelling.Refused, match="OD-22"):
            er_labelling._team(refused, real)
    with pytest.raises(er_labelling.Refused):
        er_labelling._team(project(["@example-one"], ["@TODO"]), real)
    named = project(["@Example-One", "@example-two"], [])
    assert er_labelling._team(named, real) == ({"@example-one", "@example-two"}, frozenset())


def test_precision_and_the_unsure_bound_match_stats() -> None:
    # 400 drawn: 330 same, 10 different, 60 unsure (7.3 rule 3, test_stats.py)
    pairs = [_pair(n, "S1", ("@a",)) for n in range(1, 401)]
    answers = ["same"] * 330 + ["different"] * 10 + ["unsure"] * 60
    found = [_label(p.pair_id, x, "@a", 1) for p, x in zip(pairs, answers, strict=True)]
    s1 = precision.measure(pairs, found, set()).strata["S1"]
    assert (s1.k, s1.n, s1.u) == (330, 340, 60)
    assert s1.precision == 330 / 340
    assert s1.interval == wilson_interval(330, 340)
    assert s1.bound.precision == 330 / 400 and s1.bound.interval == wilson_interval(330, 400)
    assert s1.unsure_share == 60 / 400


def test_agreement_figures_match_stats() -> None:
    first = ["same"] * 40 + ["different"] * 10
    second = ["same"] * 38 + ["different"] * 2 + ["different"] * 8 + ["same"] * 2
    pairs = [_pair(n, "S1" if n <= 40 else "S3", ("@a", "@b")) for n in range(1, 51)]
    found = [_label(p.pair_id, x, "@a", 1) for p, x in zip(pairs, first, strict=True)]
    found += [_label(p.pair_id, x, "@b", 2) for p, x in zip(pairs, second, strict=True)]
    a = precision.measure(pairs, found, set()).agreement
    assert (a.pairs, a.by_stratum) == (50, {"S1": 40, "S3": 10})
    assert a.percent == 46 / 50
    assert a.kappa == cohens_kappa(first, second) and round(a.kappa or 0, 4) == 0.75
    assert a.share_same == 80 / 100
    expected = specific_agreement(first, second)
    assert (a.positive, a.negative, a.excluded) == tuple(expected)


def _report(outcome: precision.Outcome, real_data: bool = False) -> str:
    run_info = {
        "run_id": "er-20261102T090000-ab12",
        "resolver_version": "0.1.0",
        "config_sha256": "0" * 64,
        "decisions_used": False,
        "thresholds": {"merge_threshold": {"org": 0.995, "person": 0.99}},
        "counts": {"decisions_on_file": 4},
        "inputs": [
            {"dataset": "nr_synthetic"},
            {"dataset": "gb_companies_house"},
            {"dataset": "icij_offshore_leaks"},
        ],
    }
    drawn = {"run_id": run_info["run_id"], "seed": 7, "adr_seed": None, "human_joined": 2}
    drawn |= {"frames": {"s1": 600, "s2": 50, "s3": 120}}
    return precision.report(
        outcome,
        on=date(2026, 11, 3),
        profile="demo",
        real_data=real_data,
        run=run_info,
        sample=drawn,
        project_lead="@example-pl",
    )


def test_the_report_holds_counts_only_the_readme_sentence_and_the_footer() -> None:
    pairs = [_pair(n, "S1", ("@a", "@b") if n <= 40 else ("@a",)) for n in range(1, 401)]
    pairs += [_pair(n, "S2", ("@b",), f"D{n % 5 + 1}") for n in range(401, 451)]
    pairs += [_pair(n, "S3", ("@a", "@c") if n <= 460 else ("@c",)) for n in range(451, 501)]
    found = [_label(p.pair_id, "same", h, 1) for p in pairs for h in p.labellers]
    found[0] = _label(pairs[0].pair_id, "unsure", "@a", 1)
    found.append(_label(pairs[0].pair_id, "same", "@example-pl", 2, adjudication=True))
    outcome = precision.measure(pairs, found, {TECH_LEAD}, {"S1": False, "S2": True})
    text = _report(outcome)
    assert ID_PATTERN.search(text) is None, ID_PATTERN.search(text)
    for handle in ("@a", "@b", "@c", "@example-pl"):
        assert handle not in text
    assert text.startswith("# Entity resolution precision, demo, 2026-11-03\n")
    assert "Probabilistic merges (headline): 400 of 400 correct, precision 1.000" in text
    assert "Deterministic merges: 50 of 50 correct" in text and "D3 10 of 10" in text
    assert "Joined through a reviewer's decision: 2 records (not sampled)." in text
    assert "on 50 overlapping pairs (40 from S1, 10 from S3)" in text
    assert "Labelled whole (a census of this run, not a sample): S2" in text
    assert "(no decisions applied; 4 decisions on file)" in text
    assert "adjudicated by the project lead" in text
    assert (
        "On 2026-11-03, human labellers judged 400 of 400 sampled probabilistic merges on"
        " synthetic records (profile demo) correct (precision 1.000, Wilson 95% interval 0.990"
        " to 1.000; 0 unsure, excluded). Sanctions, PEP and ICIJ records are never merged by"
        " probability, so this does not measure screening accuracy."
    ) in text
    footer = text.rstrip("\n").splitlines()[-1]
    assert footer.startswith("Sources and licences: ")
    assert load_registry().get("gb_companies_house").attribution in footer  # type: ignore[union-attr]
    assert footer.endswith(precision.ICIJ_NOTICE)
    assert "Fewer" not in text and "More than 15 percent" not in text
    assert " on a slice of the UK register correct" in _report(outcome, real_data=True)


def test_the_first_line_warns_about_unsure_labels_and_a_small_sample() -> None:
    pairs = [_pair(n, "S1", ("@a",)) for n in range(1, 101)]
    found = [
        _label(p.pair_id, "unsure" if n < 20 else "same", "@a", 1) for n, p in enumerate(pairs)
    ]
    lines = _report(precision.measure(pairs, found, set())).splitlines()
    assert lines[2] == "More than 15 percent of the labelled S1 pairs were marked unsure (20.0%)."
    assert lines[3].startswith("Only 80 S1 labels other than unsure (250 planned)")


def test_label_files_append_and_read_back(tmp_path: Path) -> None:
    labels.append_label(tmp_path, "pair-0001", "same", "@Example-One", " a note ", at=T0)
    labels.append_label(tmp_path, "pair-0002", "unsure", "@example-one", at=T0)
    labels.append_label(tmp_path, "pair-0002", "same", "@example-two", adjudication=True, at=T0)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "@example-one.jsonl",
        "@example-two.jsonl",
    ]
    found = labels.read_labels(tmp_path)
    assert [(x.pair_id, x.label, x.by, x.adjudication) for x in found] == [
        ("pair-0001", "same", "@example-one", False),
        ("pair-0002", "unsure", "@example-one", False),
        ("pair-0002", "same", "@example-two", True),
    ]
    assert found[0].note == "a note" and found[1].note is None
    with pytest.raises(LabelsError, match="same, different or unsure"):
        labels.append_label(tmp_path, "pair-0003", "maybe", "@example-one")
    (tmp_path / "@example-three.jsonl").write_text(
        '{"pair_id": "pair-0001", "label": "same", "by": "@example-one",'
        ' "at": "2026-11-02T09:00:00Z", "adjudication": false}\n',
        encoding="utf-8",
    )
    with pytest.raises(LabelsError, match="not the file's"):
        labels.read_labels(tmp_path)


def test_next_pair_resumes_where_the_labeller_stopped() -> None:
    pairs = [_pair(1, "S1", ("@a",)), _pair(2, "S3", ("@b", "@a")), _pair(3, "S2", ("@a",))]
    assert labels.next_pair(pairs, [], "@a") == (1, pairs[0])
    done = [_label("pair-0001", "same", "@a", 1), _label("pair-0002", "unsure", "@b", 2)]
    assert labels.next_pair(pairs, done, "@a") == (2, pairs[1])
    done.append(_label("pair-0002", "different", "@a", 3))
    assert labels.next_pair(pairs, done, "@a") == (3, pairs[2])
    assert labels.next_pair(pairs, done, "@b") is None


def test_er_label_refuses_to_run_without_a_terminal(tmp_path: Path, data_env: Any) -> None:
    code = "from neonradar_cli.main import app; app()"
    command = [sys.executable, "-c", code, "er", "label", "--profile", "demo", "--run", "latest"]
    for extra in ([], ["--adjudicate"]):
        result = subprocess.run(  # noqa: S603 (this interpreter; stdin closed: not a terminal, G10)
            [*command, "--labeller", "@example-one", *extra],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            cwd=tmp_path,
            env={**os.environ, "NR_PROJECT_FILE": str(data_env.project)},
        )
        assert result.returncode == 2, result.stderr
        assert "er label is for a person at a terminal" in result.stderr


def test_er_precision_writes_the_report_from_synthetic_labels(data_env: Any) -> None:
    result = runner.invoke(app, ["er", "run", "--profile", "demo", "--no-probabilistic"])
    assert result.exit_code == 0, result.output
    args = ["--profile", "demo", "--run", "latest"]
    result = runner.invoke(app, ["er", "sample", *args, "--seed", "3", "--labellers", "@a,@b"])
    assert result.exit_code == 0, result.output
    run_id = layout.latest_run("demo")
    assert run_id is not None
    folder = layout.labels_dir("demo", run_id)
    pairs, _ = sample.read_sample(folder)
    for pair in pairs[:5]:  # synthetic test labels on the synthetic demo sample
        for who in pair.labellers:
            labels.append_label(folder, pair.pair_id, "same", who, at=T0)
    out = data_env.root / "report" / "precision-test.md"
    result = runner.invoke(app, ["er", "precision", *args, "--out", str(out)])
    assert result.exit_code == 0, result.output
    text = out.read_text(encoding="utf-8")
    assert ID_PATTERN.search(text) is None and ID_PATTERN.search(result.output) is None
    assert "Sources and licences: NeonRadar synthetic data: no attribution needed." in text
    assert f"Evaluation run {run_id} (decisions applied;" in text
    assert list(layout.reports_dir("demo").glob("er-precision-*.json"))
