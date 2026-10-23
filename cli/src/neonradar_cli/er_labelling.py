"""`neonradar er sample|label|review|precision`: the evaluation sample, labelling, review of
possible matches and the precision report (PHASE-2.md M2.10c, 7.3).

Every command takes `--run <id>` or `--run latest` (`latest_run(profile)`). On a real profile
each one runs the real-data gate first and works inside the redaction guard (M2.2). `er label`
and `er review` are for a person at a terminal (`require_terminal`, checked before anything
else): they show record cards and record what that person answers, never a pre-selected
answer (G10). They refuse when the record files are not the ones the run read, and never ask
about a pair whose card is missing. `er sample` and `er precision` print counts only.
"""

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:
    from neonradar_ingest.data.profiles import Profile
    from neonradar_ingest.data.project import Project
    from neonradar_resolve.cards import Card, Facts
    from neonradar_resolve.sample import Pair

ADR_0014 = Path("docs/decisions/0014-entity-resolution-approach-and-thresholds.md")
QUESTION = "Do the two records describe the same person or organisation?"

ProfileOption = Annotated[str, typer.Option("--profile", help="A profile in ingest/profiles/.")]
RunOption = Annotated[str, typer.Option("--run", help="A resolution run id, or latest.")]


class Refused(ValueError):
    """A refusal with a fixed message (no value): exit code 2 inside the redaction guard."""

    exit_code = 2
    counts_only = True


def _gate(project: Project, chosen: Profile, where: Any) -> None:
    from neonradar_ingest.data import gate

    where.step = "gate"
    gate.check_real_data(project, chosen)
    for dataset in chosen.enabled_sources(project):
        where.dataset = dataset
        gate.check_real_data(project, chosen, dataset)
    where.step, where.dataset = "run", None


def _run_folder(chosen: Profile, run: str) -> tuple[str, Path]:
    from neonradar_ingest.data import layout

    run_id = layout.latest_run(chosen) if run == "latest" else layout.safe_name("run id", run)
    if run_id is None:
        raise Refused("this profile has no resolution run yet (er run)")
    folder = layout.resolution_dir(chosen, run_id)
    if not (folder / "run.json").is_file():
        raise Refused("no finished resolution run with this id for this profile")
    return run_id, folder


def _handle(value: str | None, option: str) -> str:
    from neonradar_resolve.rules import handle

    found = handle(value)
    if found is None:
        raise Refused(f"{option} is not a GitHub handle such as @example")
    return found


def _handles(values: Iterable[str | None]) -> set[str]:
    from neonradar_resolve.rules import handle

    return {h for value in values if (h := handle(value))}


def _team(project: Project, chosen: Profile) -> tuple[frozenset[str], frozenset[str]]:
    """people.er_labellers and people.er_senior_reviewers as handles. On a real profile the
    command is refused while either list holds a placeholder such as @TODO (or anything that
    is not a handle) or er_labellers is empty: fail closed until people join (OD-22)."""
    from neonradar_resolve.rules import handle

    labellers = [handle(v) for v in project.people.er_labellers]
    seniors = [handle(v) for v in project.people.er_senior_reviewers]
    if chosen.real_data and (not labellers or None in labellers or None in seniors):
        raise Refused(
            "people.er_labellers or people.er_senior_reviewers in project.yaml does not name"
            " people yet: labelling and review of real data wait until both do (OD-22)"
        )
    return frozenset(h for h in labellers if h), frozenset(h for h in seniors if h)


def _labellers(value: str, listed: frozenset[str], real_data: bool) -> list[str]:
    """The handles of --labellers; a real profile names every handle in people.er_labellers
    and no other (7.3 rule 1)."""
    handles = [_handle(h, "an item of --labellers") for h in value.split(",")]
    if real_data and set(handles) != listed:
        raise Refused(
            "a real profile's sample goes to every handle in people.er_labellers and to no one"
            " else (7.3 rule 1, G10)"
        )
    return handles


def _barred(project: Project, real_data: bool = False) -> frozenset[str]:
    """The people who set the thresholds (ADR-0014): never adjudicators (7.3 rule 4). On a real
    profile both people.tech_lead and squads.graph.mentor must name a person (fail closed)."""
    from neonradar_resolve.rules import handle

    graph = project.squads.get("graph")
    found = [handle(project.people.tech_lead), handle(graph.mentor if graph else None)]
    if real_data and None in found:
        raise Refused(
            "people.tech_lead or squads.graph.mentor in project.yaml does not name a person:"
            " adjudication on real data waits until both do (7.3 rule 4)"
        )
    return frozenset(h for h in found if h)


def _ask(prompt: str, choices: dict[str, str]) -> str:
    """The person's answer, asked again until it is one of `choices`; there is no default."""
    while True:
        answer = str(typer.prompt(prompt, default="", show_default=False)).strip().lower()
        if answer in choices:
            return choices[answer]
        typer.echo(f"Please type one of: {', '.join(choices)}.")


def _show(cards: dict[str, Card], pair: tuple[str, str]) -> None:
    """The two cards side by side; never a question about a pair whose card is missing."""
    from neonradar_resolve.cards import side_by_side

    left, right = (cards.get(rid) for rid in pair)
    if left is None or right is None:
        raise Refused(
            "a record of this pair is missing from this profile's record folders, so nobody is"
            " asked about the pair"
        )
    typer.echo(side_by_side(left, right))


def _check_inputs(chosen: Profile, project: Project, folder: Path) -> None:
    """Cards must show what the run resolved: refuse when the record files are not the ones
    the run read (`run.json` inputs, file names and sha256)."""
    from neonradar_resolve import records

    info = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    if not records.unchanged(chosen.record_dirs(project), info.get("inputs") or []):
        raise Refused(
            "the record files changed since this run, so its cards would not show what it"
            " resolved: a new er run (and for labelling a new sample) is needed"
        )


def sample_command(
    profile: ProfileOption,
    run: RunOption,
    seed: Annotated[int, typer.Option("--seed", min=0, help="The sample seed (ADR-0014).")],
    labellers: Annotated[
        str, typer.Option("--labellers", help="Comma-separated handles, for example @a,@b.")
    ],
) -> None:
    """Draw the evaluation sample of a run (7.3); print counts only."""
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_ingest.data import layout
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve import sample

    project, chosen = project_or_exit(), profile_or_exit(profile)
    with redact.guard(chosen, "er sample") as where:
        _gate(project, chosen, where)
        where.step = "sample"
        run_id, folder = _run_folder(chosen, run)
        info = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        sample.check_run(info, chosen.real_data)
        adr = REPO_ROOT / ADR_0014
        adr_seed = sample.check_seed(
            adr.read_text(encoding="utf-8") if adr.is_file() else None, seed, chosen.real_data
        )
        listed, _ = _team(project, chosen)
        handles = _labellers(labellers, listed, chosen.real_data)
        found = sample.frames(
            sample.read_canonical(folder / "canonical.csv"),
            sample.read_candidates(folder / "candidates.jsonl"),
        )
        pairs, census = sample.draw(found, seed, handles)
        counts = sample.sample_counts(
            found,
            pairs,
            census,
            profile=chosen.profile,
            run_id=run_id,
            seed=seed,
            adr_seed=adr_seed,
            decisions_used=info.get("decisions_used"),
            decisions_on_file=(info.get("counts") or {}).get("decisions_on_file", 0),
            started_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        sample.write_sample(layout.labels_dir(chosen, run_id), pairs, counts)
        if adr_seed is None:
            typer.echo(f"sample seed {seed} (ADR-0014 sets no evaluation sample seed yet)")
        summary.emit(chosen, "er sample", counts)


def _label_cards(chosen: Profile, project: Project, pairs: list[Pair]) -> dict[str, Card]:
    from neonradar_resolve import cards

    ids = {r for p in pairs for r in (p.record_a, p.record_b)}
    found, _ = cards.load(chosen.record_dirs(project), ids)
    return found


def label_command(
    profile: ProfileOption,
    run: RunOption,
    labeller: Annotated[str, typer.Option("--labeller", help="Your GitHub handle, @you.")],
    adjudicate: Annotated[
        bool, typer.Option("--adjudicate", help="Adjudicate S4 pairs whose two labels differ.")
    ] = False,
) -> None:
    """Label the pairs of the sample assigned to you, at a terminal (7.3; humans only)."""
    from neonradar_cli import redact
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_cli.tty import require_terminal
    from neonradar_ingest.data import layout
    from neonradar_resolve import labels, sample

    chosen = profile_or_exit(profile)
    with redact.guard(chosen, "er label") as where:
        where.step = "terminal"
        require_terminal("er label")  # before anything else is read (G10)
        project = project_or_exit()
        _gate(project, chosen, where)
        where.step = "label"
        who = _handle(labeller, "--labeller")
        listed, _ = _team(project, chosen)
        barred = _barred(project, chosen.real_data) if adjudicate else frozenset()
        allowed = (
            listed | _handles([project.people.project_lead]) if chosen.real_data else None
        )  # a real profile: the project lead and people.er_labellers only
        if adjudicate:
            labels.check_adjudicator(who, barred, allowed)
        elif chosen.real_data and who not in listed:
            raise Refused("a labeller of a real profile is in people.er_labellers (G10)")
        run_id, run_dir = _run_folder(chosen, run)
        folder = layout.labels_dir(chosen, run_id)
        pairs, _ = sample.read_sample(folder)
        _check_inputs(chosen, project, run_dir)
        if adjudicate:
            _adjudicate(chosen, project, folder, pairs, who, barred, allowed)
            return
        mine = [p for p in pairs if who in p.labellers]
        if not mine:
            raise Refused("no pair of this sample is assigned to this labeller")
        shown = _label_cards(chosen, project, mine)
        while (found := labels.next_pair(pairs, labels.read_labels(folder), who)) is not None:
            number, pair = found
            typer.echo(f"\nPair {number} of {len(mine)}")
            _show(shown, (pair.record_a, pair.record_b))
            answer = _ask(f"{QUESTION} s same, d different, u unsure, q stop", _CHOICES)
            if answer == "stop":
                return
            note = typer.prompt("Note (optional, Enter to skip)", default="", show_default=False)
            labels.append_label(folder, pair.pair_id, answer, who, note)
        typer.echo("Every pair assigned to you is labelled. Thank you.")


_CHOICES = {"s": "same", "d": "different", "u": "unsure", "q": "stop"}


def _adjudicate(
    chosen: Profile,
    project: Project,
    folder: Path,
    pairs: list[Pair],
    who: str,
    barred: frozenset[str],
    allowed: frozenset[str] | None,
) -> None:
    from neonradar_resolve import labels

    found = labels.read_labels(folder)
    queue, refused = labels.adjudication_queue(pairs, found, who, barred, allowed)
    if not queue and refused:
        raise Refused("you labelled every pair that waits: another person adjudicates it")
    # the cards of every S4 pair: a disagreement that appears while this runs has them too
    shown = _label_cards(chosen, project, [p for p in pairs if p.overlap]) if queue else {}
    done = 0
    while True:
        found = labels.read_labels(folder)
        queue, _ = labels.adjudication_queue(pairs, found, who, barred, allowed)
        if not queue:
            typer.echo(f"No pair waits for adjudication ({done} adjudicated now).")
            return
        pair = queue[0]
        typer.echo(f"\nPair to adjudicate, {len(queue)} left (neither earlier label is shown)")
        _show(shown, (pair.record_a, pair.record_b))
        answer = _ask(f"{QUESTION} s same, d different, u unsure, q stop", _CHOICES)
        if answer == "stop":
            return
        note = typer.prompt("Note (optional, Enter to skip)", default="", show_default=False)
        labels.append_label(folder, pair.pair_id, answer, who, note, adjudication=True)
        done += 1


def _crossing(left: list[str], right: list[str], facts: dict[str, Facts]) -> bool:
    """Whether merging the two clusters crosses P1 or P2 (cluster.p1_reason, crosses_p2);
    a record missing from the folders counts as crossing (fail closed)."""
    if any(rid not in facts for rid in left + right):
        return True
    fl = frozenset().union(*(facts[r].flag_topics for r in left))
    fr = frozenset().union(*(facts[r].flag_topics for r in right))
    kl, kr = {facts[r].leaked for r in left}, {facts[r].leaked for r in right}
    return fl != fr or (True in kl and False in kr) or (False in kl and True in kr)


def review_command(
    profile: ProfileOption,
    run: RunOption,
    reviewer: Annotated[str, typer.Option("--reviewer", help="Your GitHub handle, @you.")],
) -> None:
    """Review the run's possible matches at a terminal and record same or different (7.1.8)."""
    from neonradar_cli import redact
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_cli.tty import require_terminal
    from neonradar_graph.wording import evidence_lines, explain_possible_match
    from neonradar_ingest.data import layout
    from neonradar_resolve import cards, decisions, sample

    chosen = profile_or_exit(profile)
    with redact.guard(chosen, "er review") as where:
        where.step = "terminal"
        require_terminal("er review")  # before anything else is read (G10)
        project = project_or_exit()
        _gate(project, chosen, where)
        where.step = "review"
        who = _handle(reviewer, "--reviewer")
        listed, seniors = _team(project, chosen)
        if chosen.real_data and who not in listed | seniors:
            raise Refused("a reviewer is in people.er_labellers or people.er_senior_reviewers")
        _, folder = _run_folder(chosen, run)
        _check_inputs(chosen, project, folder)
        path = layout.decisions_file(chosen)
        deciders = listed | seniors if chosen.real_data else None  # as er run reads the file
        clusters: dict[str, list[str]] = {}
        for row in sample.read_canonical(folder / "canonical.csv"):
            clusters.setdefault(row["canonical_id"], []).append(row["record_id"])
        candidates = sample.read_candidates(folder / "candidates.jsonl")
        queue = decisions.review_queue(candidates, path, who, seniors, clusters, deciders)
        ids = {r for c in queue for r in clusters.get(c["a"], []) + clusters.get(c["b"], [])}
        shown, facts = cards.load(chosen.record_dirs(project), ids)
        for number, match in enumerate(queue, start=1):
            typer.echo(f"\nPossible match {number} of {len(queue)}")
            _show(shown, (match["record_a"], match["record_b"]))
            typer.echo(explain_possible_match(match))
            for line in evidence_lines(match.get("features")):
                typer.echo(f"  {line}")
            answer = _ask(
                f"{QUESTION} s same, d different, k skip, q stop",
                {"s": "same", "d": "different", "k": "skip", "q": "stop"},
            )
            if answer == "stop":
                return
            if answer == "skip":
                continue
            note = ""
            while answer == "same" and not note.strip():
                note = typer.prompt("Note (required for same: what makes them the same)")
            if answer == "different":
                note = typer.prompt(
                    "Note (optional, Enter to skip)", default="", show_default=False
                )
            a, b = match["record_a"], match["record_b"]
            crossing = _crossing(clusters[match["a"]], clusters[match["b"]], facts)
            others = decisions.supporters(path, a, b, deciders) - {who}
            if answer == "same" and crossing and who not in seniors and not others:
                typer.echo(
                    "This decision joins records listed differently, or a leaked record with"
                    " another source: it waits for a second reviewer (or a senior reviewer)"
                    " before a run applies it (7.1.2, D7)."
                )
            decisions.append_decision(path, a, b, answer, who, note)
        typer.echo("No possible match left to review in this run.")


def precision_command(
    profile: ProfileOption,
    run: RunOption,
    out: Annotated[Path, typer.Option("--out", help="Where to write the report (Markdown).")],
) -> None:
    """Combine the labels and write the precision report of 7.3 (counts and rates only)."""
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_ingest.data import layout
    from neonradar_ingest.data.project import REPO_ROOT
    from neonradar_resolve import labels, precision, sample

    project, chosen = project_or_exit(), profile_or_exit(profile)
    with redact.guard(chosen, "er precision") as where:
        _gate(project, chosen, where)
        where.step = "precision"
        run_id, folder = _run_folder(chosen, run)
        info = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        labelled = layout.labels_dir(chosen, run_id)
        pairs, drawn = sample.read_sample(labelled)
        if drawn.get("run_id") != run_id:
            raise Refused("the sample was drawn from another run")
        census = {s: bool((drawn.get("census") or {}).get(s.lower())) for s in sample.STRATA}
        listed, _ = _team(project, chosen)
        lead = _handles([project.people.project_lead])
        outcome = precision.measure(
            pairs,
            labels.read_labels(labelled),
            _barred(project, chosen.real_data),
            census,
            adjudicators=listed | lead if chosen.real_data else None,
        )
        text = precision.report(
            outcome,
            on=datetime.now(UTC).date(),
            profile=chosen.profile,
            real_data=chosen.real_data,
            run=info,
            sample=drawn,
            project_lead=next(iter(lead), None),
        )
        target = out if out.is_absolute() else REPO_ROOT / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out.name} (counts and rates only)")
        summary.emit(chosen, "er precision", precision.summary(outcome))
