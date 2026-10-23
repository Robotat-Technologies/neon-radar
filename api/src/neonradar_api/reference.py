"""`GET /meta`, `GET /typologies` and `GET /typologies/{slug}` (contracts/C3-api.md).

Meta answers even when Neo4j cannot be read, so the disclaimers are always available: every
`record_count` is then null and both count maps are empty. Its registry and disclaimers come
from the contracts package (`load_registry()`, `load_disclaimer()`), never from NR_REPO_ROOT.
Typologies come from the catalog (`load_catalog()` under NR_REPO_ROOT) with the explainer
Markdown from `docs/typologies/` when it exists.
"""

import logging
from typing import Final

from neo4j.exceptions import Neo4jError

from neonradar_api import __version__
from neonradar_api.files import RepoFiles
from neonradar_api.graph import GraphConnection, GraphUnavailable
from neonradar_api.problems import ProblemError
from neonradar_contracts import versions
from neonradar_contracts.api import (
    DatasetInfo,
    Disclaimers,
    GraphCounts,
    MetaResponse,
    TypologyDetail,
    TypologySummary,
)
from neonradar_contracts.datasets import load_registry
from neonradar_contracts.wording import load_disclaimer
from neonradar_detect.catalog import TypologyFile
from neonradar_graph.loader import STATS

logger = logging.getLogger(__name__)

NOT_FOUND: Final = "No typology has this slug."
NO_COUNTS: Final = GraphCounts(nodes_by_label={}, relationships_by_type={})
# Nodes built from records, by dataset slug (C2 `datasets`).
RECORD_COUNTS: Final = """
MATCH (n:Entity|Sanction)
UNWIND n.datasets AS slug
RETURN slug, count(DISTINCT n) AS count
"""


def _record_counts(graph: GraphConnection) -> dict[str, int] | None:
    try:
        return {str(row["slug"]): int(row["count"]) for row in graph.read(RECORD_COUNTS)}
    except (GraphUnavailable, Neo4jError) as error:
        logger.warning("meta: record counts unavailable: %s", error)
        return None


def _graph_counts(graph: GraphConnection) -> GraphCounts:
    try:
        row = graph.read(STATS)[0]
    except (GraphUnavailable, Neo4jError) as error:  # also: APOC missing
        logger.warning("meta: graph counts unavailable: %s", error)
        return NO_COUNTS
    return GraphCounts(
        nodes_by_label={str(k): int(v) for k, v in sorted(row["labels"].items())},
        relationships_by_type={str(k): int(v) for k, v in sorted(row["relTypesCount"].items())},
    )


def meta(graph: GraphConnection) -> MetaResponse:
    """The contract files come from the contracts package (C3), never from NR_REPO_ROOT."""
    counts = _record_counts(graph)
    datasets = [
        DatasetInfo(
            slug=dataset.slug,
            title=dataset.title,
            licence_id=dataset.licence.id,
            licence_url=dataset.licence.url,
            attribution=dataset.attribution,
            synthetic=dataset.synthetic,
            personal_data=dataset.personal_data,
            record_count=None if counts is None else counts.get(dataset.slug, 0),
            loaded_at=None,
        )
        for dataset in load_registry().datasets
    ]
    return MetaResponse(
        app_version=__version__,
        contracts_version=versions.CONTRACTS,
        schema_version=versions.GRAPH_SCHEMA,
        datasets=datasets,
        disclaimers=Disclaimers(
            standing=load_disclaimer("standing-v1"),
            synthetic_demo=load_disclaimer("synthetic-demo-v1"),
            real_data=load_disclaimer("real-data-v2"),
        ),
        counts=NO_COUNTS if counts is None else _graph_counts(graph),
    )


def _summary(typology: TypologyFile) -> TypologySummary:
    return TypologySummary(
        slug=typology.slug,
        name=typology.name.strip(),
        tier=typology.tier,
        status=typology.status,
        summary=typology.summary.strip(),
        detector_available=typology.detector is not None,
    )


def typologies(files: RepoFiles) -> list[TypologySummary]:
    catalog = files.catalog()
    return [_summary(catalog[slug]) for slug in sorted(catalog)]


def typology(files: RepoFiles, slug: str) -> TypologyDetail:
    found = files.catalog().get(slug)
    if found is None:
        raise ProblemError(404, NOT_FOUND)
    return TypologyDetail(
        **_summary(found).model_dump(),
        definition_markdown=files.explainer(found),
        graph_pattern=found.graph_pattern.strip(),
        citations=files.citations(found.citations),
        parameters={
            name: parameter.model_dump(exclude_none=True)
            for name, parameter in found.parameters.items()
        },
        false_positives=list(found.false_positives),
    )
