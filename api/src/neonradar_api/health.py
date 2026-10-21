"""`GET /api/v1/health`: Neo4j connectivity and the versions of Neo4j, APOC and GDS (C3).

`ok` exactly when Neo4j answers and both APOC and GDS are present (the same rule as
`make smoke`); otherwise `degraded`. The route always answers 200, so a caller reads the body.
"""

import logging
from typing import LiteralString

from neo4j.exceptions import Neo4jError

from neonradar_api.graph import GraphConnection, GraphUnavailable
from neonradar_contracts.api import HealthResponse, Neo4jStatus
from neonradar_graph.smoke import APOC_VERSION, COMPONENTS, GDS_VERSION

logger = logging.getLogger(__name__)

KERNEL = "Neo4j Kernel"


def _optional_version(graph: GraphConnection, query: LiteralString) -> str | None:
    try:
        records = graph.read(query)
    except (GraphUnavailable, Neo4jError) as error:  # e.g. "Unknown function 'gds.version'"
        logger.info("health: %s", error)
        return None
    return str(records[0]["version"]) if records and records[0]["version"] else None


def check_health(graph: GraphConnection) -> HealthResponse:
    """Ask Neo4j for its components, then for the APOC and GDS versions."""
    try:
        records = graph.read(COMPONENTS)
    except (GraphUnavailable, Neo4jError) as error:
        logger.warning("health: Neo4j is not available: %s", error)
        offline = Neo4jStatus(connected=False, version=None, edition=None)
        return HealthResponse(status="degraded", neo4j=offline, apoc_version=None, gds_version=None)
    kernel = next((record for record in records if record["name"] == KERNEL), None)
    version = str(kernel["versions"][0]) if kernel and kernel["versions"] else None
    edition = str(kernel["edition"]) if kernel and kernel["edition"] else None
    apoc = _optional_version(graph, APOC_VERSION)
    gds = _optional_version(graph, GDS_VERSION)
    return HealthResponse(
        status="ok" if apoc and gds else "degraded",
        neo4j=Neo4jStatus(connected=True, version=version, edition=edition),
        apoc_version=apoc,
        gds_version=gds,
    )
