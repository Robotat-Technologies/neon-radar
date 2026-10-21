"""The NeonRadar API (contract C3, contracts/C3-api.md): `create_app()` and every v1 route.

Every route is declared with its final response model, parameter limits and problem responses,
so the OpenAPI snapshot (contracts/openapi/v1.json) does not change when a route is
implemented. In M1.7d only `GET /health` is implemented; the others answer 501 with a problem
naming the milestone or phase that implements them. The API is read-only, binds to 127.0.0.1
(`neonradar api serve`) and makes no outbound calls: FastAPI's OpenTelemetry is switched off
and the CDN-backed `/docs` and `/redoc` pages are not served (guardrail G3).
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.telemetry import TelemetryConfig

from neonradar_api import problems
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
M19C: Final = "M1.9c"
PHASE_2: Final = "Phase 2"
PHASE_4: Final = "Phase 4"

EntityIdPath = Annotated[str, Path(pattern=ENTITY_ID_PATTERN, description="A C2 node id.")]
EntityIdQuery = Annotated[str, Query(pattern=ENTITY_ID_PATTERN)]
RelTypes = Annotated[
    list[RelationshipType] | None, Query(description="Repeatable; all record types if absent.")
]

router = APIRouter(prefix=API_PREFIX)


@router.get("/health", tags=["meta"])
def get_health(graph: Annotated[GraphConnection, Depends(get_graph)]) -> HealthResponse:
    """Neo4j connectivity and versions; always 200, `degraded` unless Neo4j, APOC and GDS answer."""
    return check_health(graph)


@router.get("/meta", tags=["meta"])
def get_meta(request: Request) -> MetaResponse:
    """Versions, datasets with licences and counts, disclaimers and graph counts."""
    not_implemented(request, M19C)


@router.get("/search", tags=["entities"], responses=responses(422, 503))
def search(
    request: Request,
    q: Annotated[str, Query(min_length=2, max_length=200)],
    labels: Annotated[list[SearchLabel] | None, Query(description="Repeatable.")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    """Full-text search over names (and exact account numbers)."""
    not_implemented(request, M19C)


@router.get("/entities/{entity_id}", tags=["entities"], responses=responses(404, 422, 503))
def get_entity(request: Request, entity_id: EntityIdPath) -> EntityDetail:
    """One `:Entity` or `:Sanction` node, by its id or any id in its `referents`."""
    not_implemented(request, M19C)


@router.get("/entities/{entity_id}/network", tags=["entities"], responses=responses(404, 422, 503))
def get_network(
    request: Request,
    entity_id: EntityIdPath,
    depth: Annotated[int, Query(ge=1, le=3)] = 1,
    rel_types: RelTypes = None,
    max_nodes: Annotated[int, Query(ge=1, le=500)] = 200,
) -> Subgraph:
    """The neighbourhood of a node, up to `depth` hops, capped at `max_nodes`."""
    not_implemented(request, M19C)


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
    request: Request,
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
    not_implemented(request, M19C)


@router.get("/alerts/{alert_id}", tags=["alerts"], responses=responses(404, 422, 503))
def get_alert(
    request: Request,
    alert_id: Annotated[
        str,
        Path(pattern=ALERT_ID_PATTERN, min_length=ALERT_ID_LENGTH, max_length=ALERT_ID_LENGTH),
    ],
) -> AlertDetail:
    """The complete C4 alert and its evidence subgraph."""
    not_implemented(request, M19C)


@router.get("/typologies", tags=["typologies"])
def list_typologies(request: Request) -> list[TypologySummary]:
    """Every typology of the catalog, by slug."""
    not_implemented(request, M19C)


@router.get("/typologies/{slug}", tags=["typologies"], responses=responses(404, 422))
def get_typology(
    request: Request, slug: Annotated[str, Path(pattern=SLUG_PATTERN)]
) -> TypologyDetail:
    """One typology with its explainer, citations, parameters and false positives."""
    not_implemented(request, M19C)


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


def create_app(graph: GraphConnection | None = None) -> FastAPI:
    """The app; nothing connects to Neo4j until a route needs it (`uvicorn --factory`)."""
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
    problems.install(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[UI_DEV_ORIGIN],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )
    app.include_router(router)
    app.openapi = _with_problem_schema(app)  # type: ignore[method-assign]
    return app
