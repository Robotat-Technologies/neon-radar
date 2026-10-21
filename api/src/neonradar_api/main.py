"""The NeonRadar API (contract C3, contracts/C3-api.md): `create_app()` and every v1 route.

Every route is declared with its final response model, parameter limits and problem responses,
so the OpenAPI snapshot (contracts/openapi/v1.json) does not change when a route is
implemented. The Phase 1 routes are implemented (M1.9c); ownership and paths (Phase 2) and the
copilot (Phase 4) answer 501 with a problem naming the phase that implements them. The API is
read-only, binds to 127.0.0.1 (`neonradar api serve`) and makes no outbound calls: FastAPI's
OpenTelemetry is switched off, and instead of its CDN-backed `/docs` and `/redoc` pages it
serves an offline page at `/docs` (guardrail G3).
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.telemetry import TelemetryConfig

from neonradar_api import alerts, docs_page, entities, problems, reference
from neonradar_api.files import RepoFiles, get_files
from neonradar_api.graph import GraphConnection, get_graph
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
    MAX_CURSOR_LENGTH,
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
    SearchLabel,
    SearchResponse,
    Subgraph,
    TypologyDetail,
    TypologySummary,
)

UI_DEV_ORIGIN: Final = "http://localhost:5173"
# FastAPI 0.143 ships native OpenTelemetry and can add OTLP exporters from the environment
# (FASTAPI_OTEL_AUTO_CONFIGURE, OTEL_EXPORTER_OTLP_*). Every switch is off (guardrail G3).
TELEMETRY_OFF: Final[TelemetryConfig] = {
    "tracing": False,
    "metrics": False,
    "logs": False,
    "operation_spans": False,
    "auto_configure": False,
}
PHASE_2: Final = "Phase 2"
PHASE_4: Final = "Phase 4"

EntityIdPath = Annotated[str, Path(pattern=ENTITY_ID_PATTERN, description="A C2 node id.")]
EntityIdQuery = Annotated[str, Query(pattern=ENTITY_ID_PATTERN)]
RelTypes = Annotated[
    list[RelationshipType] | None, Query(description="Repeatable; all record types if absent.")
]

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
)
def get_ownership(
    request: Request,
    entity_id: EntityIdPath,
    direction: Annotated[OwnershipDirection, Query()],
    max_hops: Annotated[int, Query(ge=1, le=8)] = 6,
    min_share: Annotated[float | None, Query(ge=0, le=100)] = None,
) -> OwnershipResponse:
    """Ownership chains up (owners) or down (holdings), with effective share bands."""
    not_implemented(request, PHASE_2)


@router.get("/paths", tags=["entities"], responses=responses(404, 422, 501, 503))
def find_paths(
    request: Request,
    from_id: EntityIdQuery,
    to_id: EntityIdQuery,
    max_hops: Annotated[int, Query(ge=1, le=6)] = 4,
    rel_types: RelTypes = None,
) -> PathsResponse:
    """Shortest paths between two nodes."""
    not_implemented(request, PHASE_2)


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


def create_app(graph: GraphConnection | None = None, files: RepoFiles | None = None) -> FastAPI:
    """The app; nothing connects to Neo4j or reads the repository files until a route needs
    them (`uvicorn --factory`)."""
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
    problems.install(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[UI_DEV_ORIGIN],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )
    app.include_router(router)
    app.add_api_route("/docs", _docs_page, methods=["GET"], include_in_schema=False)
    app.openapi = _with_problem_schema(app)  # type: ignore[method-assign]
    return app
