"""`neonradar bench queries`: API latencies on a loaded profile (PHASE-2.md M2.13 deliverable 3).

The eligible entities (`:Company` and `:Person` nodes with an `OWNS` relationship) come from one
read-only query, `bench_entities.cypher`, sorted by id; `pick` chooses `n` of them by the order
of sha1("<seed>:<id>"). Each pick is timed on `/ownership` up and down (`max_hops=6`), `/paths`
to the next pick (`max_hops=4`), `/network` at depth 2 and `/search` with the first token of
its caption, through the API's route functions (no HTTP). Only latencies, result counts and
timeouts are printed and emitted, never an id or a name.
"""

import hashlib
import math
import time
from collections.abc import Callable, Sequence
from functools import partial
from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:
    from neonradar_api.graph import GraphConnection

app = typer.Typer(help="Benchmarks of a loaded profile (counts and timings only).")

ENDPOINTS = ("ownership_up", "ownership_down", "paths", "network", "search")
ELIGIBLE_LIMIT = 10_000_000


def pick(ids: Sequence[str], n: int, seed: int) -> list[str]:
    """`n` of `ids` in the order of sha1("<seed>:<id>"): the same ids for the same seed."""

    def order(entity_id: str) -> tuple[str, str]:
        text = f"{seed}:{entity_id}".encode()
        return hashlib.sha1(text, usedforsecurity=False).hexdigest(), entity_id

    return sorted(set(ids), key=order)[:n]


def percentile(values: Sequence[float], share: float) -> float | None:
    """The nearest-rank percentile in milliseconds, rounded to 0.1 (None without values)."""
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(math.ceil(share * len(ordered)) - 1, 0)] * 1000, 1)


def _size(answer: Any) -> int:
    for name in ("paths", "items", "nodes"):
        if hasattr(answer, name):
            return len(getattr(answer, name))
    return 0


def measure(graph: GraphConnection, picks: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Time each endpoint for each pick; per endpoint: calls, p50, p95 and maximum in ms, the
    results returned (paths, search hits or nodes), timeouts and other errors."""
    from neonradar_api import main
    from neonradar_graph.ownership import QueryTimeout

    seconds: dict[str, list[float]] = {name: [] for name in ENDPOINTS}
    found, timeouts, errors = (dict.fromkeys(ENDPOINTS, 0) for _ in range(3))

    def timed(name: str, work: Callable[[], Any]) -> None:
        started = time.perf_counter()
        try:
            answer = work()
        except QueryTimeout:
            timeouts[name] += 1
            return
        except Exception:  # a problem (404) or a driver error: counted, never shown
            errors[name] += 1
            return
        seconds[name].append(time.perf_counter() - started)
        found[name] += _size(answer)  # paths, search hits, or the network's nodes

    for index, entity_id in enumerate(picks):
        timed("ownership_up", partial(main.get_ownership, graph, entity_id, "up", 6, None))
        timed("ownership_down", partial(main.get_ownership, graph, entity_id, "down", 6, None))
        if index + 1 < len(picks):
            timed("paths", partial(main.find_paths, graph, entity_id, picks[index + 1], 4, None))
        timed("network", partial(main.get_network, graph, entity_id, 2, None, 200))
        try:
            caption = main.get_entity(graph, entity_id).entity.caption
        except Exception:  # the search for this pick counts as an error
            caption, errors["search"] = "", errors["search"] + 1
        token = next(iter(caption.split()), "")
        if len(token) >= 2:  # /search needs 2 characters
            timed("search", partial(main.search, graph, token, None, 20))
    return {
        name: {
            "calls": len(seconds[name]) + timeouts[name] + errors[name],
            "p50_ms": percentile(seconds[name], 0.5),
            "p95_ms": percentile(seconds[name], 0.95),
            "max_ms": percentile(seconds[name], 1.0),
            "results": found[name],
            "timeouts": timeouts[name],
            "errors": errors[name],
        }
        for name in ENDPOINTS
    }


def eligible(graph: GraphConnection) -> list[str]:
    from neonradar_graph import cypher
    from neonradar_graph.ownership import read

    text = cypher.query("bench_entities.cypher")
    rows = graph.call(lambda driver, db: read(driver, db, text, {"limit": ELIGIBLE_LIMIT}))
    return [str(row["id"]) for row in rows]


@app.command(name="queries")
def queries_command(
    profile: Annotated[str, typer.Option("--profile", help="The profile the graph holds.")],
    n: Annotated[int, typer.Option("--n", min=1, max=1000, help="Entities to pick.")] = 20,
    seed: Annotated[int, typer.Option("--seed", help="The seed of the pick.")] = 20261102,
    real: Annotated[
        bool, typer.Option("--real", help="The real-data instance: runs the real-data gate first.")
    ] = False,
) -> None:
    """Time /ownership, /paths, /network and /search; print and write latencies only."""
    from neonradar_api.graph import GraphConnection
    from neonradar_cli import redact, summary
    from neonradar_cli.data import profile_or_exit, project_or_exit
    from neonradar_graph.instances import Instance
    from neonradar_ingest.data import gate

    project, chosen = project_or_exit(), profile_or_exit(profile)
    if real != chosen.real_data:
        need = "needs --real" if chosen.real_data else "is synthetic: run it without --real"
        typer.echo(f"FAIL  profile {chosen.profile} {need}", err=True)
        raise typer.Exit(code=2)
    with redact.guard(chosen, "bench queries", real=real) as where:
        where.step = "gate"
        gate.check_real_data(project, chosen)
        for dataset in chosen.enabled_sources(project):
            where.dataset = dataset
            gate.check_real_data(project, chosen, dataset)
        where.step, where.dataset = "bench", None
        instance = Instance.REAL if real else Instance.DEFAULT
        graph = GraphConnection(instance.settings)
        try:
            ids = eligible(graph)
            picks = pick(ids, n, seed)
            endpoints = measure(graph, picks)
        finally:
            graph.close()
        report = {"profile": chosen.profile, **project.summary_fields(), "real_data": real,
                  "n": n, "seed": seed, "eligible": len(ids), "picked": len(picks),
                  "endpoints": endpoints}  # fmt: skip
        summary.emit(chosen, "bench queries", report)


from neonradar_cli.bench_report import report_command  # noqa: E402  (one module per command)

app.command(name="report")(report_command)
