"""`neonradar gate check` (M1.12): tmp folders and a fake runner, so no gh, Docker or network."""

import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from neonradar_cli import gate
from neonradar_cli.gate import Context, Result, Status
from neonradar_cli.main import app

FAIL, MANUAL, PASS = Status.FAIL, Status.MANUAL, Status.PASS
TYPOLOGY_FIXTURE = Path(__file__).resolve().parents[2] / "detect/tests/fixtures/typologies"
Answer = Result | Callable[..., Result]


class FakeRun:
    """Answers a command by the first key found in its command line (default: exit 0)."""

    def __init__(self, answers: dict[str, Answer] | None = None) -> None:
        self.answers = answers or {}

    def __call__(self, *args: str, timeout: float = 120) -> Result:
        line = " ".join(args)
        answer = next((a for key, a in self.answers.items() if key in line), Result(0))
        return answer if isinstance(answer, Result) else answer(*args)


def ctx(
    root: Path, answers: dict[str, Answer] | None = None, gh: bool = False, docker: bool = False
) -> Context:
    no_gh, no_docker = None if gh else "gh is not installed", None if docker else "no Docker"
    return Context(root, FakeRun(answers), no_gh, no_docker)


def write(root: Path, path: str, text: str = "x\n") -> None:
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def test_every_section_8_check_in_order() -> None:
    assert [check[0] for check in gate.CHECKS] == [f"GC-{n:02}" for n in range(1, 18)]
    blocking = [check[0] for check in gate.CHECKS if check[2]]  # section 8 "Blocks the freeze"
    assert blocking == ["GC-01", "GC-02", "GC-03", "GC-04", "GC-17"]


def test_run_in(tmp_path: Path) -> None:
    run = gate.run_in(tmp_path)
    cwd = run(sys.executable, "-c", "import os; print(os.getcwd())")
    assert Path(cwd.out.strip()).resolve() == tmp_path.resolve()
    assert run("neonradar-no-such-command").code == 127
    assert run(sys.executable, "-c", "import time; time.sleep(5)", timeout=0.1).code == 124


def test_make_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate.doctor, "docker_info", lambda: None)
    monkeypatch.setattr(gate, "run_in", lambda root: FakeRun({"auth status": Result(1)}))
    context = gate.make_context(tmp_path)
    assert (context.no_gh, context.no_docker) == ("gh is not signed in", "Docker is not reachable")
    monkeypatch.setattr(gate.doctor, "docker_info", lambda: pytest.fail("Docker called"))
    monkeypatch.setattr(gate, "run_in", lambda root: FakeRun({"gh": lambda *a: pytest.fail()}))
    context = gate.make_context(tmp_path, offline=True)
    assert context.no_gh == "gh not used (--offline)"
    assert context.no_docker == "Docker not used (--offline)"


SECTIONS = "".join(f"### {name}: x\n\n- y\n\n" for name in ("C1", "C2", "C3", "C4"))
CHANGELOG = f"# Contracts\n\n## 1.0.0 (unreleased)\n\n{SECTIONS}## 0.9.0\n\n### C3: old\n\n- z\n"


def test_changelog_gaps() -> None:
    assert gate.changelog_gaps(CHANGELOG) == []
    assert gate.changelog_gaps(CHANGELOG.replace("### C3: x\n\n- y", "### C3: x\n\nz")) == ["C3"]
    assert gate.changelog_gaps("## 0.9.0\n\n### C1: x\n\n- y\n") == ["C1", "C2", "C3", "C4"]


def test_contract_suite(tmp_path: Path) -> None:
    write(tmp_path, "contracts/CHANGELOG.md", CHANGELOG)
    passing = ctx(tmp_path, {"make contracts-check": Result(0, "x\nOK, 3 generated files\n")})
    assert gate.contract_suite(passing) == (
        PASS,
        "contracts/CHANGELOG.md 1.0.0 has C1 to C4; make contracts-check: OK, 3 generated files",
    )
    failing = ctx(tmp_path, {"make contracts-check": Result(2, "== 1 failed ==\n")})
    assert gate.contract_suite(failing)[1].startswith("make contracts-check: == 1 failed ==; ")
    write(tmp_path, "contracts/CHANGELOG.md", CHANGELOG.replace("### C3: x", "### X"))
    assert gate.contract_suite(ctx(tmp_path))[1].startswith("contracts/CHANGELOG.md 1.0.0 lacks C3")


MIGRATION = "".join(f"CREATE CONSTRAINT c{n} IF NOT EXISTS ...;\n" for n in range(22)) + "".join(
    f"CREATE {kind}INDEX i{n} IF NOT EXISTS ...;\n" for n, kind in enumerate(["", "FULLTEXT "] * 3)
)


def test_graph_schema(tmp_path: Path) -> None:
    write(tmp_path, gate.MIGRATION, MIGRATION + "-- CREATE INDEX commented out\n")
    assert gate.graph_schema(ctx(tmp_path, docker=True))[0] is FAIL  # 6 indexes
    write(tmp_path, gate.MIGRATION, MIGRATION + "CREATE INDEX i7 IF NOT EXISTS ...;\n")
    status, evidence = gate.graph_schema(ctx(tmp_path))
    assert status is MANUAL and evidence.endswith(
        "not applied: no Docker; make test-int applies it"
    )
    no_jar = ctx(tmp_path, {"fetch_gds.sh": Result(1)}, docker=True)
    assert gate.graph_schema(no_jar)[0] is MANUAL
    applied = ctx(tmp_path, {"pytest": Result(0, "3 passed in 41.2s\n")}, docker=True)
    assert gate.graph_schema(applied) == (
        PASS,
        f"{gate.MIGRATION} declares 22 constraints and 7 indexes; pytest -m integration "
        "graph/tests/test_migrations.py: 3 passed in 41.2s",
    )
    assert gate.graph_schema(ctx(tmp_path, {"pytest": Result(1)}, docker=True))[0] is FAIL


RUN = '[{"status": "%s", "conclusion": "%s", "headSha": "66a5d8e4", "url": "https://x.invalid"}]'


@pytest.mark.parametrize(
    ("answer", "status"),
    [
        (Result(0, RUN % ("completed", "success")), PASS),
        (Result(0, RUN % ("completed", "failure")), FAIL),
        (Result(0, RUN % ("in_progress", "")), MANUAL),
        (Result(0, "[]"), FAIL),
        (Result(1, "", "HTTP 502"), MANUAL),
    ],
)
def test_ci_green(tmp_path: Path, answer: Result, status: Status) -> None:
    assert (
        gate.ci_green(ctx(tmp_path, {"run list --workflow ci.yml": answer}, gh=True))[0] is status
    )


def test_runs_need_gh_and_the_e2e_workflow(tmp_path: Path) -> None:
    assert gate.ci_green(ctx(tmp_path)) == (
        MANUAL,
        "gh is not installed; check the latest ci run on main",
    )
    success = {"run list --workflow e2e.yml": Result(0, RUN % ("completed", "success"))}
    assert gate.walking_skeleton(ctx(tmp_path, success, gh=True)) == (
        FAIL,
        "no .github/workflows/e2e.yml and no make demo-mini (pending M1.9e)",
    )
    write(tmp_path, ".github/workflows/e2e.yml")
    assert gate.walking_skeleton(ctx(tmp_path, success, gh=True))[0] is PASS
    assert gate.walking_skeleton(ctx(tmp_path))[0] is MANUAL


def test_repository_basics(tmp_path: Path) -> None:
    for path in gate.GOVERNANCE:
        write(tmp_path, path)
    write(tmp_path, ".github/labels.yml", "- {name: agent}\n- {name: phase-1}\n")
    assert gate.repository_basics(ctx(tmp_path))[0] is MANUAL  # labels need gh
    both = {"label list": Result(0, '[{"name": "agent"}, {"name": "phase-1"}]')}
    assert gate.repository_basics(ctx(tmp_path, both, gh=True))[0] is PASS
    one = {"label list": Result(0, '[{"name": "agent"}]')}
    assert "labels not on GitHub: phase-1" in gate.repository_basics(ctx(tmp_path, one, gh=True))[1]
    (tmp_path / "SECURITY.md").unlink()
    stale = {"generate_codeowners.py --check": Result(1, "", ".github/CODEOWNERS is out of date.")}
    status, evidence = gate.repository_basics(ctx(tmp_path, stale))
    assert status is FAIL
    assert evidence.startswith("missing SECURITY.md; generate_codeowners.py --check: .github/CODE")
    assert "31 of 32 M1.1 governance files" in evidence


def test_protection(tmp_path: Path) -> None:
    assert gate.protection(ctx(tmp_path))[0] is FAIL
    write(tmp_path, "docs/build/ci.md", "# CI\n\n## Plan limitation and interim controls\n")
    assert gate.protection(ctx(tmp_path))[0] is PASS
    denied = {"protection": Result(1, '{"status": "403"}', "gh: Upgrade (HTTP 403)\n")}
    assert gate.protection(ctx(tmp_path, denied, gh=True)) == (
        PASS,
        "protection API: gh: Upgrade (HTTP 403); "
        "docs/build/ci.md records the limitation and controls",
    )
    (tmp_path / "docs/build/ci.md").unlink()
    assert gate.protection(ctx(tmp_path, gh=True))[0] is PASS  # the API answered


def test_devcontainer(tmp_path: Path) -> None:
    assert gate.devcontainer(ctx(tmp_path))[0] is FAIL
    write(tmp_path, ".devcontainer/devcontainer.json", "{}")
    assert gate.devcontainer(ctx(tmp_path))[0] is MANUAL


def report(verdict: str) -> str:
    return f"# Spike\n\n| Verdict | **{verdict}** |\n\n## 7. Verdict\n\n**{verdict}.** Why.\n"


def test_spikes(tmp_path: Path) -> None:
    verdicts = ("Go", "Go", "Go with changes", "Blocked on licence decision")
    for source, verdict in zip(gate.SPIKES, verdicts, strict=True):
        write(tmp_path, f"docs/data/spikes/{source}.md", report(verdict))
    assert gate.spikes(ctx(tmp_path)) == (
        PASS,
        "companies-house: Go; gleif: Go; icij: Go with changes; "
        "opensanctions: Blocked on licence decision",
    )
    write(tmp_path, "docs/data/spikes/companies-house.md", report("Pending network run (no key)"))
    write(tmp_path, "docs/data/spikes/icij.md", report("Blocked on licence decision"))
    (tmp_path / "docs/data/spikes/gleif.md").unlink()
    assert gate.spikes(ctx(tmp_path)) == (
        FAIL,
        "companies-house: verdict 'Pending network run (no key)' (pending M1.8a); "
        "gleif: no report (pending M1.8b); "
        "icij: verdict 'Blocked on licence decision' (pending M1.8c); "
        "opensanctions: Blocked on licence decision",
    )


def test_synthetic_join(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert gate.synthetic_join(ctx(tmp_path)) == (
        FAIL,
        "no data/fixtures/demo-mini/*.ftm.jsonl (pending M1.8e)",
    )
    from neonradar_contracts import records

    monkeypatch.setattr(records, "validate_files", lambda files, strict: (Counter(Company=3), []))
    demo = {"nr_synthetic-20261023-demo-mini.ftm.jsonl": "{}\n", "labels/transactions.csv": "a\n"}
    for name, text in demo.items():
        write(tmp_path / gate.DEMO_MINI, name, text)

    def synth(*args: str) -> Result:  # writes what `neonradar synth demo-mini --out <dir>` would
        for name, text in demo.items():
            write(Path(args[args.index("--out") + 1]), name, text)
        return Result(0)

    facts = "demo-mini: 3 records, strict OK, regenerates byte-identically"
    assert gate.synthetic_join(ctx(tmp_path, {"synth demo-mini": synth}))[1].startswith(facts)
    pr = {"pr list": Result(0, '[{"number": 31, "body": "neonradar spike synthetic-join: 9"}]')}
    assert gate.synthetic_join(ctx(tmp_path, {"synth demo-mini": synth, **pr}, gh=True)) == (
        PASS,
        f"{facts}; PR #31 shows the synthetic-join output",
    )
    write(tmp_path / gate.DEMO_MINI, "labels/transactions.csv", "b\n")
    assert gate.synthetic_join(ctx(tmp_path, {"synth demo-mini": synth})) == (
        FAIL,
        "synth demo-mini --seed 20261023: labels/transactions.csv differ",
    )


def typologies(root: Path, approved: bool) -> None:
    """15 valid typology files and explainers made from the detect fixture."""
    data = yaml.safe_load((TYPOLOGY_FIXTURE / "circular_flow.yaml").read_text(encoding="utf-8"))
    for slug in ["circular_flow", *(f"pattern_{n}" for n in range(1, 15))]:
        doc = f"docs/typologies/{slug.replace('_', '-')}.md"
        sign_off = {"status": "approved", "approved_by": "@researcher"} if approved else {}
        typology = {**data, "slug": slug, "doc": doc, **sign_off}
        write(root, f"detect/typologies/{slug}.yaml", yaml.safe_dump(typology))
        write(root, doc)


def test_knowledge_base(tmp_path: Path) -> None:
    write(tmp_path, "docs/sources/bibliography.yaml", "entries:\n  - key: fatf_glossary\n")
    typologies(tmp_path, approved=False)
    assert gate.knowledge_base(ctx(tmp_path)) == (
        FAIL,
        "circular_flow is draft (a typology researcher approves it, OD-5); bibliography: 1 "
        "entries; check_citations.py passes; 15 typology files and 15 explainers of 15",
    )
    typologies(tmp_path, approved=True)
    assert gate.knowledge_base(ctx(tmp_path))[0] is PASS
    (tmp_path / "docs/typologies/pattern-3.md").unlink()
    status, evidence = gate.knowledge_base(
        ctx(tmp_path, {"check_citations": Result(1, "", "bad key")})
    )
    assert status is FAIL
    assert evidence.startswith("check_citations.py: bad key; 15 typology files and 14 explainers")


def test_intern_checks_are_not_met_without_interns(tmp_path: Path) -> None:
    write(tmp_path, "docs/build/project.yaml", "people:\n  interns: []\n")
    for check in (gate.interns_merged, gate.learning_logs, gate.assignment_2):
        status, evidence = check(ctx(tmp_path, gh=True))
        assert status is FAIL and evidence.startswith(gate.NOT_MET)


def test_intern_checks(tmp_path: Path) -> None:
    write(tmp_path, "docs/build/project.yaml", 'people:\n  interns: ["@ada", "@bo"]\n')
    write(tmp_path, "docs/learning/ada.md", "## Log\n\n### Week of 2026-10-19\n\n- Read: C1\n")
    write(tmp_path, "docs/learning/bo.md", "## Log\n\n<!--\n### Week of YYYY-MM-DD\n-->\n")
    assert gate.learning_logs(ctx(tmp_path)) == (
        FAIL,
        "no learning log with a dated entry for @bo; 1 of 2 interns have a docs/learning/ entry",
    )
    merged = {"--author ada": Result(0, '[{"number": 3}]'), "--author bo": Result(0, "[]")}
    assert gate.interns_merged(ctx(tmp_path, merged, gh=True))[1].startswith("no merged pull re")
    merged["--author bo"] = Result(0, '[{"number": 4}]')
    assert gate.interns_merged(ctx(tmp_path, merged, gh=True))[0] is PASS
    assert gate.interns_merged(ctx(tmp_path))[0] is MANUAL
    assert gate.assignment_2(ctx(tmp_path))[0] is FAIL  # no assignment-2.md yet
    write(tmp_path, "docs/team/assignment-2.md")
    assert gate.assignment_2(ctx(tmp_path))[0] is MANUAL


def adr(root: Path, number: str, status: str) -> None:
    write(
        root, f"docs/decisions/{number}-title.md", f"# {number}. Title\n\n- **Status:** {status}\n"
    )


def test_adrs(tmp_path: Path) -> None:
    for number, (status, _) in gate.ADRS.items():
        adr(tmp_path, number, status)
    assert gate.adrs(ctx(tmp_path, {"git log": Result(0, "Ada Decider\n")})) == (
        MANUAL,
        "status lines match 7.6; accepting commits by Ada Decider; "
        "confirm each accepting commit is by the ADR's deciders",
    )
    (tmp_path / "docs/decisions/0005-title.md").unlink()
    for number, status in (("0001", "proposed"), ("0002", "proposed"), ("0010", "accepted")):
        adr(tmp_path, number, status)
    assert gate.adrs(ctx(tmp_path)) == (
        FAIL,
        "missing 0005 (pending M1.8e); proposed, 7.6 says accepted (the deciders accept ADRs, "
        "OD-5): 0001, 0002; accepted, 7.6 says proposed: 0010",
    )


def test_legal_note(tmp_path: Path) -> None:
    write(tmp_path, "docs/build/PROGRESS.md", "| M1.12 | todo | legal and communications |\n")
    assert gate.legal_note(ctx(tmp_path))[0] is FAIL  # a milestone row is not the note
    write(tmp_path, "docs/build/PROGRESS.md", "# Progress\n\nLegal and communications: started.\n")
    assert gate.legal_note(ctx(tmp_path)) == (
        MANUAL,
        "note at docs/build/PROGRESS.md:3; the project lead confirms the conversation started",
    )


def test_phase_report(tmp_path: Path) -> None:
    assert gate.phase_report(ctx(tmp_path)) == (FAIL, f"no {gate.REPORT} (pending M1.12-2)")
    write(tmp_path, gate.REPORT, "# Phase 1 report\n\n## Metrics\n\n## Deviations\n")
    assert gate.phase_report(ctx(tmp_path))[1].endswith("has no heading for: risk, phase 2")
    write(
        tmp_path, gate.REPORT, "# Report\n## Metrics\n## Deviations\n## Risks\n## Phase 2 inputs\n"
    )
    assert gate.phase_report(ctx(tmp_path))[0] is PASS


def test_licence_fields_need_a_person(tmp_path: Path) -> None:
    missing = (FAIL, "missing contracts/datasets.yaml, DATA_SOURCES.md")
    assert gate.licence_fields(ctx(tmp_path)) == missing
    write(tmp_path, "contracts/datasets.yaml")
    write(tmp_path, "DATA_SOURCES.md")
    status, evidence = gate.licence_fields(ctx(tmp_path, {"git log": Result(0, "5fa31d6\n")}))
    assert status is MANUAL
    assert evidence.startswith("contracts/datasets.yaml last changed in 5fa31d6; DATA_SOURCES.md")


def test_a_raising_check_fails_and_the_others_still_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(context: Context) -> gate.Outcome:
        raise ValueError("bad file")

    checks = [("GC-01", "One", True, broken), ("GC-07", "Two", False, gate.devcontainer)]
    monkeypatch.setattr(gate, "CHECKS", checks)
    found = list(gate.run_checks(ctx(tmp_path)))
    assert [check.line() for check in found] == [
        "GC-01 FAIL   One: the check raised ValueError: bad file",
        "GC-07 FAIL   Two: no .devcontainer/devcontainer.json (pending M1.5)",
    ]
    assert gate.summary(found) == "Gate 1: 0 PASS, 2 FAIL, 0 MANUAL. Freeze checks: GC-01 FAIL"


def test_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "make_context", lambda root, offline: ctx(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["gate", "check", "--phase", "1"])
    lines = result.output.splitlines()
    assert result.exit_code == 1, result.output
    assert [line[:6] for line in lines[1:-1]] == [f"GC-{n:02} " for n in range(1, 18)]
    assert lines[-1].startswith("Gate 1: ")
    assert runner.invoke(app, ["gate", "check", "--report-only"]).exit_code == 0
    result = runner.invoke(app, ["gate", "check", "--phase", "2"])
    assert result.exit_code == 2 and "only phase 1" in result.output
