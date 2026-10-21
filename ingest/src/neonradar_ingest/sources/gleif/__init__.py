"""GLEIF (dataset `gleif_lei`, CC0 1.0): the M1.8b spike's client and its mapping to C1."""

from neonradar_ingest.sources.gleif.client import (
    coverage,
    make_client,
    normalise_company_number,
    run_spike,
)
from neonradar_ingest.sources.gleif.mapping import DATASET, build_records, summary_lines

__all__ = [
    "DATASET",
    "build_records",
    "coverage",
    "make_client",
    "normalise_company_number",
    "run_spike",
    "summary_lines",
]
