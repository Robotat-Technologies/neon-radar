"""`neonradar gate check --phase 1`: gather the Gate 1 evidence (PHASE-1.md section 8, M1.12).

One line per check, GC-01 to GC-17, with PASS, FAIL or MANUAL and its evidence. The command only
reads: it runs tests, `--check` scripts, `git log` and read-only `gh` queries, and never creates a
tag, approves a typology or an ADR, or edits a file (operator decision OD-5). A check that needs
`gh` or Docker reports MANUAL with the reason when they are unavailable; MANUAL also marks what
only a person can confirm, in the Phase 1 report. With `people.interns` empty, GC-11 to GC-13
report not met (OD-6).
"""

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Protocol

import typer
import yaml

from neonradar_cli import doctor

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
NOT_MET = "people.interns is empty, so not met (OD-6; the operator decides at the gate)"


class Status(StrEnum):
    PASS = "PASS"  # noqa: S105 (a check status, not a password)
    FAIL = "FAIL"
    MANUAL = "MANUAL"


Outcome = tuple[Status, str]


@dataclass(frozen=True)
class Result:
    code: int
    out: str = ""
    err: str = ""

    @property
    def tail(self) -> str:
        """The last line of standard output, else of standard error: short evidence."""
        lines = (self.out.strip() or self.err.strip()).splitlines()
        return lines[-1].strip() if lines else f"exit {self.code}"


class Runner(Protocol):
    def __call__(
        self, *args: str, timeout: float = ..., env: Mapping[str, str] | None = ...
    ) -> Result: ...


def run_in(root: Path) -> Runner:
    """A runner for commands in `root`; a missing program gives exit 127, a timeout 124.

    Each command starts its own process group, and a timeout kills the whole group, so no
    `make`, `uv` or `pytest` child keeps running after the gate has moved on.
    """

    def run(*args: str, timeout: float = 120, env: Mapping[str, str] | None = None) -> Result:
        if shutil.which(args[0]) is None:
            return Result(127, err=f"{args[0]}: not found")
        try:
            # Fixed argument lists from this module, never shell strings or user input.
            pipe = subprocess.PIPE
            process = subprocess.Popen(  # noqa: S603
                args, cwd=root, env=env, stdout=pipe, stderr=pipe, text=True, start_new_session=True
            )
        except OSError as exc:
            return Result(127, err=f"{args[0]}: {exc}")
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            out, err = process.communicate()
            return Result(124, out, f"{err}{args[0]}: timed out after {timeout:g} s")
        return Result(process.returncode, out, err)

    return run


@dataclass(frozen=True)
class Context:
    root: Path
    run: Runner
    no_gh: str | None = None  # why `gh` cannot be used; None when it can
    no_docker: str | None = None  # why Docker cannot be used; None when it can
    offline: bool = False  # --offline: uv must not download either (UV_OFFLINE=1)

    def read(self, path: str) -> str | None:
        file = self.root / path
        return file.read_text(encoding="utf-8") if file.is_file() else None

    def gh_json(self, *args: str) -> Any:
        """The parsed output of a read-only `gh` query, or None when it fails."""
        result = self.run("gh", *args, timeout=60)
        try:
            return json.loads(result.out) if result.code == 0 else None
        except json.JSONDecodeError:
            return None

    def interns(self) -> list[str]:
        project = yaml.safe_load(self.read("docs/build/project.yaml") or "") or {}
        return [str(handle) for handle in (project.get("people") or {}).get("interns") or []]


def make_context(root: Path = REPO_ROOT, offline: bool = False) -> Context:
    run = run_in(root)
    if offline:
        return Context(root, run, "gh not used (--offline)", "Docker not used (--offline)", True)
    gh = run("gh", "auth", "status", timeout=30).code
    no_gh = None if gh == 0 else "gh is not installed" if gh == 127 else "gh is not signed in"
    return Context(root, run, no_gh, None if doctor.docker_info() else "Docker is not reachable")


CheckFn = Callable[[Context], Outcome]
CHECKS: list[tuple[str, str, bool, CheckFn]] = []  # id, title, blocks the freeze, function


def gate_check(check_id: str, title: str, blocks: bool = False) -> Callable[[CheckFn], CheckFn]:
    def register(func: CheckFn) -> CheckFn:
        CHECKS.append((check_id, title, blocks, func))
        return func

    return register


def outcome(problems: list[str], facts: list[str], manual: str | None = None) -> Outcome:
    """FAIL with the problems first, else MANUAL when a person must still confirm `manual`."""
    if problems:
        return Status.FAIL, "; ".join([*problems, *facts])
    if manual:
        return Status.MANUAL, "; ".join([*facts, manual])
    return Status.PASS, "; ".join(facts)


def latest_run(ctx: Context, workflow: str) -> Outcome:
    """The latest run of a workflow on main, through `gh run list`."""
    query = ("run", "list", "--workflow", workflow, "--branch", "main", "--limit", "1")
    runs = ctx.gh_json(*query, "--json", "status,conclusion,headSha,url")
    if runs is None:
        return Status.MANUAL, f"gh run list --workflow {workflow} --branch main failed"
    if not runs:
        return Status.FAIL, f"no {workflow} run on main yet"
    last = runs[0]
    where = f"latest {workflow} run on main ({last['headSha'][:7]}, {last['url']})"
    if last["status"] != "completed":
        return Status.MANUAL, f"{where} is {last['status']}; run the gate again when it ends"
    if last["conclusion"] == "success":
        return Status.PASS, f"{where} succeeded"
    return Status.FAIL, f"{where} ended {last['conclusion']}"


CONTRACTS = {"C1": "M1.7a", "C2": "M1.7b", "C3": "M1.7d", "C4": "M1.7c"}


def changelog_gaps(text: str) -> list[str]:
    """The contracts with no `### Cn` section holding a bullet under `## 1.0.0`."""
    start = re.search(r"^## 1\.0\.0\b.*$", text, re.MULTILINE)
    if start is None:
        return list(CONTRACTS)
    body = re.split(r"^## ", text[start.end() :], maxsplit=1, flags=re.MULTILINE)[0]
    sections = re.split(r"^### ", body, flags=re.MULTILINE)[1:]
    done = {section[:2] for section in sections if re.search(r"^- ", section, re.MULTILINE)}
    return [name for name in CONTRACTS if name not in done]


def on_main(ctx: Context) -> tuple[bool, str]:
    """Whether the checkout is a clean `origin/main` (the local ref; nothing is fetched)."""
    head = ctx.run("git", "rev-parse", "HEAD").out.strip()
    main = ctx.run("git", "rev-parse", "--verify", "-q", "origin/main").out.strip()
    dirty = bool(ctx.run("git", "status", "--porcelain").out.strip())
    if head and head == main and not dirty:
        return True, f"ran on main ({head[:7]})"
    where = f"ran on {head[:7] or 'an unknown commit'}{' with local changes' if dirty else ''}"
    return False, f"{where}, not a clean main (origin/main is {main[:7] or 'unknown'})"


@gate_check("GC-01", "Contract suite green on main", blocks=True)
def contract_suite(ctx: Context) -> Outcome:
    gaps = changelog_gaps(ctx.read("contracts/CHANGELOG.md") or "")
    problems = [f"contracts/CHANGELOG.md 1.0.0 lacks {c} (pending {CONTRACTS[c]})" for c in gaps]
    facts = [] if gaps else ["contracts/CHANGELOG.md 1.0.0 has C1 to C4"]
    env = {**os.environ, "UV_OFFLINE": "1"} if ctx.offline else None
    suite = ctx.run("make", "contracts-check", timeout=900, env=env)
    (problems if suite.code else facts).append(f"make contracts-check: {suite.tail}")
    main, where = on_main(ctx)
    facts.append(where)
    return outcome(problems, facts, None if main else "run the gate again on a clean main")


MIGRATION = "graph/schema/migrations/0001_init.cypher"
THROWAWAY_ONLY = ("NR_TEST_NEO4J_URI", "NR_TEST_ALLOW_WIPE")
CONSTRAINT = re.compile(r"^CREATE CONSTRAINT\b", re.MULTILINE)
INDEX = re.compile(r"^CREATE (?:[A-Z]+ )?INDEX\b", re.MULTILINE)


@gate_check("GC-02", "Graph schema applies cleanly", blocks=True)
def graph_schema(ctx: Context) -> Outcome:
    text = ctx.read(MIGRATION) or ""
    counts = len(CONSTRAINT.findall(text)), len(INDEX.findall(text))
    declared = [f"{MIGRATION} declares {counts[0]} constraints and {counts[1]} indexes"]
    if counts != (22, 7):
        return outcome(["section 8 expects 22 constraints and 7 indexes"], declared)
    if ctx.no_docker:
        return outcome([], declared, f"not applied: {ctx.no_docker}; make test-int applies it")
    if ctx.run("bash", "scripts/fetch_gds.sh", "--check").code:
        return outcome([], declared, "not applied: no pinned GDS jar (run make plugins once)")
    # Always a throwaway Testcontainers Neo4j: never a database named in the environment.
    env = {k: v for k, v in os.environ.items() if k not in THROWAWAY_ONLY}
    test = "graph/tests/test_migrations.py"
    pytest = (sys.executable, "-m", "pytest", "-m", "integration", "-q", test)
    result = ctx.run(*pytest, timeout=900, env=env)
    applied = f"pytest -m integration {test}: {result.tail}"
    return outcome([applied], declared) if result.code else outcome([], [*declared, applied])


LOCAL_E2E = "a local make demo-mini && make e2e run also counts (record it in the Phase 1 report)"
DEMO_STUB = re.compile(r"^demo-mini\b[^\n]*:[^\n]*\n\t@echo \"available after", re.MULTILINE)


@gate_check("GC-03", "Walking skeleton runs end to end", blocks=True)
def walking_skeleton(ctx: Context) -> Outcome:
    if not (ctx.root / ".github/workflows/e2e.yml").is_file():
        stub = DEMO_STUB.search(ctx.read("Makefile") or "")
        local = "make demo-mini is still a placeholder" if stub else LOCAL_E2E
        return Status.FAIL, f"no .github/workflows/e2e.yml (pending M1.9e); {local}"
    if ctx.no_gh:
        return Status.MANUAL, f"{ctx.no_gh}; check the latest e2e run on main; {LOCAL_E2E}"
    status, evidence = latest_run(ctx, "e2e.yml")
    return status, evidence if status is Status.PASS else f"{evidence}; {LOCAL_E2E}"


@gate_check("GC-04", "CI green on main", blocks=True)
def ci_green(ctx: Context) -> Outcome:
    if ctx.no_gh:
        return Status.MANUAL, f"{ctx.no_gh}; check the latest ci run on main"
    return latest_run(ctx, "ci.yml")


ISSUE_FORMS = ("bug", "feature", "typology", "data-source", "contract-change", "config")
GOVERNANCE = (
    *("LICENSE", "NOTICE", "README.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "CONTRIBUTING.md"),
    *("CONTRIBUTORS.md", "DATA_SOURCES.md", "CHANGELOG.md", ".gitignore", ".gitattributes"),
    *(".editorconfig", ".worktreeinclude", ".github/pull_request_template.md"),
    *(f".github/ISSUE_TEMPLATE/{form}.yml" for form in ISSUE_FORMS),
    *(".github/labels.yml", ".github/pr-size-exclude.txt", ".github/CODEOWNERS"),
    *("scripts/generate_codeowners.py", "scripts/sync_labels.py", "docs/build/PROGRESS.md"),
    *("docs/README.md", "docs/decisions/README.md", "docs/decisions/_template.md"),
    *("docs/decisions/0001-record-architecture-decisions.md", "data/README.md"),
    "data/import/.gitkeep",
)


@gate_check("GC-05", "Repository basics")
def repository_basics(ctx: Context) -> Outcome:
    missing = [path for path in GOVERNANCE if not (ctx.root / path).is_file()]
    problems = [f"missing {', '.join(missing)}"] if missing else []
    facts = [f"{len(GOVERNANCE) - len(missing)} of {len(GOVERNANCE)} M1.1 governance files"]
    owners = ctx.run(sys.executable, "scripts/generate_codeowners.py", "--check")
    if owners.code:
        problems.append(f"generate_codeowners.py --check: {owners.tail}")
    else:
        facts.append("generate_codeowners.py --check passes")
    if ctx.no_gh:
        return outcome(problems, facts, f"labels not checked: {ctx.no_gh}")
    labels = ctx.gh_json("label", "list", "--limit", "500", "--json", "name")
    if labels is None:
        return outcome(problems, facts, "labels not checked: gh label list failed")
    wanted = {label["name"] for label in yaml.safe_load(ctx.read(".github/labels.yml") or "[]")}
    if absent := sorted(wanted - {label["name"] for label in labels}):
        problems.append(f"labels not on GitHub: {', '.join(absent)} (scripts/sync_labels.py)")
    else:
        facts.append(f"the {len(wanted)} labels of .github/labels.yml exist on GitHub")
    return outcome(problems, facts)


LIMITATION = re.compile(r"^#+ Plan limitation and interim controls", re.MULTILINE)


@gate_check("GC-06", "Protection in place, or the plan limitation recorded")
def protection(ctx: Context) -> Outcome:
    answer = f"protection not queried: {ctx.no_gh}"
    if not ctx.no_gh:
        result = ctx.run("gh", "api", "repos/{owner}/{repo}/branches/main/protection")
        if result.code == 0:
            return Status.PASS, "gh api repos/<repo>/branches/main/protection answers"
        answer = f"protection API: {Result(result.code, result.err).tail}"
    if LIMITATION.search(ctx.read("docs/build/ci.md") or ""):
        recorded = [answer, "docs/build/ci.md records the plan limitation and interim controls"]
        return outcome([], recorded, "a person confirms the OD-16 interim controls are in use")
    return Status.FAIL, f"{answer}; docs/build/ci.md has no 'Plan limitation and interim controls'"


@gate_check("GC-07", "Devcontainer works")
def devcontainer(ctx: Context) -> Outcome:
    if not (ctx.root / ".devcontainer/devcontainer.json").is_file():
        return Status.FAIL, "no .devcontainer/devcontainer.json (pending M1.5)"
    return Status.MANUAL, "devcontainer.json exists; a Windows or Codespaces user confirms it"


SPIKES = {"companies-house": "M1.8a", "gleif": "M1.8b", "icij": "M1.8c", "opensanctions": "M1.8d"}
VERDICT = re.compile(r"^#+ (?:\d+\.\s*)?Verdict\s*\n\s*\*\*([^*]+)\*\*", re.MULTILINE)


def spike_verdict(text: str) -> str | None:
    """The bold first words of a report's Verdict section, without the final full stop."""
    match = VERDICT.search(text)
    return match[1].strip().rstrip(".") if match else None


@gate_check("GC-08", "Every source fetched end to end in a spike")
def spikes(ctx: Context) -> Outcome:
    problems, facts = [], []
    for source, milestone in SPIKES.items():
        report = ctx.read(f"docs/data/spikes/{source}.md")
        verdict = spike_verdict(report or "")
        accepted = {"go", "go with changes", "drop"}
        if source == "opensanctions":
            accepted.add("blocked on licence decision")
        if verdict and verdict.lower() in accepted:
            facts.append(f"{source}: {verdict}")
        else:
            found = "no report" if report is None else f"verdict '{verdict or 'none'}'"
            problems.append(f"{source}: {found} (pending {milestone})")
    return outcome(problems, facts)


DEMO_MINI = "data/fixtures/demo-mini"
DEMO_SEED = "20261023"  # PHASE-1.md M1.8e


JOIN_BRANCHES = {"p1/m1-8e-synthetic-join": "M1.8e-1", "p1/m1-8e-2-join-spike": "M1.8e-2"}


def fixture_files(folder: Path) -> dict[str, Any]:
    """What `synth demo-mini` writes: records and labels as bytes, manifests as parsed JSON
    without `created_at` (the time of the run), by path relative to `folder`."""
    found: dict[str, Any] = {}
    for path in [*folder.glob("*.ftm.jsonl"), *folder.glob("labels/*.csv")]:
        found[path.relative_to(folder).as_posix()] = path.read_bytes()
    for path in folder.glob("*.manifest.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest.pop("created_at", None)
        found[path.relative_to(folder).as_posix()] = manifest
    return found


def join_prs(ctx: Context) -> list[dict[str, Any]] | None:
    """The M1.8e pull requests, by branch and by title, or None when gh fails."""
    fields = ("--state", "all", "--json", "number,title,headRefName,state")
    queries = [("--head", branch) for branch in JOIN_BRANCHES] + [("--search", "M1.8e in:title")]
    found: dict[int, dict[str, Any]] = {}
    for query in queries:
        prs = ctx.gh_json("pr", "list", *query, *fields)
        if prs is None:
            return None
        found.update({pr["number"]: pr for pr in prs})
    return [found[number] for number in sorted(found)]


def is_join_spike(pr: dict[str, Any]) -> bool:
    return JOIN_BRANCHES.get(pr["headRefName"]) == "M1.8e-2" or "M1.8e-2" in pr["title"]


@gate_check("GC-09", "Synthetic join proven")
def synthetic_join(ctx: Context) -> Outcome:
    files = sorted((ctx.root / DEMO_MINI).glob("*.ftm.jsonl"))
    if not files:
        return Status.FAIL, f"no {DEMO_MINI}/*.ftm.jsonl (pending M1.8e)"
    from neonradar_contracts import records

    counts, issues = records.validate_files(files, strict=True)
    if issues:
        return Status.FAIL, f"validate-records {DEMO_MINI} --strict: {len(issues)} issue(s)"
    with tempfile.TemporaryDirectory() as out:
        neonradar = str(Path(sys.executable).with_name("neonradar"))
        made = ctx.run(neonradar, "synth", "demo-mini", "--seed", DEMO_SEED, "--out", out)
        new, old = fixture_files(Path(out)), fixture_files(ctx.root / DEMO_MINI)
    if made.code or new != old:
        differ = sorted(name for name in new.keys() | old.keys() if new.get(name) != old.get(name))
        why = f"exit {made.code} ({made.tail})" if made.code else ", ".join(differ) + " differ"
        return Status.FAIL, f"synth demo-mini --seed {DEMO_SEED}: {why}"
    facts = [f"demo-mini: {counts.total()} records, strict OK, regenerates identically"]
    if ctx.no_gh:
        return outcome([], facts, f"M1.8e pull requests not checked: {ctx.no_gh}")
    prs = join_prs(ctx)
    if prs is None:
        return outcome([], facts, "M1.8e pull requests not checked: gh pr list failed")
    listed = ", ".join(f"#{pr['number']} {pr['state'].lower()}" for pr in prs) or "none"
    facts.append(f"M1.8e pull requests: {listed}")
    joins = [pr for pr in prs if pr["state"] == "MERGED" and is_join_spike(pr)]
    if not joins:
        return outcome(["no merged M1.8e-2 pull request (the synthetic-join spike)"], facts)
    numbers = ", ".join(f"#{pr['number']}" for pr in joins)
    return outcome([], facts, f"a person confirms the synthetic-join output in PR {numbers}")


@gate_check("GC-10", "Knowledge base seeded")
def knowledge_base(ctx: Context) -> Outcome:
    from neonradar_detect import catalog

    bibliography = yaml.safe_load(ctx.read("docs/sources/bibliography.yaml") or "") or {}
    entries = bibliography.get("entries") if isinstance(bibliography, dict) else None
    count = len(entries) if isinstance(entries, list) else 0
    problems = [] if count else ["docs/sources/bibliography.yaml has no entries"]
    facts = [f"bibliography: {count} entries"] if count else []
    script = (sys.executable, "scripts/check_citations.py", "docs/", "detect/typologies/")
    citations = ctx.run(*script, "README.md")
    if citations.code:
        problems.append(f"check_citations.py: {citations.tail}")
    else:
        facts.append("check_citations.py passes")
    typologies = catalog.load_catalog(ctx.root / "detect" / "typologies")
    explainers = sum((ctx.root / typology.doc).is_file() for typology in typologies.values())
    found = f"{len(typologies)} typology files and {explainers} explainers"
    (facts if (len(typologies), explainers) == (15, 15) else problems).append(f"{found} of 15")
    circular = typologies.get("circular_flow")
    if circular is not None and circular.status == "approved":
        facts.append("circular_flow is approved")
    else:
        status = circular.status if circular else "missing"
        problems.append(f"circular_flow is {status} (a typology researcher approves it, OD-5)")
    return outcome(problems, facts)


@gate_check("GC-11", "Every intern has a merged pull request")
def interns_merged(ctx: Context) -> Outcome:
    handles = ctx.interns()
    if not handles:
        return Status.FAIL, NOT_MET
    if ctx.no_gh:
        return Status.MANUAL, f"{ctx.no_gh}; run gh pr list --state merged --author <handle>"
    query = ("--state", "merged", "--limit", "1", "--json", "number")
    merged = {h: ctx.gh_json("pr", "list", "--author", h.lstrip("@"), *query) for h in handles}
    if any(prs is None for prs in merged.values()):
        return Status.MANUAL, "gh pr list --author failed for some interns"
    without = [handle for handle, prs in merged.items() if not prs]
    return outcome(
        [f"no merged pull request by {', '.join(without)}"] if without else [],
        [f"{len(handles) - len(without)} of {len(handles)} interns have a merged pull request"],
    )


LOG_ENTRY = re.compile(r"^### Week of \d{4}-\d{2}-\d{2}", re.MULTILINE)


@gate_check("GC-12", "Learning logs started")
def learning_logs(ctx: Context) -> Outcome:
    handles = ctx.interns()
    if not handles:
        return Status.FAIL, NOT_MET
    logs = {h: ctx.read(f"docs/learning/{h.lstrip('@')}.md") or "" for h in handles}
    without = [handle for handle, text in logs.items() if not LOG_ENTRY.search(text)]
    return outcome(
        [f"no learning log with a dated entry for {', '.join(without)}"] if without else [],
        [f"{len(handles) - len(without)} of {len(handles)} interns have a docs/learning/ entry"],
    )


@gate_check("GC-13", "Assignment 2 under way")
def assignment_2(ctx: Context) -> Outcome:
    problems = [] if ctx.interns() else [NOT_MET]
    if ctx.read("docs/team/assignment-2.md") is None:
        problems.append("no docs/team/assignment-2.md (pending M1.11b)")
    return outcome(problems, [], "match each typology in assignment-2.md to an open or merged PR")


# PHASE-1.md 7.6: the status at Gate 1 and the milestone that writes each ADR.
ADRS = {
    "0001": ("accepted", "M1.1"),
    "0002": ("accepted", "M1.4"),
    "0003": ("accepted", "M1.7a"),
    "0004": ("accepted", "M1.7b"),
    "0005": ("accepted", "M1.8e"),
    "0006": ("accepted", "M1.10a"),
    "0007": ("accepted", "M1.3"),
    "0008": ("accepted", "M1.7d"),
    "0009": ("accepted", "M1.7c"),
    "0010": ("proposed", "M1.10c"),
    "0011": ("accepted", "M1.2"),
    "0012": ("proposed", "M1.10c"),
}
ADR_STATUS = re.compile(r"^- \*\*Status:\*\*\s*([a-z]+)", re.MULTILINE | re.IGNORECASE)


@gate_check("GC-14", "ADRs as in 7.6")
def adrs(ctx: Context) -> Outcome:
    missing: list[str] = []
    accepted: list[tuple[str, str, str]] = []  # number, path, the status line as written
    differ: dict[str, list[str]] = {}  # "<found>, 7.6 says <expected>" -> ADR numbers
    for number, (expected, milestone) in ADRS.items():
        files = sorted((ctx.root / "docs/decisions").glob(f"{number}-*.md"))
        if not files:
            missing.append(f"{number} (pending {milestone})")
            continue
        found = ADR_STATUS.search(files[0].read_text(encoding="utf-8"))
        status = found[1].lower() if found else "no status"
        if status != expected:
            how = f"{status}, 7.6 says {expected}"
            how += " (the deciders accept ADRs, OD-5)" if expected == "accepted" else ""
            differ.setdefault(how, []).append(number)
        elif status == "accepted" and found:
            accepted.append((number, files[0].relative_to(ctx.root).as_posix(), found[0]))
    problems = [f"missing {', '.join(missing)}"] if missing else []
    problems += [f"{how}: {', '.join(numbers)}" for how, numbers in differ.items()]
    if problems:
        return outcome(problems, [])
    commits = []
    for number, path, line in accepted:  # the commit that wrote the status line as it is now
        commit = ctx.run("git", "log", "-1", "--format=%h", "-S", line, "--", path).out.strip()
        commits.append(f"{number} {commit or 'no commit found'}")
    facts = ["status lines match 7.6", f"accepting commits: {', '.join(commits) or 'none'}"]
    return outcome([], facts, "a person confirms each accepting commit is by the ADR's deciders")


@gate_check("GC-15", "Legal and communications conversation started")
def legal_note(ctx: Context) -> Outcome:
    text = ctx.read("docs/build/PROGRESS.md") or ""
    # Notes only: a milestone row in the table may name this check without being the note.
    notes = [(n, line) for n, line in enumerate(text.splitlines(), 1) if not line.startswith("|")]
    words = {"legal": r"\blegal\b", "communications": r"\bcommunication"}  # each on its own
    lines = {w: [n for n, line in notes if re.search(rx, line, re.I)] for w, rx in words.items()}
    if missing := [word for word, found in lines.items() if not found]:
        absent = " or ".join(missing)
        return Status.FAIL, f"no note in docs/build/PROGRESS.md mentions {absent} (PHASE-1.md 1.2)"
    where = ", ".join(f"{word} at line {found[0]}" for word, found in lines.items())
    note = f"docs/build/PROGRESS.md mentions {where}"
    return outcome([], [note], "the project lead confirms the conversation started")


REPORT = "docs/build/reports/phase-1.md"


@gate_check("GC-16", "Phase 1 report written")
def phase_report(ctx: Context) -> Outcome:
    text = ctx.read(REPORT)
    if text is None:
        return Status.FAIL, f"no {REPORT} (pending M1.12-2)"
    headings = " ".join(line.lower() for line in text.splitlines() if line.startswith("#"))
    absent = [part for part in ("metric", "deviation", "risk", "phase 2") if part not in headings]
    return outcome(
        [f"{REPORT} has no heading for: {', '.join(absent)}"] if absent else [],
        [] if absent else [f"{REPORT} has metrics, deviations, risks and Phase 2 inputs"],
    )


@gate_check("GC-17", "Data steward approved the licence fields", blocks=True)
def licence_fields(ctx: Context) -> Outcome:
    paths = ("contracts/datasets.yaml", "DATA_SOURCES.md")
    if missing := [path for path in paths if not (ctx.root / path).is_file()]:
        return Status.FAIL, f"missing {', '.join(missing)}"
    log = ("git", "log", "-1", "--format=%h", "--")
    facts = [f"{path} last changed in {ctx.run(*log, path).tail}" for path in paths]
    return outcome([], facts, "link the data steward's approving review in the Phase 1 report")


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    blocks: bool
    status: Status
    evidence: str

    def line(self) -> str:
        return f"{self.id} {self.status:<6} {self.title}: {self.evidence}"


def run_checks(ctx: Context) -> Iterator[Check]:
    """Run every check in order; a check that raises reports FAIL and the others still run."""
    for check_id, title, blocks, func in CHECKS:
        try:
            status, evidence = func(ctx)
        except Exception as exc:  # a broken check must not hide the others
            logger.debug("%s raised", check_id, exc_info=True)
            status, evidence = Status.FAIL, f"the check raised {type(exc).__name__}: {exc}"
        yield Check(check_id, title, blocks, status, evidence)


def summary(checks: list[Check]) -> str:
    counts = Counter(check.status for check in checks)
    totals = ", ".join(f"{counts[status]} {status}" for status in Status)
    freeze = ", ".join(f"{check.id} {check.status}" for check in checks if check.blocks)
    return f"Gate 1: {totals}. Freeze checks: {freeze}"


app = typer.Typer(help="Phase gate checks (PHASE-1.md section 8).", no_args_is_help=True)


@app.command(name="check")
def check_command(
    phase: Annotated[int, typer.Option("--phase", help="The phase whose gate to check.")] = 1,
    offline: Annotated[
        bool, typer.Option("--offline", help="Call neither gh nor Docker; those checks: MANUAL.")
    ] = False,
    report_only: Annotated[
        bool, typer.Option("--report-only", help="Exit 0 even when a check fails.")
    ] = False,
) -> None:
    """One line per gate check with PASS, FAIL or MANUAL and its evidence; exit 1 on any FAIL."""
    if phase != 1:
        typer.echo(f"No gate checks for phase {phase} yet; only phase 1 has them.")
        raise typer.Exit(code=2)
    ctx = make_context(REPO_ROOT, offline)
    head = ctx.run("git", "describe", "--always", "--dirty").tail
    typer.echo(f"Gate 1 checks (PHASE-1.md section 8) at {head}")
    checks = []
    for check in run_checks(ctx):
        typer.echo(check.line())
        checks.append(check)
    typer.echo(summary(checks))
    if not report_only and any(check.status is Status.FAIL for check in checks):
        raise typer.Exit(code=1)
