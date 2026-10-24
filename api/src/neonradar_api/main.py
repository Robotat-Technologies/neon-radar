"""The NeonRadar API (contract C3, contracts/C3-api.md): `create_app()` and every v1 route.

Every route is declared with its final response model, parameter limits and problem responses,
so the OpenAPI snapshot (contracts/openapi/v1.json) does not change when a route is
implemented. The Phase 1 routes are implemented (M1.9c), ownership, paths and resolution
(C3 1.1.0, PHASE-2.md 5.3) in M2.12 (`neonradar_graph.ownership`, `resolution`), and the
copilot answers 501 naming Phase 4. The API is read-only, binds to 127.0.0.1 (`neonradar api
serve`) and makes no outbound calls: FastAPI's OpenTelemetry is switched off, and instead of
its CDN-backed `/docs` and `/redoc` pages it serves an offline page at `/docs` (guardrail G3).
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.telemetry import TelemetryConfig

from neonradar_api import alerts, docs_page, entities, problems, reference, resolution
from neonradar_api.files import RepoFiles, get_files
from neonradar_api.graph import GraphConnection, get_graph
from neonradar_api.hardening import harden
from neonradar_api.health import check_health
from neonradar_api.problems import not_implemented, responses
from neonradar_contracts import versions
from neonradar_contracts.alert import (
    ALERT_ID_LENGTH,
    ALERT_ID_PATTERN,
    ENTITY_ID_PATTERN,
    RUN_ID_LENGTH,
    RUN_ID_PATTERN,
    SLUG_PATTERN,
    Priority,
)
from neonradar_contracts.api import (
    API_PREFIX,
    EFFECTIVE_SHARE_NOTE,
    MAX_CURSOR_LENGTH,
    MAX_OWNERSHIP_PATHS,
    MAX_PATH_SUBGRAPH_NODES,
    MAX_POSSIBLE_MATCHES,
    MAX_SHORTEST_PATHS,
    PATHS_DEFAULT_TYPES,
    QUERY_TIMEOUT_SECONDS,
    AlertDetail,
    AlertPage,
    CopilotAnswer,
    CopilotRequest,
    EntityDetail,
    HealthResponse,
    MetaResponse,
    OwnershipDirection,
    OwnershipResponse,
    PathsResponse,
    Problem,
    RelationshipType,
    ResolutionResponse,
    SearchLabel,
    SearchResponse,
    Subgraph,
    TypologyDetail,
    TypologySummary,
)
from neonradar_graph import ownership

# FastAPI 0.143 ships native OpenTelemetry and can add OTLP exporters from the environment
# (FASTAPI_OTEL_AUTO_CONFIGURE, OTEL_EXPORTER_OTLP_*). Every switch is off (guardrail G3).
TELEMETRY_OFF: Final[TelemetryConfig] = {
    "tracing": False,
    "metrics": False,
    "logs": False,
    "operation_spans": False,
    "auto_configure": False,
}
PHASE_4: Final = "Phase 4"

EntityIdPath = Annotated[str, Path(pattern=ENTITY_ID_PATTERN, description="A C2 node id.")]
EntityIdQuery = Annotated[str, Query(pattern=ENTITY_ID_PATTERN)]
RelTypes = Annotated[
    list[RelationshipType] | None,
    Query(
        description="Repeatable; all 17 types C3 shows (the 16 built from records and "
        "POSSIBLY_SAME_AS) if absent."
    ),
]
PathRelTypes = Annotated[
    list[RelationshipType] | None,
    Query(
        description="Repeatable. When absent: "
        + ", ".join(PATHS_DEFAULT_TYPES)
        + ". HAS_ADDRESS, LINKED_TO and POSSIBLY_SAME_AS are used only when asked for; FLAGS, "
        "PRODUCED and RESOLVED_TO are never allowed (422)."
    ),
]
TIMEOUT_NOTE: Final = (
    f"Runs read-only with a {QUERY_TIMEOUT_SECONDS:g}-second transaction timeout; a query that "
    "times out answers a 503 problem whose detail suggests a smaller `max_hops` or fewer "
    "relationship types."
)

Graph = Annotated[GraphConnection, Depends(get_graph)]
Files = Annotated[RepoFiles, Depends(get_files)]

router = APIRouter(prefix=API_PREFIX)


@router.get("/health", tags=["meta"])
def get_health(graph: Graph) -> HealthResponse:
    """Neo4j connectivity and versions; always 200, `degraded` unless Neo4j, APOC and GDS answer."""
    return check_health(graph)


@router.get("/meta", tags=["meta"])
def get_meta(graph: Graph) -> MetaResponse:
    """Versions, datasets with licences and counts, disclaimers and graph counts."""
    return reference.meta(graph)


@router.get("/search", tags=["entities"], responses=responses(422, 503))
def search(
    graph: Graph,
    q: Annotated[str, Query(min_length=2, max_length=200)],
    labels: Annotated[list[SearchLabel] | None, Query(description="Repeatable.")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    """Full-text search over names (and exact account numbers)."""
    return entities.search(graph, q, labels, limit)


@router.get("/entities/{entity_id}", tags=["entities"], responses=responses(404, 422, 503))
def get_entity(graph: Graph, entity_id: EntityIdPath) -> EntityDetail:
    """One `:Entity` or `:Sanction` node, by its id or any id in its `referents`."""
    return entities.entity(graph, entity_id)


@router.get("/entities/{entity_id}/network", tags=["entities"], responses=responses(404, 422, 503))
def get_network(
    graph: Graph,
    entity_id: EntityIdPath,
    depth: Annotated[int, Query(ge=1, le=3)] = 1,
    rel_types: RelTypes = None,
    max_nodes: Annotated[int, Query(ge=1, le=500)] = 200,
) -> Subgraph:
    """The neighbourhood of a node, up to `depth` hops, capped at `max_nodes`."""
    return entities.network(graph, entity_id, depth=depth, rel_types=rel_types, max_nodes=max_nodes)


@router.get(
    "/entities/{entity_id}/ownership",
    tags=["entities"],
    responses=responses(404, 422, 501, 503),
    description=(
        "Chains of `OWNS` relationships that end at the entity (`up`: its owners, their owners, "
        "and so on) or start at it (`down`). `entity_id` is a canonical id or any id in its "
        "`referents`; an unknown id answers a 404 problem. Paths have 1 to `max_hops` "
        "relationships and never repeat a node. Every path's `node_ids` start at the entity "
        "(`root_id`), so for `up` they run from the entity to its top recorded owner and for "
        "`down` from the entity to its furthest holding. A path's `effective_share_min` and "
        "`effective_share_max` are the products of `share_pct_min / 100` and "
        "`share_pct_max / 100` over its relationships, times 100, rounded to 4 decimals, and "
        "null when any relationship lacks that bound; a bound is exclusive when any "
        f"relationship's bound is. {EFFECTIVE_SHARE_NOTE} At most {MAX_OWNERSHIP_PATHS} paths, "
        "ordered by `effective_share_max` descending (nulls last), then by length, then by the "
        "list `node_ids` as returned (root first); `subgraph` holds their nodes and "
        f"relationships, at most {MAX_PATH_SUBGRAPH_NODES} nodes, and `truncated` is set when "
        "either limit cut something. Only `OWNS` is traversed: `CONTROLS` and `CONSOLIDATES` "
        f"are reachable through `/paths` and `/network`. {TIMEOUT_NOTE}"
    ),
)
def get_ownership(
    graph: Graph,
    entity_id: EntityIdPath,
    direction: Annotated[
        OwnershipDirection,
        Query(description="`up`: chains that end at the entity; `down`: chains that start at it."),
    ],
    max_hops: Annotated[
        int, Query(ge=1, le=8, description="Paths have 1 to `max_hops` relationships.")
    ] = 6,
    min_share: Annotated[
        float | None,
        Query(
            ge=0,
            le=100,
            description="Absent or 0 keeps every path. Above 0, keeps the paths whose effective "
            "share can reach it: `effective_share_max` above `min_share`, or equal to it with a "
            "closed upper bound, compared after rounding. Paths whose maximum is unknown are "
            "dropped.",
        ),
    ] = None,
) -> OwnershipResponse:
    """Ownership chains up (owners) or down (holdings), with effective share ranges."""
    return graph.call(
        lambda driver, database: ownership.ownership(
            driver, entity_id, direction, max_hops, min_share or 0, database=database
        )
    )


@router.get(
    "/paths",
    tags=["entities"],
    responses=responses(404, 422, 501, 503),
    description=(
        f"Up to {MAX_SHORTEST_PATHS} shortest paths between `from_id` and `to_id`, ignoring "
        "direction, with 1 to `max_hops` relationships of the types in `rel_types`. Each id is "
        "a canonical id or any id in its `referents`; an unknown id answers a 404 problem. "
        "Effective shares and their two flags are set only for a path made entirely of `OWNS` "
        "relationships that all point the same way along it; otherwise all four are null. "
        f"{EFFECTIVE_SHARE_NOTE} {TIMEOUT_NOTE}"
    ),
)
def find_paths(
    graph: Graph,
    from_id: EntityIdQuery,
    to_id: EntityIdQuery,
    max_hops: Annotated[int, Query(ge=1, le=6)] = 4,
    rel_types: PathRelTypes = None,
) -> PathsResponse:
    """Shortest paths between two nodes."""
    return graph.call(
        lambda driver, database: ownership.paths(
            driver, from_id, to_id, max_hops, rel_types, database=database
        )
    )


@router.get(
    "/entities/{entity_id}/resolution",
    tags=["entities"],
    responses=responses(404, 422, 503),
    description=(
        "The source records an entity was built from, how each joined it, and the other "
        "entities it may describe (possible matches, never confirmed and never merged). "
        "`entity_id` is a canonical id or any id in its `referents`; an unknown id answers a "
        "404 problem. A single-record entity has one member with method `identity`. "
        "`PossibleMatch.match_probability` is null for `deterministic` and `source_hint` "
        "possible matches, and `rule` names the D rule of a `deterministic` one; every "
        'possible-match explanation says "not confirmed". At most '
        f"{MAX_POSSIBLE_MATCHES} possible matches, the highest match probability first, then "
        "those without a probability, by entity id."
    ),
)
def get_resolution(graph: Graph, entity_id: EntityIdPath) -> ResolutionResponse:
    """How an entity was resolved: its source records and its possible matches."""
    return resolution.resolution(graph, entity_id)


@router.get("/alerts", tags=["alerts"], responses=responses(422, 503))
def list_alerts(
    graph: Graph,
    typology: Annotated[str | None, Query(pattern=SLUG_PATTERN)] = None,
    priority: Annotated[Priority | None, Query()] = None,
    entity_id: Annotated[str | None, Query(pattern=ENTITY_ID_PATTERN)] = None,
    run_id: Annotated[
        str | None,
        Query(pattern=RUN_ID_PATTERN, min_length=RUN_ID_LENGTH, max_length=RUN_ID_LENGTH),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(min_length=1, max_length=MAX_CURSOR_LENGTH)] = None,
) -> AlertPage:
    """The alert queue: priority, then pattern strength, then alert id; opaque cursor."""
    return alerts.queue(
        graph,
        typology=typology,
        priority=priority,
        entity_id=entity_id,
        run_id=run_id,
        limit=limit,
        cursor=cursor,
    )


@router.get("/alerts/{alert_id}", tags=["alerts"], responses=responses(404, 422, 503))
def get_alert(
    graph: Graph,
    alert_id: Annotated[
        str,
        Path(pattern=ALERT_ID_PATTERN, min_length=ALERT_ID_LENGTH, max_length=ALERT_ID_LENGTH),
    ],
) -> AlertDetail:
    """The complete C4 alert and its evidence subgraph."""
    return alerts.detail(graph, alert_id)


@router.get("/typologies", tags=["typologies"])
def list_typologies(files: Files) -> list[TypologySummary]:
    """Every typology of the catalog, by slug."""
    return reference.typologies(files)


@router.get("/typologies/{slug}", tags=["typologies"], responses=responses(404, 422))
def get_typology(files: Files, slug: Annotated[str, Path(pattern=SLUG_PATTERN)]) -> TypologyDetail:
    """One typology with its explainer, citations, parameters and false positives."""
    return reference.typology(files, slug)


@router.post("/copilot/ask", tags=["copilot"], responses=responses(422, 501, 503))
def ask_copilot(request: Request, body: CopilotRequest) -> CopilotAnswer:
    """Answer a question from a template, with its query and evidence subgraph."""
    not_implemented(request, PHASE_4)


def _operation_id(route: APIRoute) -> str:
    return route.name


def _with_problem_schema(app: FastAPI) -> Callable[[], dict[str, Any]]:
    """`app.openapi` plus the Problem schema that the error responses refer to."""
    generate = app.openapi
    schema = Problem.model_json_schema(ref_template="#/components/schemas/{model}")

    def openapi() -> dict[str, Any]:
        document = generate()
        document.setdefault("components", {}).setdefault("schemas", {})["Problem"] = schema
        return document

    return openapi


def _docs_page() -> HTMLResponse:
    """The offline API page (not in the OpenAPI document)."""
    headers = {
        "content-security-policy": docs_page.CONTENT_SECURITY_POLICY,
        "x-content-type-options": "nosniff",
    }
    return HTMLResponse(docs_page.PAGE, headers=headers)


def create_app(
    graph: GraphConnection | None = None,
    files: RepoFiles | None = None,
    *,
    dev: bool = False,
    report: Callable[[Exception], None] | None = None,
) -> FastAPI:
    """The app; nothing connects to Neo4j or reads the repository files until a route needs
    them (`uvicorn --factory`). `harden` (PHASE-4.md M4.1) answers only this machine's host
    names, logs route templates only and contains unexpected errors; `dev` adds CORS for a UI
    served by the Vite dev server from another origin (`neonradar api serve --dev`). `report`
    marks the real-data app (PHASE-2.md M2.12): an unhandled error's traceback goes to it
    (`problems.install`), and it never sends CORS headers, so `dev` is refused with it."""
    if dev and report is not None:
        raise ValueError("the real-data app sends no CORS headers: dev and report exclude")
    connection = graph if graph is not None else GraphConnection()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        connection.close()

    app = FastAPI(
        title="NeonRadar API",
        version=versions.API,
        summary="Read-only API over the NeonRadar graph (contract C3).",
        description=(
            "Serves the NeonRadar graph, alerts and typologies to the UI and the copilot. "
            "Errors are RFC 9457 problem details. A pattern match is not evidence of "
            "wrongdoing; the disclaimers are served by `GET /api/v1/meta`."
        ),
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=None,
        redoc_url=None,
        generate_unique_id_function=_operation_id,
        telemetry=TELEMETRY_OFF,
        lifespan=lifespan,
    )
    app.state.graph = connection
    app.state.files = files if files is not None else RepoFiles()
    problems.install(app, report)  # before harden: `report`'s layer sits inside `Contain`
    app.include_router(router)
    app.add_api_route("/docs", _docs_page, methods=["GET"], include_in_schema=False)
    harden(app, dev=dev)  # after every route: trusted hosts, access log, CORS (dev), limits
    app.openapi = _with_problem_schema(app)  # type: ignore[method-assign]
    return app


def create_dev_app() -> FastAPI:
    """`create_app(dev=True)` as a factory for uvicorn (`neonradar api serve --dev`)."""
    return create_app(dev=True)
